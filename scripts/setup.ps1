param(
  [string]$InstallRoot = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\")).Path
if (-not $InstallRoot) {
  $InstallRoot = Join-Path $env:USERPROFILE ".codex\skills\dynamic-comic-video"
}
$PaintedRoot = Join-Path (Split-Path -Parent $InstallRoot) "code-painted-video"

New-Item -ItemType Directory -Force $InstallRoot | Out-Null
New-Item -ItemType Directory -Force $PaintedRoot | Out-Null
if ((Resolve-Path $RepoRoot).Path -ne (Resolve-Path $InstallRoot).Path) {
  Get-ChildItem -LiteralPath $RepoRoot -Force | Where-Object {
    $_.Name -notin @('.git', '.venv', 'node_modules', 'projects', 'renderer', 'manga-renderer', 'skills')
  } | Copy-Item -Destination $InstallRoot -Recurse -Force
}
if ((Resolve-Path (Join-Path $RepoRoot "skills\code-painted-video")).Path -ne (Resolve-Path $PaintedRoot).Path) {
  Get-ChildItem -LiteralPath (Join-Path $RepoRoot "skills\code-painted-video") -Force |
    Copy-Item -Destination $PaintedRoot -Recurse -Force
}
Write-Host "Ready. Remotion Skill: $InstallRoot"
Write-Host "Ready. Code-painted Skill: $PaintedRoot"
Write-Host "Copy the painted-frame starter outside the Skill folder for each new code-painted video."
