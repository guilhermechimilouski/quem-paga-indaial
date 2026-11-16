@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ===== %date% %time% ===== >> atualizacao_log.txt
git pull --rebase --autostash >> atualizacao_log.txt 2>&1
python -m coletor.coletar atualizar >> atualizacao_log.txt 2>&1
echo Coleta terminou com codigo %errorlevel% >> atualizacao_log.txt
git add docs dados >> atualizacao_log.txt 2>&1
git diff --cached --quiet && (echo Nada novo para enviar. >> atualizacao_log.txt) || (git commit -m "Atualização automática dos dados (%date%)" >> atualizacao_log.txt 2>&1 & git push >> atualizacao_log.txt 2>&1)
echo Fim: %time% >> atualizacao_log.txt
