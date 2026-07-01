# Exile Filter Studio

Aplicação desktop local para Windows e Linux que instala filtros do Path of Exile, organiza pacotes de áudio e aplica `CustomAlertSound` com backup automático. A interface está em português e foi construída com Python 3.12, PySide6, Requests e SQLite.

## O que está incluído

- dashboard com pasta do jogo, filtro atual, pacote ativo e última atualização;
- perfis separados para Path of Exile 1 e Path of Exile 2, com caminho e filtro ativo próprios;
- download por URL direta e importação manual de `.filter`;
- importação dos filtros online do Path of Exile 2 em `OnlineFilters`, inclusive arquivos sem extensão;
- validação de extensão, tamanho, conteúdo e blocos `Show`/`Hide`/`Minimal`;
- pacotes de som e mapeamentos para Currency, Divination Cards, Unique Items, Maps, Scarabs, Essences, Fragments, Gems e High Value Items;
- seletores de áudio em cartões responsivos, com o nome do arquivo ocupando uma linha inteira;
- categorias específicas do PoE 2: Waystones, Tablets, Omens, Runes/Soul Cores, Uncut Gems, Charms, Keys, Logbooks e Relics;
- reprodução de WAV/MP3 pela camada multimídia do Qt;
- aplicação de `CustomAlertSound` ou `CustomAlertSoundOptional`, substituindo alertas padrão anteriores no bloco;
- cópia atômica, original imutável, backup antes de cada alteração e restauração segura;
- prévia com destaque de comandos de som, busca e comparação original × alterado;
- histórico, relatórios Markdown e logs no app e em arquivo rotativo;
- exportação de um ZIP autocontido para compartilhar, reescrevendo o filtro e aleatorizando os nomes dos áudios;
- tema escuro/claro e tarefas em segundo plano para a interface não travar;
- detecção da pasta padrão no Windows e de instalações Steam/Proton comuns no Linux.

## Limitações do FilterBlade e decisão de integração

O FilterBlade oferece download manual na tela **Export to PoE**, mas não publica uma API estável de download para este tipo de integração. A página também é gerada por JavaScript e os downloads podem depender do estado da sessão. Por isso, o app:

1. não automatiza login, cookies ou endpoints privados;
2. aceita somente uma URL HTTP/HTTPS direta que devolva o conteúdo do `.filter`;
3. recusa HTML, downloads acima de 20 MB, URLs com credenciais e endereços de rede local;
4. oferece importação manual como fluxo principal e sempre disponível.

Os termos publicados pelo FilterBlade declaram que o código do site, embora visível, não pode ser redistribuído, modificado ou monetizado sem permissão. Este projeto não contém nem modifica código do FilterBlade; apenas processa um arquivo exportado pelo próprio usuário. Consulte [Export do FilterBlade](https://www.filterblade.xyz/) e [contato/termos do FilterBlade](https://www.filterblade.xyz/Contact). Isso é uma análise técnica conservadora, não aconselhamento jurídico.

A sintaxe de som segue a [documentação oficial de filtros do Path of Exile](https://www.pathofexile.com/item-filter/about), que documenta `PlayAlertSound`, `CustomAlertSound` e `CustomAlertSoundOptional`, volume de 0 a 300 e exemplos com MP3.

## Instalação para desenvolvimento

Pré-requisito: Python 3.12 ou superior.

### Windows (PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

### Linux

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

No Linux, a reprodução MP3 depende dos codecs multimídia disponíveis no sistema. WAV costuma ser a opção mais portátil.

## Primeiro uso

1. Escolha **Path of Exile 1** ou **Path of Exile 2** em **Configurações** ou na tela **Sons**. Cada jogo mantém seu próprio caminho e filtro ativo.
2. Use **Testar permissão de escrita**.
3. Exporte o `.filter` no FilterBlade e escolha **Importar .filter** no dashboard. Para os filtros sincronizados do PoE 2, use **Importar filtro online**: o app lê os metadados dos arquivos sem extensão e cria uma cópia local `.filter`, sem alterar o cache do jogo.
4. Em **Sons**, crie ou escolha um pacote, selecione a pasta com WAV/MP3, recarregue a lista e ative os mapeamentos desejados.
5. Teste os sons e clique em **Aplicar ao filtro ativo**.
6. Para enviar a um amigo, use **Exportar ZIP surpresa** no dashboard. Ele deve extrair todo o ZIP na pasta de filtros, mantendo a subpasta `sounds`.
7. Confira o relatório em **Editor → Abrir relatórios**. Se necessário, reverta em **Histórico → Backups**.

O ZIP não contém os nomes originais nem uma tabela de correspondência. Isso oculta a surpresa pelo nome do arquivo, mas não criptografa o áudio: quem extrair e reproduzir os arquivos ainda poderá ouvi-los.

O classificador usa condições e comentários dos blocos. Filtros muito personalizados podem não corresponder a todas as categorias; elas serão listadas no relatório como não encontradas e não serão alteradas.

Ao reaplicar um pacote, comandos de som anteriormente inseridos pelo app em blocos que deixaram de corresponder à categoria são removidos. Isso permite corrigir classificações antigas antes de gerar um novo ZIP.

## Dados locais

- Windows: `%LOCALAPPDATA%\Exile Filter Studio`
- Linux: `$XDG_DATA_HOME/exile-filter-studio` ou `~/.local/share/exile-filter-studio`

Ali ficam `studio.db`, logs, originais, versões modificadas, backups e relatórios. Para testes, defina `EXILE_FILTER_STUDIO_HOME` para redirecionar tudo a outra pasta.

## Gerar executável

Windows:

```powershell
.\build.ps1
```

Linux:

```bash
chmod +x build.sh
./build.sh
```

O PyInstaller gera uma pasta autocontida em `dist/ExileFilterStudio`. O build precisa ser executado separadamente em cada sistema operacional; PyInstaller não faz cross-compilation Windows/Linux.

## Testes

```bash
python -m unittest discover -s tests -v
```

Os testes cobrem parser/classificação, idempotência dos comandos de som, SQLite, operações atômicas e isolamento da pasta de áudio.

## Estrutura

```text
app.py
src/exile_filter_studio/
├── manager.py
├── database.py
├── repositories/
│   ├── app_repository.py
│   └── settings_repository.py
├── services/
│   ├── filterblade_service.py
│   ├── online_filter_service.py
│   ├── filter_editor.py
│   ├── export_service.py
│   ├── sound_service.py
│   ├── backup_service.py
│   └── report_service.py
└── ui/
    ├── main_window.py
    ├── settings_page.py
    ├── sound_mapping_page.py
    ├── editor_page.py
    ├── history_page.py
    └── log_page.py
```

## Segurança

- nenhum token ou credencial é armazenado;
- toda substituição de filtro existente cria backup, mesmo que outras preferências sejam alteradas;
- downloads são limitados, validados e gravados primeiro em arquivo temporário;
- o app não envia filtros, sons ou histórico a nenhum serviço;
- a remoção do histórico apaga apenas a linha do banco, nunca o filtro instalado.
