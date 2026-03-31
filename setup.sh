#!/usr/bin/env bash
# ============================================================
# PXE Auto Deploy - VM A 初始化脚本
# 在 Ubuntu 24 (VM A) 上以 root 身份运行一次即可
# ============================================================
set -e

REPO_URL="https://github.com/la18201498539/pxeAutoDeploy.git"
INSTALL_DIR="/opt/pxeAutoDeploy"

echo "=========================================="
echo "  PXE Auto Deploy - 初始化"
echo "=========================================="

# ── 系统依赖 ──────────────────────────────────
echo "[1/3] 安装系统依赖 ..."
apt-get update -qq
apt-get install -y \
    python3 \
    git \
    dnsmasq \
    syslinux-common \
    pxelinux

# ── 克隆/更新代码 ─────────────────────────────
echo "[2/3] 获取项目代码 ..."
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "  已存在，执行 git pull ..."
    git -C "$INSTALL_DIR" pull
else
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

# ── 快捷命令 ──────────────────────────────────
echo "[3/3] 创建快捷命令 ..."
cat > /usr/local/bin/pxe-deploy << 'SH'
#!/usr/bin/env bash
sudo python3 /opt/pxeAutoDeploy/main.py "$@"
SH
chmod +x /usr/local/bin/pxe-deploy

echo ""
echo "=========================================="
echo "  安装完成！"
echo "=========================================="
echo ""
echo "  启动: sudo python3 $INSTALL_DIR/main.py"
echo "  或:   pxe-deploy"
echo ""
