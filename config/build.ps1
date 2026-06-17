param(
    [switch]$SkipInstaller,
    [switch]$SkipExe,
    [switch]$SkipRelease,
    [switch]$AllowMissingEnv
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

function Build-ReleaseAssets {
    param(
        [string]$Version,
        [string]$ExePath,
        [string]$InstallerPath,
        [string]$ProjectRoot
    )

    $releaseDir = Join-Path $ProjectRoot ("dist\release")
    $exeName = Split-Path $ExePath -Leaf
    $portableZip = Join-Path $ProjectRoot ("dist\ChatList-{0}-portable.zip" -f $Version)

    if (Test-Path $releaseDir) {
        Remove-Item $releaseDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null

    Copy-Item $ExePath (Join-Path $releaseDir $exeName)
    if (Test-Path $InstallerPath) {
        Copy-Item $InstallerPath $releaseDir
    }

    if (Test-Path $portableZip) {
        Remove-Item $portableZip -Force
    }
    Compress-Archive -Path $ExePath -DestinationPath $portableZip -Force

    $hashLines = @()
    Get-ChildItem $releaseDir -File | ForEach-Object {
        $hash = Get-FileHash $_.FullName -Algorithm SHA256
        $hashLines += ("{0}  {1}" -f $hash.Hash.ToLower(), $_.Name)
    }
    $hashLines | Set-Content (Join-Path $releaseDir "SHA256SUMS.txt") -Encoding ASCII

    Write-Host ("Release assets: {0}" -f $releaseDir)
    Write-Host ("Portable zip: {0}" -f $portableZip)
}

$Version = Get-AppVersion
$ExeName = "chatlist-$Version.exe"
$ExePath = Join-Path $Root ("dist\{0}" -f $ExeName)
$InstallerName = "ChatList-$Version-Setup.exe"
$InstallerPath = Join-Path $Root ("dist\{0}" -f $InstallerName)
$EnvFile = Join-Path $Root "config\.env"

Write-Host "Building ChatList $Version"

if (-not (Test-Path $EnvFile)) {
    if ($AllowMissingEnv) {
        Write-Warning "config/.env not found - building without embedded API keys."
    }
    else {
        throw @"
config/.env is required for release build.
Create config/.env with OPENROUTER_API_KEY before building.
For local dev builds without keys use: .\config\build.ps1 -AllowMissingEnv
"@
    }
}

if (-not $SkipExe) {
    python -m PyInstaller config/chatlist.spec
    if (-not (Test-Path $ExePath)) {
        throw "Executable not found: $ExePath"
    }
    Write-Host ("Done: {0}" -f $ExePath)
    if (Test-Path $EnvFile) {
        Write-Host "API keys embedded inside exe (user sees only one file)"
    }
}
elseif (-not (Test-Path $ExePath)) {
    throw "Executable not found: $ExePath. Run build without -SkipExe first."
}

if ($SkipInstaller) {
    if (-not $SkipRelease) {
        Build-ReleaseAssets -Version $Version -ExePath $ExePath -InstallerPath $InstallerPath -ProjectRoot $Root
    }
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

Write-Host "Building installer (single exe output)..."
& $IsccPath "/DAppVersion=$Version" (Join-Path $Root "config\chatlist.iss")

if (-not (Test-Path $InstallerPath)) {
    throw "Installer not created: $InstallerPath"
}

Write-Host ("Done: {0}" -f $InstallerPath)

if (-not $SkipRelease) {
    Build-ReleaseAssets -Version $Version -ExePath $ExePath -InstallerPath $InstallerPath -ProjectRoot $Root
}
