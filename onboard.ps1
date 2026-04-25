# onboard.ps1 — interactive onboarding wrapper.
#
# Same pattern as deploy.ps1: venv + deps cached, then runs onboard.py.

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$venv = Join-Path $scriptDir ".venv"
$stamp = Join-Path $venv ".deps-installed"
$reqs = Join-Path $scriptDir "scripts\requirements.txt"
$activate = Join-Path $venv "Scripts\Activate.ps1"

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

# Recreate venv if missing OR broken (Activate.ps1 absent — happens when an
# earlier wrapper invocation failed midway through and left a partial dir).
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

. $activate

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

python scripts/onboard.py @args
exit $LASTEXITCODE
