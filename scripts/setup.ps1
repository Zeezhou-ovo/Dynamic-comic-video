param(
  [string]$InstallRoot = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\")).Path
if (-not $InstallRoot) {
  $InstallRoot = Join-Path $env:USERPROFILE ".codex\skills\dynamic-comic-video"
}

New-Item -ItemType Directory -Force $InstallRoot | Out-Null
if ((Resolve-Path $RepoRoot).Path -ne (Resolve-Path $InstallRoot).Path) {
  Get-ChildItem -LiteralPath $RepoRoot -Force | Where-Object {
    $_.Name -notin @('.git', '.venv', 'node_modules', 'projects', 'renderer', 'manga-renderer')
  } | Copy-Item -Destination $InstallRoot -Recurse -Force
}
Write-Host "Ready. Dynamic-comic Skill: $InstallRoot"
