<#
PowerShell helper to publish the current project folder to a GitHub remote.
Usage example:
  .\publish_to_github.ps1 -RemoteUrl git@github.com:USERNAME/REPO.git -Branch main -Message "Initial commit"

Notes:
- This script assumes `git` is available in PATH and the user has SSH or HTTPS credentials configured.
- For HTTPS with PAT, you may need to use credential helpers or embed token in remote URL (not recommended).
#>
param(
    [Parameter(Mandatory=$true)]
    [string]$RemoteUrl,

    [string]$Branch = "main",

    [string]$Message = "Initial commit from publish_to_github.ps1"
)

function Ensure-GitRepo {
    if (-not (Test-Path .git)) {
        git init
        Write-Host "Initialized new git repository"
    } else {
        Write-Host "Git repository already initialized"
    }
}

function Ensure-Remote($remote) {
    $remotes = git remote
    if ($remotes -notcontains 'origin') {
        git remote add origin $remote
        Write-Host "Added remote 'origin' -> $remote"
    } else {
        Write-Host "Remote 'origin' already exists"
    }
}

# Main
Ensure-GitRepo

# Add sensible .gitignore if missing
if (-not (Test-Path .gitignore)) {
    @(
        "venv/",
        "temperatures.db",
        "__pycache__/",
        ".vscode/"
    ) | Out-File -Encoding utf8 .gitignore
    Write-Host "Created .gitignore"
}

# Stage, commit and push
git add .
# Allow committing even if nothing to commit
$commitResult = git commit -m "$Message" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "No changes to commit or commit failed. Proceeding to push if remote exists."
}

Ensure-Remote $RemoteUrl

# Ensure branch name
git branch -M $Branch

# Push (will prompt for auth if needed)
Write-Host "Pushing to origin/$Branch..."
git push -u origin $Branch

Write-Host "Done. If push failed due to auth, configure SSH keys or PAT and retry."