param(
    [string]$RemoteUrl = "https://github.com/MuhammadAzzaRayyan/finance-tracker.git",
    [string]$Branch = 'main',
    [string]$CommitMessage = 'Add personal finance static site and OCR features'
)

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "git is not installed or not in PATH. Install Git first: https://git-scm.com/download/win"
    exit 1
}

Push-Location -Path (Split-Path -Path $MyInvocation.MyCommand.Definition -Parent)

if (-not (Test-Path .git)) {
    git init
}

git add .
try {
    git commit -m "$CommitMessage" -q
} catch {
    Write-Host "No changes to commit or commit failed. Continuing..."
}

try { git remote remove origin 2>$null } catch {}
git remote add origin $RemoteUrl
git branch -M $Branch

Write-Host "Pushing to $RemoteUrl (branch $Branch)..."
git push -u origin $Branch

Pop-Location
