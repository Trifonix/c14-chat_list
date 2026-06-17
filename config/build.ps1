param(
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Version = python -c "import sys; sys.path.insert(0, 'config'); from load_version import load_version; print(load_version())"
if (-not $Version) {
    throw "Не удалось прочитать версию из version.py"
}

Write-Host "Сборка ChatList $Version"

python -m PyInstaller config/chatlist.spec

$ExeName = "chatlist-$Version.exe"
$ExePath = Join-Path $Root "dist\$ExeName"
if (-not (Test-Path $ExePath)) {
    throw "Не найден исполняемый файл: $ExePath"
}

Write-Host "Готово: dist\$ExeName"

if ($SkipInstaller) {
    return
}

$Iscc = Get-Command iscc -ErrorAction SilentlyContinue
if (-not $Iscc) {
    Write-Host "Inno Setup (iscc) не найден — установщик не собран."
    Write-Host "Установите Inno Setup и выполните:"
    Write-Host "  iscc /DAppVersion=$Version config\chatlist.iss"
    return
}

& iscc "/DAppVersion=$Version" (Join-Path $Root "config\chatlist.iss")
Write-Host "Готово: dist\ChatList-$Version-Setup.exe"
