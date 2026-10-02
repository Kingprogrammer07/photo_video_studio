@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Photo Video Studio - Setup yasash

echo ============================================
echo   Photo Video Studio release build
echo   EXE papka + Windows Setup yaratiladi
echo ============================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\build_release.ps1" %*
if errorlevel 1 (
  echo.
  echo [XATO] Build tugamadi.
  echo Agar Inno Setup yo'q bo'lsa: build_exe.bat -InstallBuildTools
  echo.
  pause
  exit /b 1
)

echo.
echo Tayyor: release papkasini tekshiring.
pause
