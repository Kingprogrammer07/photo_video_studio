@echo off
title Photo Video Studio - EXE yasash
echo Bir martalik: standalone .exe yasaladi (Python'siz ochiladi)...
python -m pip install pyinstaller customtkinter pillow numpy
pyinstaller --noconfirm --onefile --windowed --name PhotoVideoStudio ^
  --add-data "fonts;fonts" ^
  --hidden-import music --hidden-import studio_engine --hidden-import image_enhance --hidden-import pvs_storage ^
  --collect-all customtkinter ^
  app.py
echo.
echo Tayyor:  dist\PhotoVideoStudio.exe
echo (Eslatma: ffmpeg baribir PATH da bo'lishi kerak.)
pause
