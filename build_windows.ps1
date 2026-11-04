# Build a self-contained Windows executable (Python + FFmpeg + FFprobe).
# Run with BUILD_WINDOWS.bat. Run this script from Windows, not Linux.
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $Root

function Assert-LastExitCode([string]$Step) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed (exit code: $LASTEXITCODE)."
    }
}

Write-Host '[1/6] Checking Python...'
if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 -c 'import sys; print(sys.version)'
    Assert-LastExitCode 'Python check'
    $PythonLauncher = 'py'
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python -c 'import sys; print(sys.version)'
    Assert-LastExitCode 'Python check'
    $PythonLauncher = 'python'
} else {
    throw 'Python is not installed. Install Python from https://www.python.org/downloads/windows/ and run BUILD_WINDOWS.bat again.'
}

$VenvDir = Join-Path $Root '.venv'
$VenvPython = Join-Path $VenvDir 'Scripts\python.exe'
if (-not (Test-Path -LiteralPath $VenvPython)) {
    Write-Host '[2/6] Creating build environment...'
    if ($PythonLauncher -eq 'py') {
        & py -3 -m venv "$VenvDir"
    } else {
        & python -m venv "$VenvDir"
    }
    Assert-LastExitCode 'Creating virtual environment'
} else {
    Write-Host '[2/6] Reusing build environment...'
}

Write-Host '[3/6] Installing build dependency (PyInstaller)...'
& $VenvPython -m pip install --disable-pip-version-check --upgrade pyinstaller
Assert-LastExitCode 'Installing PyInstaller'

$ToolDir = Join-Path $Root 'tools'
$FFmpegExe = Join-Path $ToolDir 'ffmpeg.exe'
$FFprobeExe = Join-Path $ToolDir 'ffprobe.exe'
New-Item -ItemType Directory -Path $ToolDir -Force | Out-Null

if (-not ((Test-Path -LiteralPath $FFmpegExe) -and (Test-Path -LiteralPath $FFprobeExe))) {
    Write-Host '[4/6] Downloading official FFmpeg Windows distribution...'
    $ZipPath = Join-Path $ToolDir 'ffmpeg-release-essentials.zip'
    $CheckPath = Join-Path $ToolDir 'ffmpeg-release-essentials.zip.sha256'
    $Url = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'
    $ChecksumUrl = "$Url.sha256"

    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $Url -OutFile $ZipPath -UseBasicParsing
    Invoke-WebRequest -Uri $ChecksumUrl -OutFile $CheckPath -UseBasicParsing

    $ExpectedText = Get-Content -LiteralPath $CheckPath -Raw
    $HashMatch = [regex]::Match($ExpectedText, '(?i)\b[a-f0-9]{64}\b')
    if (-not $HashMatch.Success) {
        throw 'Unable to parse expected SHA256 checksum. Download not extracted.'
    }
    $ExpectedSha256 = $HashMatch.Value.ToLowerInvariant()
    $ActualSha256 = (Get-FileHash -LiteralPath $ZipPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($ActualSha256 -ne $ExpectedSha256) {
        throw 'FFmpeg download SHA256 mismatch. Download not extracted.'
    }
    Write-Host "  SHA256 verified: $ActualSha256"

    $Extracted = Join-Path $ToolDir 'unpacked'
    if (Test-Path -LiteralPath $Extracted) {
        Remove-Item -LiteralPath $Extracted -Recurse -Force
    }
    Expand-Archive -LiteralPath $ZipPath -DestinationPath $Extracted -Force

    $FfmpegFound = Get-ChildItem -LiteralPath $Extracted -Recurse -File -Filter 'ffmpeg.exe' | Select-Object -First 1
    $FfprobeFound = Get-ChildItem -LiteralPath $Extracted -Recurse -File -Filter 'ffprobe.exe' | Select-Object -First 1
    if (-not $FfmpegFound -or -not $FfprobeFound) {
        throw 'ffmpeg.exe and ffprobe.exe were not found inside the downloaded archive.'
    }

    Copy-Item -LiteralPath $FfmpegFound.FullName -Destination $FFmpegExe -Force
    Copy-Item -LiteralPath $FfprobeFound.FullName -Destination $FFprobeExe -Force
    Remove-Item -LiteralPath $Extracted -Recurse -Force
    Remove-Item -LiteralPath $ZipPath -Force
    Remove-Item -LiteralPath $CheckPath -Force
} else {
    Write-Host '[4/6] Reusing existing FFmpeg binaries in tools folder...'
}

Write-Host '[5/6] Building AudioExtractor.exe...'
& $VenvPython -m PyInstaller `
    --noconfirm --clean --onefile --windowed `
    --name AudioExtractor `
    --add-binary "${FFmpegExe};." `
    --add-binary "${FFprobeExe};." `
    --add-data "THIRD_PARTY_NOTICES.txt;." `
    'audio_extractor_gui.py'
Assert-LastExitCode 'PyInstaller packaging'

$ExePath = Join-Path $Root 'dist\AudioExtractor.exe'
if (-not (Test-Path -LiteralPath $ExePath)) {
    throw "The Windows .exe is missing after packaging: $ExePath"
}

Write-Host '[6/6] Creating shareable release folder and ZIP...'
$ReleaseDir = Join-Path $Root 'RELEASE'
New-Item -ItemType Directory -Path $ReleaseDir -Force | Out-Null
Copy-Item -LiteralPath $ExePath -Destination (Join-Path $ReleaseDir 'AudioExtractor.exe') -Force
Copy-Item -LiteralPath (Join-Path $Root 'README_PARTAGE.txt') -Destination (Join-Path $ReleaseDir 'README_PARTAGE.txt') -Force
Copy-Item -LiteralPath (Join-Path $Root 'THIRD_PARTY_NOTICES.txt') -Destination (Join-Path $ReleaseDir 'THIRD_PARTY_NOTICES.txt') -Force
Copy-Item -LiteralPath (Join-Path $Root 'audio_extractor_gui.py') -Destination (Join-Path $ReleaseDir 'audio_extractor_gui.py') -Force

$ReleaseExe = Join-Path $ReleaseDir 'AudioExtractor.exe'
$Sha = (Get-FileHash -LiteralPath $ReleaseExe -Algorithm SHA256).Hash
Set-Content -LiteralPath (Join-Path $ReleaseDir 'SHA256SUMS.txt') -Value "$Sha  AudioExtractor.exe" -Encoding ASCII

$ReleaseZip = Join-Path $Root 'AudioExtractor_Windows_Portable.zip'
if (Test-Path -LiteralPath $ReleaseZip) { Remove-Item -LiteralPath $ReleaseZip -Force }
Compress-Archive -LiteralPath @(
    $ReleaseExe,
    (Join-Path $ReleaseDir 'README_PARTAGE.txt'),
    (Join-Path $ReleaseDir 'THIRD_PARTY_NOTICES.txt'),
    (Join-Path $ReleaseDir 'audio_extractor_gui.py'),
    (Join-Path $ReleaseDir 'SHA256SUMS.txt')
) -DestinationPath $ReleaseZip -CompressionLevel Optimal

Write-Host "SUCCESS: $ReleaseExe"
Write-Host "SUCCESS: $ReleaseZip"
Write-Host "SHA256 : $Sha"
Write-Host 'IMPORTANT: Binary has NOT been digitally signed. Windows SmartScreen may warn.'
