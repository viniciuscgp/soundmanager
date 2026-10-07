# Sound Manager

App desktop em Python para explorar uma biblioteca local, ouvir sons sem abrir outro player, editar áudio e salvar recortes. Interface em português, com PySide6, NumPy, SoundFile e FFmpeg incluído nas dependências.

## Abrir no Windows

Dê dois cliques em **SoundManager.bat**. O iniciador prepara o ambiente Python e instala as dependências na primeira execução; nesse momento precisa de internet e de Python 3.10 ou superior. Depois, o app funciona offline.

Na primeira abertura, escolha a **pasta base** da biblioteca. É possível trocar a base a qualquer momento pelo botão **Escolher biblioteca…**.

## Usar

- Biblioteca, navegação por pastas e abertura de arquivos ficam à esquerda. Clique numa pasta da árvore para ver **somente os arquivos de áudio dela**, à direita. **Subir** vai para a pasta acima; **Raiz** volta à pasta base.
- Clique em **▶** ao lado de um som para ouvir sem abrir a onda. O mesmo botão pausa; duplo clique no nome também reproduz. **Parar (■)**, **Repetir (↻)**, tempo atual/duração e volume de reprodução ficam na coluna **Reprodução da própria linha do som aberto**. O formato e o tamanho ficam juntos na coluna **Arquivo**. A lista ocupa o espaço até o fim da janela, sem player inferior.
- Clique em **Recortar**, antes do nome do arquivo, para expandir a forma de onda **na própria linha**. **Fechar** recolhe o editor e devolve o espaço à lista. A onda começa recolhida e não abre automaticamente ao ouvir ou selecionar arquivos.
- Há dois filtros independentes: **Filtrar pastas ou arquivos…** acima da árvore à esquerda e **Filtrar arquivos pelo nome…** acima da lista à direita. Basta digitar: buscam nomes que **contêm** o texto em qualquer posição, sem diferenciar maiúsculas e minúsculas, como `%meutexto%` — não é preciso digitar os `%`. À esquerda, uma pasta aparece se **o nome dela combinar ou algum arquivo dentro dela combinar**, inclusive em subpastas; os ancestrais continuam visíveis para mostrar o caminho. À direita, são filtrados **somente os arquivos exibidos na pasta atual**. São pesquisados os nomes, sem ler o conteúdo dos arquivos. Limpar pelo **×** restaura os itens. **↻** atualiza a busca depois de alterações feitas fora do app. **Abrir arquivo…** permite abrir um som fora da biblioteca e abre o editor desse arquivo.
- Arraste pelo **nome do arquivo** para uma pasta na árvore à esquerda ou uma pasta aberta no **Explorer**, para copiar. Ctrl/Shift permitem selecionar vários arquivos. O arraste oferece apenas cópia, preservando o original. Ao copiar dentro do app, nomes repetidos recebem `(cópia)`, `(cópia 2)` etc., sem substituir o destino existente.
- Arraste sobre a forma de onda para selecionar um trecho. Ajuste as alças ou os campos **Início** e **Fim**, em segundos. A onda controla somente a seleção: clicar ou arrastar nela não move a reprodução. A **barra amarela separada abaixo da onda** controla a posição de reprodução e de colagem; clique ou arraste nela. Ela cobre o áudio inteiro, mesmo quando a onda está ampliada. As setas movem a posição em 0,1 s; Home/End levam ao início/fim.
- Os ícones de **lupa − / +** e a roda do mouse ampliam a onda. A barra cinza percorre o som ampliado; o ícone de **enquadrar** restaura a visão completa.
- **Play** toca somente a seleção e vira **Pausa** durante a reprodução. Clique novamente para pausar; **Play** retoma do mesmo ponto. **Repetir** repete o áudio ou o trecho em reprodução. Há controles de parada e volume na linha do arquivo. A linha amarela na onda acompanha a posição da reprodução e é apenas visual: não pode ser arrastada. Use a barra abaixo da onda para mudar a posição.
- A barra principal reúne **Play, copiar, colar, excluir, desfazer, refazer, selecionar todo o áudio e inverter áudio selecionado** na mesma linha. As ações usam ícones com descrição e atalhos ao passar o mouse, incluindo uma **lixeira** para excluir e **setas curvas** para desfazer/refazer.
- Os ícones de **alto-falante − / +** ajustam o volume somente da seleção, pelo valor em dB ao lado. As **duas setas opostas** invertem o trecho para tocar de trás para frente, preservando os canais.
- Os ícones de **rampa crescente / decrescente** aplicam fade in no início ou fade out no final da seleção. O campo **Fade** define a duração em segundos. Se a duração ultrapassar o trecho, o fade ocupa toda a seleção.
- O ícone **Copiar** guarda uma cópia do áudio numa área temporária na memória. Abra o editor de outro som, posicione a barra amarela abaixo da onda e use o ícone **Colar** ou **Ctrl+V**. O trecho é inserido nessa posição, deslocando o restante do som. A colagem ajusta automaticamente a taxa de amostragem e os canais do trecho ao destino. A área temporária dura até o app ser fechado; uma nova cópia substitui a anterior. Também é colocado um WAV na área de transferência, cujo uso em outro aplicativo depende do suporte dele a `audio/wav`.
- Os ícones **Desfazer** e **Refazer** permitem voltar e reaplicar edições. As edições de cada arquivo são preservadas na memória ao trocar de som durante a sessão. Para mantê-las depois de fechar o app, use **Salvar áudio**. O histórico mantém até 20 passos, reduzidos conforme o tamanho do áudio para limitar o uso de memória.
- A **lixeira (Remover seleção)** exclui o trecho e junta diretamente as partes que ficaram antes e depois, sem inserir silêncio. O cursor fica no ponto da junção. **Desfazer / Ctrl+Z** recupera o trecho, e **Refazer** reaplica a remoção. Se remover o áudio inteiro, o editor fica vazio e permite desfazer ou colar um trecho.
- **Salvar áudio** (Ctrl+S) grava todo o áudio em edição no **mesmo arquivo aberto**, mantendo o caminho e o formato, após perguntar se deseja salvar. Não usa a última pasta de exportação. **Salvar trecho…** (Ctrl+Shift+S) continua exportando a seleção para outro nome ou destino, em WAV 24 bits, OGG Vorbis, FLAC 24 bits ou MP3. A extensão do arquivo determina o formato final. WAV/FLAC evitam a compressão com perda de OGG/MP3.
- **Mostrar arquivo** abre a pasta do arquivo original no Explorer.

O app abre WAV, OGG, MP3, FLAC, AIFF, M4A, AAC, OPUS e WMA. A leitura tenta SoundFile primeiro e usa FFmpeg para os demais codecs. Arquivos danificados mostram uma mensagem de erro. A edição ocorre em memória; arquivos grandes exigem RAM proporcional à duração e à quantidade de canais.

As edições ficam na memória até usar **Salvar áudio** e confirmar a substituição do arquivo aberto. A gravação é preparada num arquivo temporário e só substitui o original após terminar com sucesso. Para exportar um trecho, escolha outro nome ou destino; essa exportação bloqueia sobrescrita do original, inclusive quando o destino é um link para ele. Cópias por arraste são criadas apenas na pasta escolhida; o arquivo de origem permanece no lugar.

## Preferências e atalhos

Biblioteca, última pasta, posição e tamanho da janela, divisória, volume, repetição e última pasta de exportação ficam em `.state/settings.ini` ao executar pelo código Python. No executável Windows ficam em `%LOCALAPPDATA%\SoundManager\settings.ini`; no executável Linux, em `$XDG_CONFIG_HOME/sound-manager/settings.ini` ou `~/.config/sound-manager/settings.ini`. Assim, atualizar ou mover o executável preserva as preferências. O argumento `--settings` permite escolher outro arquivo de preferências. Se um monitor foi desconectado, a janela volta para uma tela disponível.

| Atalho | Ação |
| --- | --- |
| Espaço | Reproduzir / pausar |
| Ctrl+O | Abrir arquivo |
| Ctrl+C | Copiar seleção de áudio |
| Ctrl+V | Inserir o trecho copiado na posição do cursor |
| Ctrl+Z | Desfazer edição |
| Ctrl+Y ou Ctrl+Shift+Z | Refazer edição |
| Ctrl+A | Selecionar todo o áudio enquanto o editor está aberto; com o editor fechado, selecionar arquivos. Campos de texto mantêm a seleção de texto. |
| Ctrl+S | Salvar o áudio completo no arquivo aberto, após confirmação |
| Ctrl+Shift+S | Salvar seleção como |
| Alt+↑ | Subir uma pasta |

## Executar manualmente no Windows

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Uma biblioteca pode ser informada por argumento:

```powershell
.\.venv\Scripts\python.exe app.py --library "C:\MinhaBibliotecaDeSons"
```

## Executar pelo código-fonte no Linux

Em Ubuntu/Debian, instale Python/venv e as bibliotecas de sistema usadas pelo Qt:

```bash
sudo apt-get update
sudo apt-get install python3 python3-venv libegl1 libgl1 libopengl0 \
  libxkbcommon-x11-0 libxcb-cursor0 libxcb-icccm4 libxcb-image0 \
  libxcb-keysyms1 libxcb-render-util0 libxcb-xinerama0 libxcb-xkb1 \
  libdbus-1-3 libpulse0
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

## Conteúdo do repositório

Este repositório contém o código-fonte do app, dependências de execução, iniciadores, testes, ferramentas de validação e os ícones da interface. Os testes geram seus próprios áudios sintéticos; nenhuma biblioteca de sons precisa ser baixada para validá-los.

Os geradores de executáveis, dependências de empacotamento, `build/`, `dist/`, ambientes Python, preferências pessoais e arquivos de áudio ficam fora do versionamento por meio do `.gitignore`. Esses arquivos podem permanecer no disco sem entrar nos commits.

## Verificar

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tools\validate_app.py
.\.venv\Scripts\python.exe tools\validate_editor.py
```

O segundo comando verifica a interface, reprodução sem abrir a onda, editor na linha, recorte, exportação, eventos de arraste/cópia e restauração de preferências em um ambiente separado dentro de `.state/validation`, e gera capturas de tela. O terceiro verifica volume, inversão, fades, desfazer/refazer, remoção com junção das partes, áudio vazio, controles de reprodução na própria linha, colagem entre sons com taxas e canais diferentes, troca de documentos durante uma edição e exportação do resultado, em `.state/validation-editor`. Também verifica Ctrl+A, Play/Pausa, indicador na onda e confirmação, cancelamento e falha do salvamento no arquivo aberto, usando apenas arquivos sintéticos. Não alteram as preferências de uso normal nem os sons da biblioteca.
