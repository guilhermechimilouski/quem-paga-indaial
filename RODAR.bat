@echo off
chcp 65001 >nul
title Quem paga, Indaial? - atualizar dados
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Python nao encontrado. Instale em https://www.python.org/downloads/ marcando "Add python.exe to PATH".
  pause
  exit /b 1
)

if not exist .env (
  echo Primeira vez: cole o token da API da Camara (aparece em camaraindaial.sc.gov.br/dadosabertos, logado^)
  set /p TOKEN=Token: 
  call echo RADAR_TOKEN=%%TOKEN%%> .env
)

echo Instalando dependencias...
python -m pip install -q -r requirements.txt

echo.
echo Coletando (pode levar de 5 a 20 minutos na primeira vez)...
python -m coletor.coletar atualizar
if errorlevel 2 (
  echo.
  echo A Camara pediu verificacao anti-robo. O que ja foi coletado esta salvo.
  echo Espere uns 15 minutos e rode de novo.
)

echo.
echo Pronto. Agora abra o GitHub Desktop, escreva "Atualizacao manual" e clique em Commit e depois Push.
pause
