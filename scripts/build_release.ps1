param(
    [switch]$SkipInstaller,
    [switch]$InstallBuildTools
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

function Get-AppVersion {
    $version = python -c "from version import APP_VERSION; print(APP_VERSION)"
    if (-not $version) { throw "APP_VERSION topilmadi." }
    return $version.Trim()
}

function Find-Ffmpeg {
    if ($env:PVS_FFMPEG -and (Test-Path $env:PVS_FFMPEG)) {
        return (Resolve-Path $env:PVS_FFMPEG).Path
    }

    $cmd = Get-Command ffmpeg -ErrorAction SilentlyContinue
    if ($cmd -and (Test-Path $cmd.Source)) {
        return $cmd.Source
    }

    $candidates = @(
        "C:\ffmpeg\bin\ffmpeg.exe",
        "$env:USERPROFILE\ffmpeg\bin\ffmpeg.exe",
        "C:\Program Files\ffmpeg\bin\ffmpeg.exe"
    )
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return (Resolve-Path $candidate).Path
        }
    }

    throw "ffmpeg.exe topilmadi. ffmpeg o'rnating yoki PVS_FFMPEG env var bilan manzil bering."
}

function Find-Iscc {
    $cmd = Get-Command iscc -ErrorAction SilentlyContinue
    if ($cmd -and (Test-Path $cmd.Source)) {
        return $cmd.Source
    }

    $candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return (Resolve-Path $candidate).Path
        }
    }
    return ""
}

Write-Host "Photo Video Studio release build boshlanmoqda..."
$Version = Get-AppVersion
Write-Host "Version: $Version"

Write-Host "Python kutubxonalari tekshirilmoqda..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller

$distApp = Join-Path $RepoRoot "dist\PhotoVideoStudio"
if (Test-Path $distApp) {
    Remove-Item -LiteralPath $distApp -Recurse -Force
}

$pyInstallerArgs = @(
    "--noconfirm",
    "--clean",
    "--onedir",
    "--windowed",
    "--name", "PhotoVideoStudio",
    "--paths", "video_converter\src",
    "--add-data", "fonts;fonts",
    "--add-data", "previews;previews",
    "--hidden-import", "music",
    "--hidden-import", "studio_engine",
    "--hidden-import", "image_enhance",
    "--hidden-import", "pvs_storage",
    "--hidden-import", "starter_pack",
    "--hidden-import", "connectivity",
    "--hidden-import", "runtime_paths",
    "--hidden-import", "updater",
    "--hidden-import", "version",
    "--hidden-import", "video_converter.converter",
    "--collect-all", "customtkinter",
    "app.py"
)

Write-Host "PyInstaller onedir build..."
python -m PyInstaller @pyInstallerArgs

if (-not (Test-Path (Join-Path $distApp "PhotoVideoStudio.exe"))) {
    throw "PyInstaller build tugadi, lekin PhotoVideoStudio.exe topilmadi."
}

Write-Host "Bundled ffmpeg joylanmoqda..."
$ffmpeg = Find-Ffmpeg
$ffmpegDest = Join-Path $distApp "ffmpeg\bin"
New-Item -ItemType Directory -Force -Path $ffmpegDest | Out-Null
Copy-Item -LiteralPath $ffmpeg -Destination (Join-Path $ffmpegDest "ffmpeg.exe") -Force

if (Test-Path "THIRD_PARTY_NOTICES.md") {
    Copy-Item -LiteralPath "THIRD_PARTY_NOTICES.md" -Destination (Join-Path $distApp "THIRD_PARTY_NOTICES.md") -Force
}

if ($SkipInstaller) {
    Write-Host "Installer o'tkazib yuborildi. EXE papka: $distApp"
    exit 0
}

$iscc = Find-Iscc
if (-not $iscc -and $InstallBuildTools) {
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget) {
        throw "Inno Setup topilmadi va winget mavjud emas."
    }
    Write-Host "Inno Setup o'rnatilmoqda..."
    winget install --id JRSoftware.InnoSetup -e --accept-package-agreements --accept-source-agreements
    $iscc = Find-Iscc
}

if (-not $iscc) {
    throw "Inno Setup topilmadi. https://jrsoftware.org/isdl.php dan o'rnating yoki scripts\build_release.ps1 -InstallBuildTools ishlating."
}

New-Item -ItemType Directory -Force -Path (Join-Path $RepoRoot "release") | Out-Null
Write-Host "Installer yaratilmoqda..."
& $iscc "/DAppVersion=$Version" "/DSourceDir=$distApp" "installer\PhotoVideoStudio.iss"

$setup = Join-Path $RepoRoot "release\PhotoVideoStudioSetup-$Version.exe"
if (-not (Test-Path $setup)) {
    throw "Installer kutilgan joyda topilmadi: $setup"
}

Write-Host "Tayyor:"
Write-Host "  App:   $distApp"
Write-Host "  Setup: $setup"
