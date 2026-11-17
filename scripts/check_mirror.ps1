# 校验 GitHub / GitCode 两个远端与本地是否一致（只读，不做任何修改）
# 用法： powershell -File scripts/check_mirror.ps1
param(
    [string]$RepoPath = (Split-Path -Parent $PSScriptRoot),
    [string]$ProxyPort = 7890
)

$ErrorActionPreference = 'Stop'
$sshCmd = 'ssh -F D:/514/_tools/ssh/config'

# GitHub 需要代理；GitCode 直连
if ($ProxyPort -gt 0 -and (Test-NetConnection -ComputerName '127.0.0.1' -Port $ProxyPort -InformationLevel Quiet -WarningAction SilentlyContinue)) {
    $env:HTTPS_PROXY = "http://127.0.0.1:$ProxyPort"
    $env:HTTP_PROXY  = "http://127.0.0.1:$ProxyPort"
} else {
    Write-Host "[warn] 代理 127.0.0.1:$ProxyPort 未监听，GitHub 拉取可能失败" -ForegroundColor Yellow
}

Push-Location $RepoPath
try {
    git -c core.sshCommand="$sshCmd" fetch --all --prune --quiet 2>$null

    $local = (git rev-parse HEAD).Trim()
    $gh = (git rev-parse origin/main 2>$null).Trim()
    $gc = (git rev-parse gitcode/main 2>$null).Trim()

    function FileCount($ref) {
        if (-not $ref) { return -1 }
        return (git ls-tree -r --name-only $ref | Measure-Object).Count
    }

    $rows = @(
        [pscustomobject]@{ Remote = 'local '; Head = $local.Substring(0,7); Files = (git ls-files | Measure-Object).Count }
        [pscustomobject]@{ Remote = 'github'; Head = $gh.Substring(0,7);    Files = (FileCount 'origin/main') }
        [pscustomobject]@{ Remote = 'gitcode'; Head = $gc.Substring(0,7);   Files = (FileCount 'gitcode/main') }
    )
    $rows | Format-Table -AutoSize | Out-String | Write-Host

    $ok = $true
    if ($local -ne $gh) { Write-Host "[FAIL] 本地与 GitHub 不一致：$($local.Substring(0,7)) vs $($gh.Substring(0,7))" -ForegroundColor Red; $ok = $false }
    if ($local -ne $gc) { Write-Host "[FAIL] 本地与 GitCode 不一致：$($local.Substring(0,7)) vs $($gc.Substring(0,7))" -ForegroundColor Red; $ok = $false }

    if ($gh -and $gc -and $gh -ne $gc) {
        Write-Host "[FAIL] 两个远端分叉，需人工确认方向：" -ForegroundColor Red
        git log --oneline --left-right "$gh...$gc" | Select-Object -First 10 | Write-Host
        $ok = $false
    }

    $dirty = (git status --porcelain | Measure-Object).Count
    if ($dirty -gt 0) { Write-Host "[warn] 工作区有 $dirty 个未提交改动" -ForegroundColor Yellow }

    if ($ok) { Write-Host "PASS：本地 / GitHub / GitCode 指向同一 commit" -ForegroundColor Green }
    exit ([int](-not $ok))
}
finally {
    Pop-Location
}
