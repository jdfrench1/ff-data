[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [int]$Season,

    [Parameter(Mandatory = $true)]
    [int]$Week,

    [switch]$ForceRefresh,

    [string]$LogDirectory = "logs"
)

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$projectRoot = (Resolve-Path (Join-Path $scriptRoot "..")).Path
$srcPath = Join-Path $projectRoot "src"

if ($env:PYTHONPATH) {
    $env:PYTHONPATH = "$srcPath;${env:PYTHONPATH}"
} else {
    $env:PYTHONPATH = $srcPath
}

$venvPath = Join-Path $projectRoot ".venv"
$venvScripts = Join-Path $venvPath "Scripts"
$pythonFromVenv = Join-Path $venvScripts "python.exe"
$pythonExecutable = if (Test-Path $pythonFromVenv) { $pythonFromVenv } else { "python" }

if ([System.IO.Path]::IsPathRooted($LogDirectory)) {
    $resolvedLogDir = $LogDirectory
} else {
    $resolvedLogDir = Join-Path $projectRoot $LogDirectory
}

if (-not (Test-Path $resolvedLogDir)) {
    New-Item -ItemType Directory -Path $resolvedLogDir | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logFile = Join-Path $resolvedLogDir ("update-week-{0}-w{1}-{2}.log" -f $Season, $Week, $timestamp)

$arguments = @("-m", "nfldb.cli", "update-week", "--season", $Season, "--week", $Week)
if ($ForceRefresh.IsPresent) {
    $arguments += "--force-refresh"
}

"[$(Get-Date -Format 's')] Starting weekly update for season $Season week $Week." | Tee-Object -FilePath $logFile
"[$(Get-Date -Format 's')] Using python executable: $pythonExecutable" | Tee-Object -FilePath $logFile -Append
"[$(Get-Date -Format 's')] PYTHONPATH set to $env:PYTHONPATH" | Tee-Object -FilePath $logFile -Append

& $pythonExecutable @arguments 2>&1 | Tee-Object -FilePath $logFile -Append
$exitCode = $LASTEXITCODE

"[$(Get-Date -Format 's')] Finished with exit code $exitCode." | Tee-Object -FilePath $logFile -Append

exit $exitCode