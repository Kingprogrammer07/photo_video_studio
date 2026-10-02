# Release And Install Guide

Last updated: 2026-10-02

## Build A Windows Installer

1. Install build tools once:
   - Python 3.14 or current project Python
   - ffmpeg available on `PATH`, or set `PVS_FFMPEG=C:\path\to\ffmpeg.exe`
   - Inno Setup 6 (`build_exe.bat -InstallBuildTools` can install it with `winget`)
2. Run:

```powershell
build_exe.bat
```

The script creates:

- `dist\PhotoVideoStudio\PhotoVideoStudio.exe`
- `dist\PhotoVideoStudio\ffmpeg\bin\ffmpeg.exe`
- `release\PhotoVideoStudioSetup-<version>.exe`

Use `scripts\build_release.ps1 -SkipInstaller` to test only the PyInstaller app folder.

## Publish An Update

1. Update `APP_VERSION` in `version.py`.
2. Run the full test/build checks.
3. Publish to GitHub Releases:

```powershell
scripts\publish_release.ps1
```

The app checks `https://github.com/Kingprogrammer07/photo_video_studio/releases/latest`. Users click `Sozlamalar -> Yangilanishni tekshirish`, then `Yuklab olish` to download and run the new setup.

## User Install Behavior

- Installer requires internet before install and stops with a clear message when offline.
- After install, slideshow render and Video Tools work offline because ffmpeg is bundled.
- OpenAI AI features require internet and a user-provided API key.

## API Key Testing

Inside the app:

1. Open `Sozlamalar`.
2. Paste key into `OpenAI API key`.
3. Click `Saqlash`.
4. Click `Tekshirish`.

Keys are stored in Windows Credential Manager/keyring, not in repo files or `settings.json`. Use `docs\OPENAI_MANUAL_TEST.md` for full AI validation.
