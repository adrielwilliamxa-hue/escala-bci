@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Construindo "Escala BCI Multi-Postos.exe" (isso demora 1-3 minutos)...
python -m PyInstaller escala-bci.spec --noconfirm
if errorlevel 1 (
    echo.
    echo A construcao FALHOU -- veja as mensagens acima.
    pause
    exit /b 1
)
copy /y "dist\Escala BCI Multi-Postos.exe" "Escala BCI Multi-Postos.exe" >nul
echo.
echo Pronto! O arquivo "Escala BCI Multi-Postos.exe" esta na pasta do projeto.
echo Pra usar em outro computador, e so copiar esse arquivo.
pause
