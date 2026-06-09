# vocab_pwa 一键上线脚本（需先完成 gh auth login 与 Turso 凭证）
# 用法: .\scripts\deploy_online.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$Gh = "C:\Program Files\GitHub CLI\gh.exe"
if (-not (Test-Path $Gh)) {
    $Gh = "gh"
}

Write-Host "==> 检查 GitHub CLI 登录状态..."
& $Gh auth status
if ($LASTEXITCODE -ne 0) {
    Write-Host "请先运行: gh auth login"
    exit 1
}

Write-Host "==> 创建/推送 GitHub 仓库..."
$remote = (& git remote get-url origin 2>$null)
if (-not $remote) {
    & $Gh repo create seanzombias/vocab_pwa --public --source=. --remote=origin --push
} else {
    git push -u origin main
}

Write-Host ""
Write-Host "==> 下一步（浏览器手动完成）:"
Write-Host "1. GitHub Pages: https://github.com/seanzombias/vocab_pwa/settings/pages"
Write-Host "   Source 选 GitHub Actions"
Write-Host "2. Turso: https://turso.tech/app  创建库 vocab-pwa，复制 URL 与 Token"
Write-Host "3. Render Blueprint: https://dashboard.render.com/select-repo?type=blueprint"
Write-Host "   连接 seanzombias/vocab_pwa，填入 TURSO_DATABASE_URL / TURSO_AUTH_TOKEN"
Write-Host "4. 验证 API: https://vocab-pwa-api.onrender.com/api/health"
Write-Host "5. 打开 PWA: https://seanzombias.github.io/vocab_pwa/"
Write-Host ""
Write-Host "导入词汇到生产环境（部署完成后）:"
Write-Host "  python scripts/import_vocab.py backend/data/axios_article_vocab.json --api https://vocab-pwa-api.onrender.com --token <VOCAB_API_TOKEN>"
