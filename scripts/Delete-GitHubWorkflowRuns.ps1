[CmdletBinding()]
param(
    [string]$Owner = "Sergepetroff",
    [string]$Repo = "DekoRss",
    [string[]]$WorkflowNames = @("pages-build-deployment", "Page build deployment"),
    [string]$Token = $env:GITHUB_TOKEN,
    [int]$KeepNewest = 0,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($Token)) {
    throw "GitHub token not found. Set GITHUB_TOKEN or pass -Token."
}

$headers = @{
    Authorization        = "Bearer $Token"
    Accept               = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
}

function Get-NextLink {
    param(
        [string]$LinkHeader
    )

    if ([string]::IsNullOrWhiteSpace($LinkHeader)) {
        return $null
    }

    foreach ($part in ($LinkHeader -split ',')) {
        if ($part -match '<([^>]+)>;\s*rel="next"') {
            return $matches[1]
        }
    }

    return $null
}

function Get-MatchingWorkflowRuns {
    param(
        [string]$Owner,
        [string]$Repo,
        [hashtable]$Headers,
        [string[]]$WorkflowNames
    )

    $uri = "https://api.github.com/repos/$Owner/$Repo/actions/runs?per_page=100"
    $runs = @()

    while ($uri) {
        $response = Invoke-WebRequest -Method Get -Uri $uri -Headers $Headers
        $payload = $response.Content | ConvertFrom-Json

        foreach ($run in $payload.workflow_runs) {
            if ($WorkflowNames -contains $run.name) {
                $runs += $run
            }
        }

        $uri = Get-NextLink -LinkHeader $response.Headers.Link
    }

    return $runs
}

$runs = Get-MatchingWorkflowRuns -Owner $Owner -Repo $Repo -Headers $headers -WorkflowNames $WorkflowNames |
    Where-Object { $_.status -eq "completed" } |
    Sort-Object created_at -Descending

if (-not $runs -or $runs.Count -eq 0) {
    Write-Host "No completed workflow runs found for: $($WorkflowNames -join ', ')"
    exit 0
}

if ($KeepNewest -gt 0) {
    $runs = @($runs | Select-Object -Skip $KeepNewest)
}

if (-not $runs -or $runs.Count -eq 0) {
    Write-Host "Nothing to delete after applying -KeepNewest $KeepNewest"
    exit 0
}

Write-Host "Repository: $Owner/$Repo"
Write-Host "Workflow names: $($WorkflowNames -join ', ')"
Write-Host "Runs selected for deletion: $($runs.Count)"

if ($DryRun) {
    $runs |
        Select-Object id, name, status, conclusion, created_at, html_url |
        Format-Table -AutoSize
    exit 0
}

$deleted = 0
$failed = 0

foreach ($run in $runs) {
    $deleteUri = "https://api.github.com/repos/$Owner/$Repo/actions/runs/$($run.id)"

    try {
        Invoke-WebRequest -Method Delete -Uri $deleteUri -Headers $headers | Out-Null
        $deleted++
        Write-Host "Deleted run $($run.id) - $($run.name) - $($run.created_at)"
    }
    catch {
        $failed++
        Write-Warning "Failed to delete run $($run.id): $($_.Exception.Message)"
    }
}

Write-Host "Done. Deleted: $deleted. Failed: $failed."
