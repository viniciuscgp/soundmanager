# Desenvolvimento do Sound Manager

Requisitos: Python 3.10 ou superior. A biblioteca de sons fica fora do repositório; os testes geram áudios sintéticos.

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

## Verificar

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tools\validate_app.py
.\.venv\Scripts\python.exe tools\validate_editor.py
.\.venv\Scripts\python.exe tools\validate_languages.py
```

O segundo comando verifica a interface, reprodução sem abrir a onda, editor na linha, recorte, exportação, eventos de arraste/cópia e restauração de preferências em um ambiente separado dentro de `.state/validation`, e gera capturas de tela. O terceiro verifica volume, inversão, fades, desfazer/refazer, remoção com junção das partes, áudio vazio, controles de reprodução na própria linha, colagem entre sons com taxas e canais diferentes, troca de documentos durante uma edição e exportação do resultado, em `.state/validation-editor`. Também verifica Ctrl+A, Play/Pausa, indicador na onda e confirmação, cancelamento e falha do salvamento no arquivo aberto, usando apenas arquivos sintéticos. Não alteram as preferências de uso normal nem os sons da biblioteca.

O quarto verifica a troca imediata PT-BR/EN, preservação de edição, histórico, cópia, seleção, zoom e reprodução, os diálogos traduzidos e a preferência ao reabrir. As capturas e o relatório ficam em `.state/validation-languages`.

## Textos da interface

O catálogo inglês e as ligações entre textos e controles ficam em `i18n.py`. A língua de origem é português. Use `self.ui(controle, "setText", "Texto {0}", valor)` para um texto que precisa mudar ao trocar o idioma, ou `self.t("Texto")` para diálogos. Valores como nomes de arquivos ficam fora da tradução. Para um argumento que também precisa ser traduzido, use `Message("Texto")`.
