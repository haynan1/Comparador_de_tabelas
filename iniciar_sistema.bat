@echo off
setlocal

cd /d "%~dp0"

echo ==========================================
echo  Comparador IPASGO - Inicializacao
echo ==========================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo Criando ambiente virtual...
    py -3 -m venv venv
    if errorlevel 1 (
        echo.
        echo Nao foi possivel criar a venv usando py -3.
        echo Tentando com python...
        python -m venv venv
        if errorlevel 1 (
            echo.
            echo Erro ao criar o ambiente virtual.
            pause
            exit /b 1
        )
    )
) else (
    echo Ambiente virtual ja existe.
)

echo.
echo Instalando dependencias...
"venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo.
    echo Erro ao atualizar o pip.
    pause
    exit /b 1
)

"venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo Erro ao instalar as dependencias.
    pause
    exit /b 1
)

echo.
echo Iniciando o sistema...
echo Abra no navegador: http://127.0.0.1:5000
echo.

"venv\Scripts\python.exe" run.py

echo.
echo Sistema encerrado.
pause
