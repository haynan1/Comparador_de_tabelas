# Empacotamento para Windows

Este projeto já está preparado para rodar localmente e pode ser empacotado com PyInstaller.

## Preparar ambiente

```powershell
cd comparador_ipasgo_app
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install pyinstaller
```

## Gerar executável

```powershell
pyinstaller --noconfirm --onedir --name ComparadorIPASGO ^
  --add-data "app\templates;app\templates" ^
  --add-data "app\static;app\static" ^
  run.py
```

O executável ficará em:

```text
dist\ComparadorIPASGO\run.exe
```

## Script de inicialização sugerido

Crie um arquivo `iniciar_comparador.bat` ao lado do executável:

```bat
@echo off
cd /d "%~dp0"
start "" http://127.0.0.1:5000
run.exe
```

## Pastas de dados

Mantenha estas pastas ao lado do executável ou dentro da pasta de execução:

```text
data\uploads
data\processed
data\reports
```

O SQLite será criado automaticamente em `data\comparador_ipasgo.sqlite3`.

## Observações

- A aplicação não precisa de internet para funcionar depois de instalada.
- Para um instalador completo, use Inno Setup ou NSIS apontando para a pasta gerada pelo PyInstaller.
- Em produção local, mantenha `debug=False` no `run.py`.
