$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$environmentPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'

try {
    if (-not (Test-Path -LiteralPath $environmentPython)) {
        $pythonCandidates = @()
        $pythonRoot = Join-Path $env:LOCALAPPDATA 'Python'
        if (Test-Path -LiteralPath $pythonRoot) {
            $pythonCandidates += Get-ChildItem -LiteralPath $pythonRoot -Directory |
                Where-Object { $_.Name -like 'pythoncore-*' } |
                Sort-Object Name -Descending |
                ForEach-Object { Join-Path $_.FullName 'python.exe' }
        }
        $programsPythonRoot = Join-Path $env:LOCALAPPDATA 'Programs\Python'
        if (Test-Path -LiteralPath $programsPythonRoot) {
            $pythonCandidates += Get-ChildItem -LiteralPath $programsPythonRoot -Directory |
                Sort-Object Name -Descending |
                ForEach-Object { Join-Path $_.FullName 'python.exe' }
        }
        $commandPython = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($commandPython -and $commandPython.Source -notlike '*WindowsApps*') {
            $pythonCandidates += $commandPython.Source
        }
        $basePython = $pythonCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
        if (-not $basePython) {
            throw 'Python nao encontrado. Instale Python 3.10 ou superior em https://www.python.org/downloads/ e execute novamente.'
        }
        Write-Host 'Preparando o ambiente do Sound Manager...'
        & $basePython -m venv (Join-Path $PSScriptRoot '.venv')
        if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel criar o ambiente Python.' }
    }
    & $environmentPython -c "import importlib.util, sys; sys.exit(0 if all(importlib.util.find_spec(name) for name in ('PySide6', 'numpy', 'soundfile', 'imageio_ffmpeg')) else 1)"
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'Instalando as dependencias (necessita internet apenas na primeira vez)...'
        & $environmentPython -m pip install --disable-pip-version-check -r (Join-Path $PSScriptRoot 'requirements.txt')
        if ($LASTEXITCODE -ne 0) { throw 'A instalacao falhou. Verifique a conexao com a internet e tente novamente.' }
    }
    $windowPython = Join-Path $PSScriptRoot '.venv\Scripts\pythonw.exe'
    Start-Process -FilePath $windowPython -ArgumentList @('app.py') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
} catch {
    Write-Host ('Erro: ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
