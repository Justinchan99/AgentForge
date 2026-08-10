[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$SourceRoot,
    [switch]$Yes,
    [switch]$SkipTools,
    [switch]$Init,
    [string]$Project = "."
)

$ErrorActionPreference = "Stop"

function Find-Python {
    foreach ($candidate in @("python", "python3", "py")) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($command) {
            if ($candidate -eq "py") {
                & $candidate -3 -c "import sys; assert sys.version_info >= (3, 9)" 2>$null
            } else {
                & $candidate -c "import sys; assert sys.version_info >= (3, 9)" 2>$null
            }
            if ($LASTEXITCODE -eq 0) { return $candidate }
        }
    }
    $localAppData = [Environment]::GetFolderPath("LocalApplicationData")
    $pythonRoot = Join-Path $localAppData "Programs\Python"
    if (Test-Path -LiteralPath $pythonRoot) {
        $installed = Get-ChildItem -LiteralPath $pythonRoot -Filter "python.exe" -Recurse -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending
        foreach ($candidate in $installed) {
            & $candidate.FullName -c "import sys; assert sys.version_info >= (3, 9)" 2>$null
            if ($LASTEXITCODE -eq 0) { return $candidate.FullName }
        }
    }
    throw "Python 3.9 or newer is required. Install Python, then rerun this installer."
}

function Refresh-ProcessPath {
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machinePath;$userPath"
}

function Add-UserPathEntry([string]$Entry) {
    if (-not (Test-Path -LiteralPath $Entry)) { return }
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $pathEntries = @($userPath -split ";" | Where-Object { $_ })
    if ($pathEntries -notcontains $Entry) {
        [Environment]::SetEnvironmentVariable("Path", ((@($Entry) + $pathEntries) -join ";"), "User")
        Write-Host "Added $Entry to the user PATH."
    }
    Refresh-ProcessPath
}

function Test-Tool([string[]]$Names) {
    foreach ($name in $Names) {
        if (Get-Command $name -ErrorAction SilentlyContinue) { return $true }
    }
    return $false
}

function Install-WingetPackage([string]$Id) {
    Write-Host "Installing $Id ..."
    & winget install --id $Id --exact --accept-package-agreements --accept-source-agreements --silent
    if ($LASTEXITCODE -ne 0) { Write-Warning "winget could not install $Id (exit $LASTEXITCODE)" }
}

$python = $null
try { $python = Find-Python } catch {
    if ($SkipTools) { throw }
    $installPython = $Yes
    if (-not $Yes) {
        $answer = Read-Host "Python 3.9+ is missing. Install Python 3.12 with winget? [y/N]"
        $installPython = $answer -match "^[Yy]"
    }
    if (-not $installPython) { throw }
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "winget is unavailable. Install Python 3.9+ manually, then rerun this installer."
    }
    Install-WingetPackage "Python.Python.3.12"
    Refresh-ProcessPath
    $python = Find-Python
}
Refresh-ProcessPath
Write-Host "AgentForge Environment Check"
Write-Host "OS:           $([System.Environment]::OSVersion.VersionString)"
Write-Host "Architecture: $env:PROCESSOR_ARCHITECTURE"
Write-Host "Mode:         Windows Local Development"
$elevated = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
Write-Host "Elevated:     $($elevated.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))"

function Test-ProjectLanguage([string]$Language) {
    $detector = Join-Path $SourceRoot "scripts\detect_environment.py"
    if ($python -eq "py") {
        & py -3 $detector --project $Project --has-language $Language
    } else {
        & $python $detector --project $Project --has-language $Language
    }
    return $LASTEXITCODE -eq 0
}

$needsCpp = Test-ProjectLanguage "cpp"
$needsPython = Test-ProjectLanguage "python"
if ($needsCpp) {
    # Some LLVM winget releases do not register their binary directory.
    Add-UserPathEntry "C:\Program Files\LLVM\bin"
}

$toolDefinitions = @(
    @{ Name = "git"; Commands = @("git"); Package = "Git.Git" },
    @{ Name = "node"; Commands = @("node"); Package = "OpenJS.NodeJS.LTS" },
    @{ Name = "npm"; Commands = @("npm", "npm.cmd"); Package = "OpenJS.NodeJS.LTS" },
    @{ Name = "cmake"; Commands = @("cmake"); Package = "Kitware.CMake" },
    @{ Name = "ninja"; Commands = @("ninja"); Package = "Ninja-build.Ninja" },
    @{ Name = "opencode"; Commands = @("opencode", "opencode.cmd", "opencode.exe"); Package = $null },
    @{ Name = "VS Code"; Commands = @("code", "code.cmd"); Package = "Microsoft.VisualStudioCode" }
)
if ($needsCpp) {
    $toolDefinitions += @{ Name = "clangd"; Commands = @("clangd", "clangd.exe"); Package = "LLVM.LLVM" }
}
if ($needsPython) {
    $toolDefinitions += @{ Name = "pyright"; Commands = @("pyright-langserver", "pyright-langserver.cmd"); Package = $null }
}
$missing = @($toolDefinitions | Where-Object { -not (Test-Tool $_.Commands) })
$wingetPackageIds = @($missing | ForEach-Object { $_.Package } | Where-Object { $_ } | Sort-Object -Unique)

Write-Host "`nInstalled:"
$toolDefinitions | Where-Object { Test-Tool $_.Commands } | ForEach-Object { Write-Host "  [OK] $($_.Name)" }
Write-Host "`nMissing:"
if ($missing.Count -eq 0) { Write-Host "  none" } else { $missing | ForEach-Object { Write-Host "  [--] $($_.Name)" } }

$installMissing = -not $SkipTools
if ($installMissing -and $missing.Count -gt 0 -and -not $Yes) {
    $answer = Read-Host "Install missing development tools? [y/N]"
    $installMissing = $answer -match "^[Yy]"
}
if ($installMissing -and $wingetPackageIds.Count -gt 0) {
        if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
            Write-Warning "winget is unavailable; install the missing tools manually."
        } else {
            foreach ($packageId in $wingetPackageIds) { Install-WingetPackage $packageId }
            Refresh-ProcessPath
            Add-UserPathEntry "C:\Program Files\LLVM\bin"
        }
}

if ($installMissing -and (Test-Tool @("npm", "npm.cmd"))) {
    $npmPackages = @("opencode-ai")
    if ($needsPython) { $npmPackages += "pyright" }
    foreach ($package in $npmPackages) {
        $commandName = if ($package -eq "pyright") { "pyright-langserver" } else { "opencode" }
        if (-not (Test-Tool @($commandName, "$commandName.cmd"))) {
            Write-Host "Installing npm package $package ..."
            & npm install --global $package
            if ($LASTEXITCODE -ne 0) { Write-Warning "npm could not install $package (exit $LASTEXITCODE)" }
        }
    }
}

$localAppData = [Environment]::GetFolderPath("LocalApplicationData")
$installRoot = Join-Path $localAppData "AgentForge"
$binRoot = Join-Path $installRoot "bin"
New-Item -ItemType Directory -Force -Path $installRoot, $binRoot | Out-Null

$resolvedSource = (Resolve-Path -LiteralPath $SourceRoot).Path.TrimEnd('\')
$resolvedInstall = (Resolve-Path -LiteralPath $installRoot).Path.TrimEnd('\')
if (-not $resolvedSource.Equals($resolvedInstall, [StringComparison]::OrdinalIgnoreCase)) {
    foreach ($item in @("install.sh", "install.ps1", "agentforge", "agentforge.cmd", "README.md", "LICENSE", "scripts", "templates", "examples", "docs")) {
        $source = Join-Path $SourceRoot $item
        if (Test-Path -LiteralPath $source) {
            Copy-Item -LiteralPath $source -Destination $installRoot -Recurse -Force
        }
    }
}

$launcher = Join-Path $binRoot "agentforge.cmd"
$pythonInvocation = if ($python -eq "py") { 'py -3' } else { '"' + $python + '"' }
$launcherContent = "@echo off`r`n$pythonInvocation `"$installRoot\scripts\agentforge.py`" %*`r`n"
Set-Content -LiteralPath $launcher -Value $launcherContent -Encoding ASCII

Add-UserPathEntry $binRoot
$env:Path = "$binRoot;$env:Path"
Write-Host "AgentForge CLI installed: $launcher"

if ($python -eq "py") {
    & py -3 "$installRoot\scripts\configure_lsp.py" --migrate-global
} else {
    & $python "$installRoot\scripts\configure_lsp.py" --migrate-global
}
if ($LASTEXITCODE -ne 0) { Write-Warning "Legacy global OpenCode configuration could not be inspected; it was preserved." }

if ($Init) {
    & $launcher init $Project
    exit $LASTEXITCODE
}
exit 0
