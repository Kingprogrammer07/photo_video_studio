@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Photo Video Studio

where python >nul 2>nul
if errorlevel 1 (
  echo [XATO] Python topilmadi. https://www.python.org/downloads/ dan o'rnating.
  echo O'rnatishда "Add Python to PATH" ni belgilang.
  echo. & pause & exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo ============================================
  echo   Birinchi ishga tushirish
  echo   Virtual muhit yaratilmoqda... ^(bir marta^)
  echo ============================================
  python -m venv .venv
  if errorlevel 1 ( echo [XATO] venv yaratilmadi. & pause & exit /b 1 )
)

set "PY=.venv\Scripts\python.exe"
"%PY%" -c "import customtkinter, PIL, numpy" 1>nul 2>nul
if errorlevel 1 (
  echo ============================================
  echo   Kutubxonalar o'rnatilmoqda ^(offline, internetsiz^)...
  echo   Bu ~30-60 soniya davom etishi mumkin.
  echo   OYNANI YOPMANG - tugmagunicha kuting.
  echo ============================================
  "%PY%" -m pip install --no-index --find-links "%~dp0wheels" customtkinter pillow numpy
  "%PY%" -c "import customtkinter, PIL, numpy" 1>nul 2>nul
  if errorlevel 1 (
    echo Offline o'rnatilmadi. Internet orqali urinilmoqda...
    "%PY%" -m pip install -r requirements.txt
    if errorlevel 1 ( echo [XATO] Kutubxonalar o'rnatilmadi. & pause & exit /b 1 )
  )
  echo Kutubxonalar o'rnatildi.
)

echo Photo Video Studio ochilmoqda...
"%PY%" app.py
if errorlevel 1 ( echo. & echo [XATO] Dastur xato bilan yopildi. & pause )
