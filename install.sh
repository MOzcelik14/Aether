#!/bin/bash

set -e

APP_NAME="aether"
VERSION="0.1.0"
ARCH="all"

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEB_FILE="$PROJECT_DIR/dist/aether_0.1.0_all.deb"

echo "======================================"
echo "       AETHER KURULUMU"
echo "======================================"
echo ""

# ============================================================
# ROOT KONTROLÜ
# ============================================================

if [ "$EUID" -eq 0 ]; then
    echo "Bu script sudo ile değil, normal kullanıcı olarak çalıştırılmalı."
    echo "Gerekli yerlerde sudo otomatik kullanılacak."
    exit 1
fi

# ============================================================
# INTERNET KONTROLÜ
# ============================================================

echo "==> Internet bağlantısı kontrol ediliyor..."

if ! curl -Is --max-time 5 https://ollama.com >/dev/null 2>&1; then
    echo "HATA: Internet bağlantısı bulunamadı."
    exit 1
fi

# ============================================================
# APT BAĞIMLILIKLARI
# ============================================================

echo "==> APT paket listesi güncelleniyor..."

sudo apt update

echo "==> Aether bağımlılıkları kuruluyor..."

sudo apt install -y \
    python3 \
    python3-gi \
    gir1.2-gtk-4.0 \
    gir1.2-adw-1 \
    curl \
    ca-certificates \
    dpkg

# ============================================================
# OLLAMA
# ============================================================

if command -v ollama >/dev/null 2>&1; then
    echo "==> Ollama zaten kurulu."
else
    echo "==> Ollama kuruluyor..."
    echo ""
    curl -fsSL https://ollama.com/install.sh | sh
fi

# ============================================================
# OLLAMA SERVİSİ
# ============================================================

echo ""
echo "==> Ollama servisi başlatılıyor..."

if systemctl list-unit-files 2>/dev/null | grep -q "^ollama.service"; then
    sudo systemctl enable ollama.service
    sudo systemctl restart ollama.service
else
    echo "UYARI: Ollama systemd servisi bulunamadı."
    echo "Ollama elle başlatılmayı gerektirebilir."
fi

# ============================================================
# OLLAMA KONTROLÜ
# ============================================================

echo "==> Ollama kontrol ediliyor..."

sleep 2

OLLAMA_OK=0

# 1. PATH'te kontrol et
if command -v ollama >/dev/null 2>&1; then
    OLLAMA_OK=1
fi

# 2. Servis kontrol et
if systemctl is-active --quiet ollama 2>/dev/null; then
    OLLAMA_OK=1
fi

# 3. API kontrol et
if curl -fsS http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
    OLLAMA_OK=1
fi

if [ "$OLLAMA_OK" -eq 1 ]; then
    echo "OK: Ollama çalışıyor."
else
    echo "UYARI: Ollama API'sine şu anda erişilemiyor."
    echo "Kurulum devam edecek."
fi

# ============================================================
# AETHER .DEB BUILD (Entegre)
# ============================================================

echo ""
echo "==> Aether paketi oluşturuluyor..."

# Eski build'i temizle
rm -rf "$PROJECT_DIR/dist"

# Paket dizini
BUILD_DIR="$PROJECT_DIR/dist"
PKG_DIR="$BUILD_DIR/${APP_NAME}_${VERSION}_${ARCH}"
APP_DIR_NAME="aether"

# Dizinleri oluştur
mkdir -p \
    "$PKG_DIR/DEBIAN" \
    "$PKG_DIR/usr/bin" \
    "$PKG_DIR/usr/share/$APP_DIR_NAME" \
    "$PKG_DIR/usr/share/applications"

# Uygulama dosyalarını kopyala
echo "==> Uygulama dosyaları kopyalanıyor..."

# Dosyaların var olduğunu kontrol et
REQUIRED_FILES=("main.py" "ollama.py" "database.py" "config.py" "style.css")
MISSING_FILES=()

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$PROJECT_DIR/$file" ]; then
        MISSING_FILES+=("$file")
    fi
done

if [ ${#MISSING_FILES[@]} -ne 0 ]; then
    echo "HATA: Aşağıdaki dosyalar bulunamadı:"
    for file in "${MISSING_FILES[@]}"; do
        echo "  - $file"
    done
    exit 1
fi

cp "$PROJECT_DIR/main.py" \
   "$PROJECT_DIR/ollama.py" \
   "$PROJECT_DIR/database.py" \
   "$PROJECT_DIR/config.py" \
   "$PROJECT_DIR/style.css" \
   "$PKG_DIR/usr/share/$APP_DIR_NAME/"

# Çalıştırıcı oluştur
echo "==> Çalıştırıcı oluşturuluyor..."
cat > "$PKG_DIR/usr/bin/aether" <<'EOF'
#!/bin/sh
exec /usr/bin/python3 /usr/share/aether/main.py "$@"
EOF

chmod 755 "$PKG_DIR/usr/bin/aether"

# Desktop dosyası
echo "==> Desktop dosyası oluşturuluyor..."
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

# DEBIAN/control
echo "==> DEBIAN/control oluşturuluyor..."
cat > "$PKG_DIR/DEBIAN/control" <<EOF
Package: aether
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Maintainer: Murat Özçelik
Depends: python3, python3-gi, gir1.2-gtk-4.0, gir1.2-adw-1
Description: Aether
 Ollama için GTK4 ve Libadwaita tabanlı yerel yapay zeka istemcisi.
EOF

# postinst (Güncellenmiş - daha kapsamlı Ollama kontrolü)
echo "==> postinst oluşturuluyor..."
cat > "$PKG_DIR/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e

# Desktop database güncelle
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
fi

# Ollama kontrolü - daha kapsamlı
OLLAMA_OK=0

# 1. PATH'te kontrol et
if command -v ollama >/dev/null 2>&1; then
    OLLAMA_OK=1
fi

# 2. Servis kontrol et
if systemctl is-active --quiet ollama 2>/dev/null; then
    OLLAMA_OK=1
fi

# 3. API kontrol et
if curl -fsS http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
    OLLAMA_OK=1
fi

# Uyarı göster
if [ "$OLLAMA_OK" -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "UYARI: Ollama sistemde bulunamadı veya çalışmıyor!"
    echo "Aether çalışmak için Ollama gerektirir."
    echo ""
    echo "Ollama kurulumu için:"
    echo "  curl -fsSL https://ollama.com/install.sh | sh"
    echo "=========================================="
    echo ""
fi

exit 0
EOF

chmod 755 "$PKG_DIR/DEBIAN/postinst"

# .deb oluştur
echo "==> .deb oluşturuluyor..."
dpkg-deb --build \
    "$PKG_DIR" \
    "$DEB_FILE"

# ============================================================
# AETHER KURULUMU (Güncellenmiş - erişim izni sorunu çözüldü)
# ============================================================

echo ""
echo "==> Aether kuruluyor..."

# Dosyayı geçici dizine kopyala (erişim izni sorununu çözer)
TMP_DEB="/tmp/aether_${VERSION}_${ARCH}.deb"
cp "$DEB_FILE" "$TMP_DEB"

# .deb'i kur
sudo apt install -y "$TMP_DEB"

# Geçici dosyayı temizle
rm -f "$TMP_DEB"

# ============================================================
# DESKTOP DATABASE
# ============================================================

if command -v update-desktop-database >/dev/null 2>&1; then
    sudo update-desktop-database \
        /usr/share/applications \
        >/dev/null 2>&1 || true
fi

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

# Ollama durumunu kontrol et
if command -v ollama >/dev/null 2>&1; then
    echo "✅ Ollama: OK"
elif systemctl is-active --quiet ollama 2>/dev/null; then
    echo "✅ Ollama: OK (servis çalışıyor)"
elif curl -fsS http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
    echo "✅ Ollama: OK (API çalışıyor)"
else
    echo "❌ Ollama: kontrol edilemedi"
fi

echo ""
echo "📌 Uygulama menüsünden Aether'i açabilirsin."
echo "📌 Terminalden 'aether' komutuyla da başlatabilirsin."
echo ""

# ============================================================
# BEKLEME FONKSİYONU
# ============================================================

echo "----------------------------------------------"
echo "Kapatmak için bir tuşa basın..."
read -n 1 -s -r
echo ""
