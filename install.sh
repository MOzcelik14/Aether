#!/bin/bash

set -e

echo "==============================================================="
echo "       AETHER - MOzcelik14 tarafından geliştirildi"
echo "==============================================================="
echo ""

# ============================================================
# ROOT KONTROLÜ
# ============================================================

if [ "$EUID" -eq 0 ]; then
    echo "Bu script sudo ile değil, normal kullanıcı olarak çalıştırılmalı."
    exit 1
fi

# ============================================================
# INTERNET KONTROLÜ
# ============================================================

echo "==> Internet bağlantısı kontrol ediliyor..."
if ! curl -Is --max-time 5 https://github.com >/dev/null 2>&1; then
    echo "HATA: Internet bağlantısı bulunamadı."
    exit 1
fi

# ============================================================
# GEÇİCİ DİZİN OLUŞTUR
# ============================================================

echo "==> Çalışma dizini hazırlanıyor..."
TMP_DIR=$(mktemp -d)
cd "$TMP_DIR"
echo "==> Dizin: $TMP_DIR"

# ============================================================
# DOSYALARI İNDİR
# ============================================================

echo "==> Aether dosyaları indiriliyor..."

BASE_URL="https://raw.githubusercontent.com/MOzcelik14/Aether/main"

curl -s -O "$BASE_URL/main.py"
curl -s -O "$BASE_URL/ollama.py"
curl -s -O "$BASE_URL/database.py"
curl -s -O "$BASE_URL/config.py"
curl -s -O "$BASE_URL/style.css"

if [ ! -f "main.py" ]; then
    echo "HATA: Dosyalar indirilemedi!"
    exit 1
fi

echo "==> Dosyalar indirildi."

# ============================================================
# APT BAĞIMLILIKLARI
# ============================================================

echo "==> APT paket listesi güncelleniyor..."
sudo apt update

echo "==> Bağımlılıklar kuruluyor..."
sudo apt install -y \
    python3 \
    python3-gi \
    gir1.2-gtk-4.0 \
    gir1.2-adw-1 \
    curl \
    dpkg

# ============================================================
# OLLAMA
# ============================================================

if command -v ollama >/dev/null 2>&1; then
    echo "==> Ollama zaten kurulu."
else
    echo "==> Ollama kuruluyor..."
    curl -fsSL https://ollama.com/install.sh | sh
fi

# ============================================================
# OLLAMA SERVİSİ
# ============================================================

echo "==> Ollama servisi başlatılıyor..."
if systemctl list-unit-files 2>/dev/null | grep -q "^ollama.service"; then
    sudo systemctl enable ollama.service
    sudo systemctl restart ollama.service
else
    echo "UYARI: Ollama systemd servisi bulunamadı."
fi

# ============================================================
# OLLAMA KONTROLÜ
# ============================================================

echo "==> Ollama kontrol ediliyor..."
sleep 2

if curl -fsS http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
    echo "OK: Ollama çalışıyor."
else
    echo "UYARI: Ollama API'sine erişilemiyor."
fi

# ============================================================
# .DEB PAKETİ OLUŞTUR
# ============================================================

echo "==> Aether paketi oluşturuluyor..."

APP_NAME="aether"
VERSION="0.1.0"
ARCH="all"
BUILD_DIR="$TMP_DIR/dist"
PKG_DIR="$BUILD_DIR/${APP_NAME}_${VERSION}_${ARCH}"

mkdir -p \
    "$PKG_DIR/DEBIAN" \
    "$PKG_DIR/usr/bin" \
    "$PKG_DIR/usr/share/aether" \
    "$PKG_DIR/usr/share/applications"

cp main.py ollama.py database.py config.py style.css "$PKG_DIR/usr/share/aether/"

cat > "$PKG_DIR/usr/bin/aether" <<'EOF'
#!/bin/sh
exec /usr/bin/python3 /usr/share/aether/main.py "$@"
EOF
chmod 755 "$PKG_DIR/usr/bin/aether"

cat > "$PKG_DIR/usr/share/applications/com.murat.Aether.desktop" <<'EOF'
[Desktop Entry]
Name=Aether
Comment=Ollama tabanlı yerel yapay zeka istemcisi
Exec=aether
Icon=applications-science
Terminal=false
Type=Application
Categories=Utility;Development;AI;
StartupNotify=true
EOF

cat > "$PKG_DIR/DEBIAN/control" <<EOF
Package: aether
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Maintainer: Murat Özçelik
Depends: python3, python3-gi, gir1.2-gtk-4.0, gir1.2-adw-1
Description: Aether - Ollama tabanlı yerel yapay zeka istemcisi
EOF

cat > "$PKG_DIR/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
fi
exit 0
EOF
chmod 755 "$PKG_DIR/DEBIAN/postinst"

DEB_FILE="$BUILD_DIR/${APP_NAME}_${VERSION}_${ARCH}.deb"
dpkg-deb --build "$PKG_DIR" "$DEB_FILE"

# ============================================================
# .DEB'İ KUR
# ============================================================

echo "==> Aether kuruluyor..."
sudo apt install -y "$DEB_FILE"

# ============================================================
# TEMİZLİK
# ============================================================

cd /
rm -rf "$TMP_DIR"

# ============================================================
# SONUÇ
# ============================================================

echo ""
echo "======================================"
echo "       AETHER BAŞARIYLA KURULDU"
echo "======================================"
echo ""

if command -v aether >/dev/null 2>&1; then
    echo "✅ Aether: OK"
else
    echo "❌ Aether: kontrol edilemedi"
fi

if command -v ollama >/dev/null 2>&1; then
    echo "✅ Ollama: OK"
else
    echo "❌ Ollama: kontrol edilemedi"
fi

echo ""
echo "📌 Uygulama menüsünden Aether'i açabilirsin."
echo "📌 Terminalden 'aether' komutuyla başlatabilirsin."
echo ""
echo "Kapatmak için bir tuşa basın..."
read -n 1 -s -r
echo ""
