# run_once.ps1 — PowerShell wrapper around scripts/run_once.py.
#
# Activates the project venv (created by deploy.ps1) and forwards all
# arguments. Run AFTER a successful deploy.
#
# Usage:
#   .\run_once.ps1                    # standard kickoff
#   .\run_once.ps1 --kickoff "..."    # custom kickoff message
#   .\run_once.ps1 --dry-run          # tell agent to log, not post
#   .\run_once.ps1 --no-stream        # send kickoff and exit

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$venv = Join-Path $scriptDir ".venv"
$activate = Join-Path $venv "Scripts\Activate.ps1"

if (-not (Test-Path $activate)) {
    Write-Error "No working venv at $venv — run .\deploy.ps1 first."
    exit 1
}

. $activate

python scripts/run_once.py @args
exit $LASTEXITCODE
