# Sound Manager

Organize sua biblioteca de sons, ouça arquivos e edite trechos em uma única janela. O Sound Manager trabalha com os arquivos do seu computador e funciona offline.

## Abrir o app

1. Extraia o pacote recebido para uma pasta do computador.
2. **Windows:** abra `SoundManager.exe` com dois cliques.
3. **Linux:** abra `SoundManager`. Se o sistema pedir permissão para executar, marque o arquivo como executável nas propriedades ou use `chmod +x SoundManager` no terminal.

Não é necessário instalar Python ou FFmpeg para usar o pacote do app. Se o pacote tiver uma pasta `_internal`, mantenha essa pasta junto do programa. A primeira abertura pode levar alguns segundos.

## Escolher seus sons

Na primeira abertura, clique em **Escolher biblioteca…** e selecione a pasta onde estão seus arquivos de áudio. Você pode trocar essa pasta a qualquer momento. O app não inclui uma biblioteca de sons.

As pastas aparecem à esquerda. Clique em uma delas para ver seus sons na lista à direita. **Subir** volta à pasta acima e **Raiz** volta à pasta principal da biblioteca. Para abrir um som de outro local, use **Abrir arquivo…**.

Use os campos de busca para encontrar arquivos:

- **Filtrar pastas ou arquivos…**, à esquerda, procura nomes de pastas e dos arquivos dentro delas.
- **Filtrar arquivos pelo nome…**, à direita, procura apenas os arquivos da pasta que está aberta.

Digite uma parte do nome; maiúsculas e minúsculas não fazem diferença. Clique no **×** para limpar o filtro ou em **↻** para atualizar depois de mudar arquivos fora do app.

## Ouvir um som

Clique em **▶** na linha do arquivo para ouvir. Clique novamente para pausar. Um duplo clique no nome também reproduz o som.

Na mesma linha, você encontra o tempo de reprodução, o volume, **■ Parar** e **↻ Repetir**. O volume de reprodução muda apenas o que você ouve; ele não altera o volume gravado no arquivo.

## Selecionar e editar um trecho

1. Clique em **Recortar** na linha do arquivo para abrir a forma de onda.
2. Arraste sobre a onda para selecionar o trecho desejado.
3. Ajuste as alças verdes ou os campos **Início** e **Fim** para refinar a seleção.
4. Clique em **Play** para ouvir a seleção. O botão vira **Pausa** durante a reprodução; clique nele para pausar e em **Play** para continuar.

A **linha amarela na onda** mostra onde o áudio está tocando. Ela é apenas um indicador. Para mudar a posição de reprodução ou de colagem, clique ou arraste na **barra amarela abaixo da onda**. Na onda, arraste para selecionar trechos ou ajustar suas alças.

Use as lupas ou a roda do mouse para ampliar a onda. A barra cinza percorre o áudio ampliado, e o botão de enquadrar volta a mostrar o som inteiro. **Fechar** recolhe o editor na lista.

Passe o mouse sobre os ícones para ver a função de cada botão. As ferramentas de edição permitem:

- **Copiar:** guardar o trecho selecionado para colar depois.
- **Colar:** inserir o trecho copiado na posição da barra amarela, inclusive em outro arquivo.
- **Remover seleção:** excluir o trecho e juntar as partes que ficaram antes e depois. Isso edita o áudio, sem excluir o arquivo da biblioteca.
- **Desfazer / Refazer:** voltar uma edição ou reaplicá-la.
- **Selecionar tudo:** selecionar o áudio inteiro.
- **Inverter:** fazer o trecho tocar de trás para frente.
- **Volume − / +:** diminuir ou aumentar o volume da seleção pelo valor em dB indicado ao lado.
- **Fade in / Fade out:** fazer o trecho começar suavemente ou desaparecer aos poucos. O campo **Fade** define a duração do efeito em segundos.

A cópia de áudio fica disponível durante a sessão. Ao copiar outro trecho, você substitui a cópia anterior.

## Salvar suas alterações

**Salvar áudio** grava o áudio completo no **mesmo arquivo que está aberto**. O app mostra o caminho e pede sua confirmação antes de substituir o arquivo. Esse botão não usa a pasta de exportação de trechos.

**Salvar trecho…** cria um arquivo com apenas a seleção. Escolha o nome, a pasta e o formato: WAV, OGG, FLAC ou MP3. Use outro nome ou destino para preservar o arquivo aberto. WAV e FLAC evitam a compressão com perda de OGG e MP3.

As edições são mantidas ao trocar de arquivo durante a sessão. **Para mantê-las depois de fechar o app, use Salvar áudio e confirme.** Alterações não salvas são perdidas ao fechar.

## Copiar arquivos para outra pasta

Arraste pelo **nome do arquivo** para uma pasta na árvore à esquerda ou para uma pasta aberta no gerenciador de arquivos do computador. Use Ctrl ou Shift para selecionar vários arquivos.

O arraste faz uma cópia e mantém o arquivo de origem. Ao copiar dentro do app, nomes repetidos recebem um sufixo como `(cópia)`, sem substituir o arquivo que já existe no destino. **Mostrar arquivo** abre a pasta do som original.

## Atalhos

| Atalho | Função |
| --- | --- |
| Espaço | Reproduzir / pausar |
| Ctrl+O | Abrir um arquivo |
| Ctrl+A | Selecionar todo o áudio com o editor aberto; selecionar arquivos com o editor fechado |
| Ctrl+C | Copiar a seleção de áudio |
| Ctrl+V | Colar na posição da barra amarela |
| Ctrl+Z | Desfazer |
| Ctrl+Y ou Ctrl+Shift+Z | Refazer |
| Ctrl+S | Salvar o áudio completo no arquivo aberto, após confirmação |
| Ctrl+Shift+S | Salvar o trecho selecionado em outro arquivo |
| Alt+↑ | Subir uma pasta |

Nos campos de texto, Ctrl+A continua selecionando o texto do campo.

## Preferências e formatos

O app lembra a biblioteca, a última pasta aberta, o tamanho e a posição da janela, o volume de reprodução, a repetição e a última pasta usada para salvar trechos.

Formatos que podem ser abertos: **WAV, OGG, MP3, FLAC, AIFF, M4A, AAC, OPUS e WMA**.

## Se precisar de ajuda

- **Não sai som:** confira o volume na linha do arquivo, o volume do sistema e o dispositivo de áudio selecionado no computador.
- **Um arquivo não abre:** tente outro som para conferir se o problema está naquele arquivo. O app mostra uma mensagem quando encontra um áudio danificado.
- **O app não abre no Linux:** confira se há um ambiente gráfico e as bibliotecas do Qt disponíveis. Em Ubuntu/Debian, as dependências usuais podem ser instaladas com:

```bash
sudo apt-get install libegl1 libgl1 libopengl0 libxkbcommon-x11-0 \
  libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
  libxcb-render-util0 libxcb-xinerama0 libxcb-xkb1 libdbus-1-3 libpulse0
```
