# deploy.ps1 — PowerShell wrapper around scripts/deploy.py.
#
# Sets up a venv on first run, installs dependencies once (cached via a
# stamp file), then forwards all arguments to deploy.py. Re-runs are fast.
#
# Usage:
#   .\deploy.ps1                              # full deploy
#   .\deploy.ps1 --dry-run                    # validate only
#   .\deploy.ps1 --skill understanding-foo    # re-upload one skill
#   .\deploy.ps1 --force-recreate slack-token # rotate token
#
# If you get "running scripts is disabled on this system" when invoking
# this, your PowerShell execution policy is locked down. One-time fix:
#   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

$ErrorActionPreference = "Stop"

# Always run from this script's directory so paths resolve regardless of cwd.
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$venv = Join-Path $scriptDir ".venv"
$stamp = Join-Path $venv ".deps-installed"
$reqs = Join-Path $scriptDir "scripts\requirements.txt"
$activate = Join-Path $venv "Scripts\Activate.ps1"

# Pick a python: prefer 'py -3' (Windows launcher) then 'python', then 'python3'.
function Find-Python {
    foreach ($candidate in @("py", "python", "python3")) {
        if (Get-Command $candidate -ErrorAction SilentlyContinue) {
            if ($candidate -eq "py") { return @("py", "-3") }
            return @($candidate)
        }
    }
    throw "Python 3.12+ not found on PATH. See docs/01-prerequisites.md."
}
$pyCmd = Find-Python

# 1. Recreate venv if missing OR broken (Activate.ps1 absent — happens when an
#    earlier wrapper invocation failed midway through and left a partial dir).
if (-not (Test-Path $venv) -or -not (Test-Path $activate)) {
    if (Test-Path $venv) {
        Write-Host "[wrapper] Detected broken venv at $venv (no Activate.ps1); removing and recreating ..."
        Remove-Item -Recurse -Force $venv
    } else {
        Write-Host "[wrapper] Creating venv at $venv ..."
    }
    & $pyCmd[0] @($pyCmd[1..($pyCmd.Length - 1)] + @("-m", "venv", $venv))
    if (-not (Test-Path $activate)) {
        throw "venv creation succeeded but $activate is still missing. Try running '$($pyCmd -join ' ') -m venv .venv' manually to see the underlying error."
    }
}

# 2. Activate the venv.
. $activate

# 3. Install deps if the stamp is missing or older than requirements.txt.
$needInstall = $false
if (-not (Test-Path $stamp)) {
    $needInstall = $true
} elseif ((Get-Item $reqs).LastWriteTime -gt (Get-Item $stamp).LastWriteTime) {
    $needInstall = $true
}
if ($needInstall) {
    Write-Host "[wrapper] Installing dependencies from $reqs ..."
    pip install --quiet --upgrade pip
    pip install --quiet -r $reqs
    if ($LASTEXITCODE -ne 0) { throw "pip install failed" }
    New-Item -ItemType File -Path $stamp -Force | Out-Null
}

# 4. Run the deploy. Forward all args.
python scripts/deploy.py @args
exit $LASTEXITCODE
