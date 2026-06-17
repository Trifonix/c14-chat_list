param(
    [switch]$SkipInstaller,
    [switch]$SkipExe,
    [switch]$SkipPortable
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

function Build-PortablePackage {
    param(
        [string]$Version,
        [string]$ExePath,
        [string]$ProjectRoot
    )

    $portableDir = Join-Path $ProjectRoot "dist\ChatList-$Version-portable"
    $configDir = Join-Path $portableDir "config"
    $envSrc = Join-Path $ProjectRoot "config\.env"
    $envExample = Join-Path $ProjectRoot "config\.env.example"

    if (Test-Path $portableDir) {
        Remove-Item $portableDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $configDir -Force | Out-Null

    Copy-Item $ExePath $portableDir
    Copy-Item (Join-Path $ProjectRoot "app.ico") $portableDir

    if (Test-Path $envSrc) {
        Copy-Item $envSrc (Join-Path $configDir ".env")
        Write-Host "Portable: config\.env included"
    } elseif (Test-Path $envExample) {
        Copy-Item $envExample (Join-Path $configDir ".env.example")
        Write-Warning "config\.env not found — portable folder has .env.example only"
    }

    Write-Host "Portable package: dist\ChatList-$Version-portable\"
}

$Version = Get-AppVersion
$ExeName = "chatlist-$Version.exe"
$ExePath = Join-Path $Root "dist\$ExeName"
$InstallerName = "ChatList-$Version-Setup.exe"
$InstallerPath = Join-Path $Root "dist\$InstallerName"
$EnvFile = Join-Path $Root "config\.env"

Write-Host "Building ChatList $Version"

if (-not (Test-Path $EnvFile)) {
    Write-Warning "config\.env not found."
    Write-Warning "For out-of-the-box distribution, create config\.env with your API keys before build."
    Write-Warning "The exe will embed .env only if config\.env exists at build time."
}

if (-not $SkipExe) {
    python -m PyInstaller config/chatlist.spec
    if (-not (Test-Path $ExePath)) {
        throw "Executable not found: $ExePath"
    }
    Write-Host "Done: dist\$ExeName"
    if (Test-Path $EnvFile) {
        Write-Host "Embedded .env in exe (single-file portable works without extra files)"
    }
} elseif (-not (Test-Path $ExePath)) {
    throw "Executable not found: $ExePath. Run build without -SkipExe first."
}

if (-not $SkipPortable) {
    Build-PortablePackage -Version $Version -ExePath $ExePath -ProjectRoot $Root
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
