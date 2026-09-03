$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $ProjectRoot

function Find-Python {
    foreach ($Candidate in @("py", "python")) {
        if (Get-Command $Candidate -ErrorAction SilentlyContinue) {
            if ($Candidate -eq "py") { return @("py", "-3") }
            return @("python")
        }
    }
    throw "Python 3 was not found. Install Python 3.11 or 3.12 from https://www.python.org/downloads/"
}

$PythonCommand = Find-Python
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$RequirementsHashFile = Join-Path $ProjectRoot ".venv\requirements.sha256"
$CurrentHash = (Get-FileHash -Algorithm SHA256 (Join-Path $ProjectRoot "requirements.txt")).Hash

if (-not (Test-Path -LiteralPath $VenvPython)) {
    Write-Host "Creating the Python virtual environment..."
    $PythonExecutable = $PythonCommand[0]
    $PythonArguments = @($PythonCommand | Select-Object -Skip 1)
    & $PythonExecutable @PythonArguments -m venv .venv
}

$InstalledHash = if (Test-Path -LiteralPath $RequirementsHashFile) {
    Get-Content -Raw -LiteralPath $RequirementsHashFile
} else { "" }

if ($InstalledHash.Trim() -ne $CurrentHash) {
    Write-Host "Downloading the required packages and FFmpeg..."
    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install -r requirements.txt
    Set-Content -NoNewline -LiteralPath $RequirementsHashFile -Value $CurrentHash
}

Write-Host "Starting the app..."
& $VenvPython app.py
