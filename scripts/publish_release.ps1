param(
    [string]$Version = "",
    [switch]$Draft
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

if (-not $Version) {
    $Version = (python -c "from version import APP_VERSION; print(APP_VERSION)").Trim()
}
if (-not $Version) {
    throw "Version berilmadi va version.py dan o'qilmadi."
}

$setup = Join-Path $RepoRoot "release\PhotoVideoStudioSetup-$Version.exe"
if (-not (Test-Path $setup)) {
    Write-Host "Setup topilmadi, release build ishga tushiriladi..."
    & (Join-Path $PSScriptRoot "build_release.ps1")
}
if (-not (Test-Path $setup)) {
    throw "Setup fayl topilmadi: $setup"
}

$tag = "v$Version"
$repo = "Kingprogrammer07/photo_video_studio"

gh auth status | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "gh auth login kerak."
}

$existing = gh release view $tag --repo $repo 2>$null
if ($LASTEXITCODE -eq 0) {
    throw "Release allaqachon bor: $tag"
}

$notes = @"
Photo Video Studio $Version

- Windows installer: PhotoVideoStudioSetup-$Version.exe
- Bundled ffmpeg included for offline video render/convert after install.
- AI features still require internet and a user-provided API key.
"@

$ghArgs = @(
    "release", "create", $tag, $setup,
    "--repo", $repo,
    "--title", "Photo Video Studio $Version",
    "--notes", $notes
)
if ($Draft) {
    $ghArgs += "--draft"
}

gh @ghArgs
Write-Host "Release tayyor: https://github.com/$repo/releases/tag/$tag"
