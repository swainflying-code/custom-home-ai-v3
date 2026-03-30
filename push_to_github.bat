# 成交魔方 V3 - GitHub 推送脚本
# 在 PowerShell 中运行此脚本
# 使用前：先在 GitHub 上新建仓库 custom-home-ai-v3

cd "F:\AI-ying\custom-home-ai-v3"

# 添加远程仓库（把 swainflying-code 换成你的 GitHub 用户名）
git remote add origin https://github.com/swainflying-code/custom-home-ai-v3.git

# 推送
git branch -M main
git push -u origin main
