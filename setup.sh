#!/usr/bin/env bash
# ============================================================
# PXE Auto Deploy - VM A 初始化脚本
# 在 Ubuntu 24 (VM A) 上以 root 身份运行
# ============================================================
set -e

REPO_URL="https://github.com/la18201498539/pxeAutoDeploy.git"
INSTALL_DIR="/opt/pxeAutoDeploy"

echo "=========================================="
echo "  PXE Auto Deploy - 初始化"
echo "=========================================="

# ── 系统依赖 ──────────────────────────────────
echo "[1/4] 安装系统依赖 ..."
apt-get update -qq
apt-get install -y \
    python3 \
    python3-pip \
    python3-tk \
    git \
    dnsmasq \
    syslinux-common \
    pxelinux

# ── 克隆/更新代码 ─────────────────────────────
echo "[2/4] 获取项目代码 ..."
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "  已存在，执行 git pull ..."
    git -C "$INSTALL_DIR" pull
else
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

# ── Python 依赖 (venv，兼容 Ubuntu 24 externally-managed) ──
echo "[3/4] 安装 Python 依赖 ..."
apt-get install -y python3-venv -qq 2>/dev/null || true
python3 -m venv "$INSTALL_DIR/.venv"
"$INSTALL_DIR/.venv/bin/pip" install -q -r "$INSTALL_DIR/requirements.txt"

# ── 权限 & 快捷方式 ──────────────────────────
echo "[4/4] 设置权限 ..."
chmod +x "$INSTALL_DIR/main.py"

# 创建快捷启动脚本
cat > /usr/local/bin/pxe-deploy << 'EOF'
#!/usr/bin/env bash
# 保留 DISPLAY/XAUTHORITY 以支持图形界面
sudo -E /opt/pxeAutoDeploy/.venv/bin/python /opt/pxeAutoDeploy/main.py "$@"
EOF
chmod +x /usr/local/bin/pxe-deploy

echo ""
echo "=========================================="
echo "  安装完成！"
echo "=========================================="
echo ""
echo "  启动方式:"
echo "    pxe-deploy"
echo ""
echo "  或手动:"
echo "    sudo python3 $INSTALL_DIR/main.py"
echo ""
