from __future__ import annotations

import ipaddress
import socket
import tempfile
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin, urlparse

import requests

from exile_filter_studio.services.file_utils import atomic_copy


ProgressCallback = Callable[[int], None]


class FilterBladeService:
    MAX_DOWNLOAD_BYTES = 20 * 1024 * 1024
    USER_AGENT = "ExileFilterStudio/1.3.2 (+local desktop client)"

    @staticmethod
    def validate_download_url(url: str) -> str:
        clean = url.strip()
        parsed = urlparse(clean)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("Informe uma URL HTTP ou HTTPS válida.")
        if parsed.username or parsed.password:
            raise ValueError("URLs com credenciais embutidas não são permitidas.")
        if parsed.hostname.lower() in {"localhost", "localhost.localdomain"}:
            raise ValueError("Endereços locais não são aceitos para download.")
        try:
            addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
            for address in addresses:
                ip = ipaddress.ip_address(address[4][0])
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                    raise ValueError("A URL aponta para uma rede local ou reservada.")
        except socket.gaierror as exc:
            raise ConnectionError(f"Não foi possível resolver o host: {parsed.hostname}") from exc
        return clean

    def download(self, url: str, destination: Path, progress: ProgressCallback | None = None) -> Path:
        clean_url = self.validate_download_url(url)
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            response = None
            current_url = clean_url
            for _ in range(6):
                response = requests.get(
                    current_url,
                    stream=True,
                    timeout=(10, 45),
                    allow_redirects=False,
                    headers={"User-Agent": self.USER_AGENT, "Accept": "text/plain,*/*;q=0.5"},
                )
                if response.is_redirect or response.is_permanent_redirect:
                    location = response.headers.get("Location")
                    response.close()
                    if not location:
                        raise ConnectionError("O servidor retornou um redirecionamento sem destino.")
                    current_url = self.validate_download_url(urljoin(current_url, location))
                    continue
                break
            else:
                raise ConnectionError("A URL excedeu o limite de cinco redirecionamentos.")

            assert response is not None
            with response:
                response.raise_for_status()
                content_type = response.headers.get("Content-Type", "").lower()
                if "text/html" in content_type:
                    raise ValueError(
                        "A URL abriu uma página HTML, não um .filter. Exporte no FilterBlade e importe o arquivo manualmente."
                    )
                declared = int(response.headers.get("Content-Length", "0") or 0)
                if declared > self.MAX_DOWNLOAD_BYTES:
                    raise ValueError("O download excede o limite de segurança de 20 MB.")

                with tempfile.NamedTemporaryFile(
                    dir=destination.parent, prefix=".download-", suffix=".tmp", delete=False
                ) as handle:
                    temporary = Path(handle.name)
                    received = 0
                    for chunk in response.iter_content(chunk_size=64 * 1024):
                        if not chunk:
                            continue
                        received += len(chunk)
                        if received > self.MAX_DOWNLOAD_BYTES:
                            raise ValueError("O download excede o limite de segurança de 20 MB.")
                        handle.write(chunk)
                        if progress:
                            progress(min(99, int(received * 100 / declared)) if declared else 0)

            atomic_copy(temporary, destination)
            if progress:
                progress(100)
            return destination
        except requests.Timeout as exc:
            raise TimeoutError("O download demorou demais. Verifique a conexão e tente novamente.") from exc
        except requests.RequestException as exc:
            raise ConnectionError(f"Falha ao baixar o filtro: {exc}") from exc
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)
