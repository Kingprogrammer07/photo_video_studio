# Third-Party Notices

## FFmpeg

Photo Video Studio can bundle `ffmpeg.exe` in release installers so video rendering and conversion work offline after installation.

FFmpeg is a third-party project distributed under LGPL/GPL license options depending on the build used. The release builder copies the `ffmpeg.exe` found on the build machine; before public distribution, confirm that the selected FFmpeg build license is suitable for redistribution and include any license files shipped with that build.

- Project: https://ffmpeg.org/
- License information: https://ffmpeg.org/legal.html

## Python Packages

Release builds bundle Python runtime dependencies through PyInstaller. Main runtime packages:

- CustomTkinter
- Pillow
- NumPy

Do not remove package license metadata from the build output when preparing public releases.
