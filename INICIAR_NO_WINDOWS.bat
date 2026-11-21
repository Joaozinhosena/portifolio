@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Criando ambiente virtual...
    py -m venv .venv
    if errorlevel 1 goto erro
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 goto erro

echo Instalando/verificando dependencias...
python -m pip install -r requirements.txt
if errorlevel 1 goto erro

echo.
echo Servidor iniciado. Abra http://127.0.0.1:5000 no navegador.
echo Para encerrar, pressione CTRL+C nesta janela.
echo.
python app.py
pause
exit /b 0

:erro
echo Ocorreu um erro ao preparar o projeto. Confira se Python 3.12 esta instalado.
pause
exit /b 1
