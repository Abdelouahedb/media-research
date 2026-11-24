[CmdletBinding()]
param(
    [string]$UserDirectory = [Environment]::GetFolderPath('UserProfile'),
    [switch]$SkipDependencies
)

$ErrorActionPreference = 'Stop'
$source = Join-Path $PSScriptRoot 'media-research'
if (-not (Test-Path -LiteralPath (Join-Path $source 'SKILL.md') -PathType Leaf)) {
    throw 'Extract the complete package before running the installer.'
}

$parents = @(
    (Join-Path $UserDirectory '.claude/skills')
    (Join-Path $UserDirectory '.agents/skills')
)
foreach ($parent in $parents) {
    $destination = Join-Path $parent 'media-research'
    if (Test-Path -LiteralPath $destination) {
        Write-Output "Existing installation preserved: $destination"
        continue
    }
    [void][IO.Directory]::CreateDirectory($parent)
    $staging = Join-Path $parent ('.media-research-install-' + [Guid]::NewGuid())
    Copy-Item -LiteralPath $source -Destination $staging -Recurse
    [IO.Directory]::Move($staging, $destination)
    Write-Output "Installed: $destination"
}

if (-not $SkipDependencies) {
    python -m pip install --user -r (Join-Path $PSScriptRoot 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Could not install Python dependencies.' }
    python -m playwright install chromium
    if ($LASTEXITCODE -ne 0) { throw 'Could not install the Playwright Chromium browser.' }
    foreach ($tool in @('ffmpeg', 'ffprobe')) {
        if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
            Write-Warning "Install $tool and add it to PATH for video support."
        }
    }
}
