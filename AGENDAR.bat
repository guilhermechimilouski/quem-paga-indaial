@echo off
chcp 65001 >nul
title Quem paga, Indaial? - primeira publicacao e agendamento
cd /d "%~dp0"
git config user.name "Quem paga, Indaial? (atualização automática)"
git config user.email "quempagaindaial@gmail.com"
git rm --cached -q dados/radar.db
git add -A
git commit -q -m "Coleta completa no computador, páginas dos vereadores para o Google e vigia diário"
echo.
echo Enviando para o GitHub. Se abrir uma janela do GitHub, entre na sua conta e autorize.
echo.
git push
if errorlevel 1 (
  echo.
  echo O envio falhou. Copie a mensagem acima e mande para o Claude.
  pause
  exit /b 1
)
echo.
echo Criando a tarefa diaria das 13h...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$a = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument '/c \"%~dp0ATUALIZAR_DIARIO.bat\"' -WorkingDirectory '%~dp0'; $t = New-ScheduledTaskTrigger -Daily -At 13:00; $s = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2); Register-ScheduledTask -TaskName 'Quem paga Indaial - atualizacao diaria' -Action $a -Trigger $t -Settings $s -Description 'Coleta os dados da Camara de Indaial e atualiza quempagaindaial.com.br' -Force | Out-Null; Get-ScheduledTask -TaskName 'Quem paga Indaial - atualizacao diaria' | Select-Object TaskName, State"
echo.
echo Pronto. O site foi publicado e a atualizacao diaria das 13h esta agendada. Pode fechar e avisar o Claude.
pause
