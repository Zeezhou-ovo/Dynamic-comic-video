# Install the dynamic-comic-video skill for any AI agent.
#
#   .\scripts\setup.ps1                        # check the environment only
#   .\scripts\setup.ps1 -Dest <skill dir>      # also copy the skill there (several allowed)
#   .\scripts\setup.ps1 <skill dir>            # same as -Dest (older usage)
#
# The skill is agent-neutral: SKILL.md plus local Python/Node scripts. Copy it
# into whatever skill folder your AI tool reads, or just point the agent at
# SKILL.md in this repository.
param(
  [Parameter(Position = 0)]
  [string[]]$Dest = @()
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\")).Path

foreach ($Target in $Dest) {
  New-Item -ItemType Directory -Force $Target | Out-Null
  if ((Resolve-Path $RepoRoot).Path -ne (Resolve-Path $Target).Path) {
    Get-ChildItem -LiteralPath $RepoRoot -Force | Where-Object {
      $_.Name -notin @('.git', '.venv', 'node_modules', 'projects', 'renderer', 'manga-renderer')
    } | Copy-Item -Destination $Target -Recurse -Force
  }
  Write-Host "Installed skill: $(Join-Path (Resolve-Path $Target).Path 'SKILL.md')"
}

if ($Dest.Count -eq 0) {
  Write-Host "No copy made. Point your AI agent at: $(Join-Path $RepoRoot 'SKILL.md')"
  Write-Host "(or rerun with -Dest <the skill folder your AI tool reads>)"
}

$Python = Get-Command python -ErrorAction SilentlyContinue
if (-not $Python) { $Python = Get-Command py -ErrorAction SilentlyContinue }
if ($Python) {
  Write-Host "Environment check (fix commands are listed for anything missing):"
  & $Python.Source (Join-Path $RepoRoot "scripts\doctor.py")
} else {
  Write-Warning "Python 3.10+ not found; install it, then run: pip install -r requirements.txt"
}
foreach ($Tool in @('ffmpeg', 'ffprobe')) {
  if (-not (Get-Command $Tool -ErrorAction SilentlyContinue)) {
    Write-Warning "$Tool not found; preview loudness and the delivery gate need it."
  }
}
