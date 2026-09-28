param(
  [string]$InstallRoot = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\")).Path
if (-not $InstallRoot) {
  $InstallRoot = Join-Path $env:USERPROFILE ".codex\skills\dynamic-comic-video"
}

Write-Host "Preparing Dynamic-comic-video at $InstallRoot"
New-Item -ItemType Directory -Force $InstallRoot | Out-Null
if ((Resolve-Path $RepoRoot).Path -ne (Resolve-Path $InstallRoot).Path) {
  Get-ChildItem -LiteralPath $RepoRoot -Force | Where-Object {
    $_.Name -notin @('.git', '.venv', 'node_modules', 'projects', 'renderer', 'manga-renderer')
  } | Copy-Item -Destination $InstallRoot -Recurse -Force
}
Write-Host "Ready. Skill: $InstallRoot"
Write-Host "Copy assets\painted-frame-starter outside the Skill folder for each new video."
Write-Host "Install Node and browser dependencies inside that video project."
