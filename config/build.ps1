param(
    [switch]$SkipInstaller,
    [switch]$SkipExe
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Get-AppVersion {
    $version = python -c "import sys; sys.path.insert(0, 'config'); from load_version import load_version; print(load_version())"
    if (-not $version) {
        throw "Failed to read version from version.py"
    }
    return $version.Trim()
}

function Find-InnoSetupCompiler {
    $iscc = Get-Command iscc -ErrorAction SilentlyContinue
    if ($iscc) {
        return $iscc.Source
    }

    $candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )
    foreach ($path in $candidates) {
        if (Test-Path $path) {
            return $path
        }
    }

    return $null
}

$Version = Get-AppVersion
$ExeName = "chatlist-$Version.exe"
$ExePath = Join-Path $Root "dist\$ExeName"
$InstallerName = "ChatList-$Version-Setup.exe"
$InstallerPath = Join-Path $Root "dist\$InstallerName"

Write-Host "Building ChatList $Version"

if (-not $SkipExe) {
    python -m PyInstaller config/chatlist.spec
    if (-not (Test-Path $ExePath)) {
        throw "Executable not found: $ExePath"
    }
    Write-Host "Done: dist\$ExeName"
} elseif (-not (Test-Path $ExePath)) {
    throw "Executable not found: $ExePath. Run build without -SkipExe first."
}

if ($SkipInstaller) {
    return
}

$IsccPath = Find-InnoSetupCompiler
if (-not $IsccPath) {
    Write-Host ""
    Write-Host "Inno Setup (ISCC.exe) not found."
    Write-Host "Install Inno Setup 6: https://jrsoftware.org/isdl.php"
    Write-Host "Then run: .\config\build.ps1 -SkipExe"
    exit 1
}

Write-Host "Building installer..."
& $IsccPath "/DAppVersion=$Version" (Join-Path $Root "config\chatlist.iss")

if (-not (Test-Path $InstallerPath)) {
    throw "Installer not created: $InstallerPath"
}

Write-Host "Done: dist\$InstallerName"
