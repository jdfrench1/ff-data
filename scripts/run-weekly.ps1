[CmdletBinding()]
param(
    [Parameter()][int]$Season = (Get-Date).Year,
    [Parameter()][Nullable[int]]$Week,
    [Parameter()][string]$Output = "nfl_weekly_stats.csv",
    [Parameter()][string]$EnvFile,
    [Parameter()][string]$LogFile,
    [switch]$AllowEmpty,
    [switch]$SkipPostgres,
    [switch]$SkipETL
)

$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Path $PSCommandPath -Parent
$repoRoot = Split-Path -Path $scriptDir -Parent
Push-Location $repoRoot

$previousPythonPath = $env:PYTHONPATH

try {
    $verboseRequested = $PSBoundParameters.ContainsKey('Verbose') -or $VerbosePreference -eq 'Continue'

    if ($LogFile) {
        $logDirectory = Split-Path -Path $LogFile -Parent
        if ($logDirectory -and -not (Test-Path $logDirectory)) {
            New-Item -ItemType Directory -Path $logDirectory | Out-Null
        }
    }

    if ($EnvFile) {
        if (Test-Path $EnvFile) {
            Get-Content -Path $EnvFile | ForEach-Object {
                $line = $_.Trim()
                if (-not $line -or $line.StartsWith('#')) { return }
                $parts = $line.Split('=', 2)
                if ($parts.Count -ne 2) { return }
                $name = $parts[0].Trim()
                $value = $parts[1].Trim()
                if ($value.StartsWith('"') -and $value.EndsWith('"')) {
                    $value = $value.Trim('"')
                }
                elseif ($value.StartsWith("'") -and $value.EndsWith("'")) {
                    $value = $value.Trim("'")
                }
                Set-Item -Path Env:$name -Value $value
            }
        }
        else {
            Write-Warning "Env file $EnvFile not found; continuing with existing environment variables."
        }
    }

    $pythonPath = Join-Path $repoRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path $pythonPath)) {
        $pythonPath = 'python'
    }

    $pathSeparator = [System.IO.Path]::PathSeparator
    if ([string]::IsNullOrWhiteSpace($previousPythonPath)) {
        $env:PYTHONPATH = 'src'
    } else {
        $paths = $previousPythonPath -split [System.IO.Path]::PathSeparator
        if ($paths -notcontains 'src') {
            $env:PYTHONPATH = 'src' + $pathSeparator + $previousPythonPath
        } else {
            $env:PYTHONPATH = $previousPythonPath
        }
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

    if (-not $SkipETL.IsPresent) {
        $weeksToUpdate = @()
        if ($Week.HasValue) {
            $weeksToUpdate = @($Week.Value)
        }
        else {
            if (Test-Path $Output) {
                try {
                    $csvFullPath = (Resolve-Path -Path $Output).Path
                    $escapedCsv = $csvFullPath -replace '\\', '\\\\'
                    $weekScript = @"
import pandas as pd
from pathlib import Path
import sys

path = Path(r"$escapedCsv")
if not path.exists():
    sys.exit(1)
df = pd.read_csv(path)
if "week" not in df.columns:
    sys.exit(2)
weeks = sorted({int(x) for x in pd.to_numeric(df["week"], errors="coerce").dropna().astype(int)})
print(",".join(str(w) for w in weeks))
"@
                    $weekResult = & $pythonPath -c $weekScript
                    if ($LASTEXITCODE -eq 0 -and $weekResult) {
                        $weeksToUpdate = $weekResult -split ',' | Where-Object { $_ -ne '' } | ForEach-Object { [int]$_ }
                    }
                    else {
                        Write-Warning "Unable to infer week values from $Output; skipping ETL update."
                    }
                }
                catch {
                    Write-Warning "Failed to resolve weeks from $Output: $_"
                }
            }
            else {
                Write-Warning "Output CSV $Output not found when inferring weeks; skipping ETL update."
            }
        }

        if ($weeksToUpdate.Count -gt 0) {
            foreach ($weekNumber in ($weeksToUpdate | Sort-Object -Unique)) {
                $etlArgs = @('-m', 'nfldb.cli', 'update-week', '--season', $Season.ToString(), '--week', $weekNumber.ToString())
                & $pythonPath @etlArgs
                if ($LASTEXITCODE -ne 0) {
                    throw "ETL update-week failed for week $weekNumber with exit code $LASTEXITCODE"
                }
            }
        }
        else {
            Write-Warning "No week numbers resolved; skipping ETL stage."
        }
    }
}
finally {
    if ($previousPythonPath) {
        $env:PYTHONPATH = $previousPythonPath
    }
    else {
        Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    }
    Pop-Location
}
