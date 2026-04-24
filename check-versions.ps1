$tools = @(
    @{ Name = "Docker Desktop"; Command = { docker --version } },
    @{ Name = "Git";            Command = { git --version } },
    @{ Name = "VS Code";        Command = { code --version | Select-Object -First 1 } },
    @{ Name = "Python";         Command = { python --version } },
    @{ Name = "AWS CLI v2";     Command = { aws --version } }
)

foreach ($tool in $tools) {
    try {
        $version = & $tool.Command 2>&1
        Write-Host "$($tool.Name): $version"
    } catch {
        Write-Host "$($tool.Name): not found"
    }
}
