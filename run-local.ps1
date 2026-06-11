Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force
Push-Location $PSScriptRoot
if (-Not (Test-Path .venv)) {
    python -m venv .venv
}
& .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
Pop-Location