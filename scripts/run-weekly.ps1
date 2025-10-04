[CmdletBinding()]
param(
    [Parameter()][int]$Season = (Get-Date).Year,
    [Parameter()][Nullable[int]]$Week,
    [Parameter()][string]$Output = "nfl_weekly_stats.csv",
    [Parameter()][string]$EnvFile,
    [Parameter()][string]$LogFile,
    [switch]$AllowEmpty,
    [switch]$SkipPostgres
)

$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Path $PSCommandPath -Parent
$repoRoot = Split-Path -Path $scriptDir -Parent
Push-Location $repoRoot

try {
    $verboseRequested = $PSBoundParameters.ContainsKey('Verbose') -or $VerbosePreference -eq 'Continue'
    if ($LogFile) {
        $logDirectory = Split-Path -Path $LogFile -Parent
        if ($logDirectory -and -not (Test-Path $logDirectory)) {
            New-Item -ItemType Directory -Path $logDirectory | Out-Null
        }
    }

    $pythonPath = Join-Path $repoRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path $pythonPath)) {
        $pythonPath = 'python'
    }

    $loaderArgs = @('scripts\load_weekly_data.py', '--season', $Season.ToString(), '--output', $Output)
    if ($Week.HasValue) {
        $loaderArgs += @('--week', $Week.Value.ToString())
    }
    if ($AllowEmpty.IsPresent) {
        $loaderArgs += '--allow-empty'
    }
    if ($verboseRequested) {
        $loaderArgs += '--verbose'
    }
    if ($LogFile) {
        $loaderArgs += @('--log-file', $LogFile)
        if (-not $verboseRequested) {
            $loaderArgs += '--quiet'
        }
    }

    & $pythonPath @loaderArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Weekly data loader exited with code $LASTEXITCODE"
    }

    if (-not $SkipPostgres.IsPresent) {
        $uploadScript = Join-Path $repoRoot 'scripts\upload_weekly_to_postgres.py'
        if (Test-Path $uploadScript) {
            $uploadArgs = @('--csv-path', $Output)
            if ($EnvFile) {
                $uploadArgs += @('--env-file', $EnvFile)
            }
            if ($LogFile) {
                $uploadArgs += @('--log-file', $LogFile)
                if (-not $verboseRequested) {
                    $uploadArgs += '--quiet'
                }
            }
            if ($verboseRequested) {
                $uploadArgs += @('--log-level', 'DEBUG')
            }
            & $pythonPath $uploadScript @uploadArgs
            if ($LASTEXITCODE -ne 0) {
                throw "Postgres upload exited with code $LASTEXITCODE"
            }
        }
        else {
            Write-Warning "Postgres upload script not found at $uploadScript. Skipping database load."
        }
    }
}
finally {
    Pop-Location
}
