[CmdletBinding()]
param(
    [switch]$Yes,
    [switch]$SkipTools,
    [switch]$Init,
    [string]$Project = "."
)

$ErrorActionPreference = "Stop"
$installer = Join-Path $PSScriptRoot "scripts\install_windows.ps1"
& $installer -SourceRoot $PSScriptRoot -Yes:$Yes -SkipTools:$SkipTools -Init:$Init -Project $Project
exit $LASTEXITCODE
