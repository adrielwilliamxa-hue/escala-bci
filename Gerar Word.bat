@echo off
chcp 65001 >nul
echo Gerando os documentos Word da escala BCI a partir de Escala-BCI-2026.xlsx ...
python "%~dp0scripts\gerar_word.py" todos
echo.
echo Pronto! Os arquivos estao na pasta "Word gerados".
pause
