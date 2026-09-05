
#!/bin/bash

set -e

clear

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
# TEMİZLİK
# ============================================================

TMP_DIR=""

cleanup() {
    if [ -n "$TMP_DIR" ] && [ -d "$TMP_DIR" ]; then
        rm -rf "$TMP_DIR"
    fi
}

trap cleanup EXIT

# ============================================================
# INTERNET KONTROLÜ
# ============================================================

echo "==> Internet bağlantısı kontrol ediliyor..."

if ! curl -Is --max-time 5 https://github.com >/dev/null 2>&1; then
    echo "HATA: Internet bağlantısı bulunamadı."
    exit 1
fi

echo "OK: Internet bağlantısı mevcut."

# ============================================================
# ÇALIŞMA DİZİNİ
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

curl -fLsS -o main.py "$BASE_URL/main.py"
curl -fLsS -o ollama.py "$BASE_URL/ollama.py"
curl -fLsS -o database.py "$BASE_URL/database.py"
curl -fLsS -o config.py "$BASE_URL/config.py"
curl -fLsS -o style.css "$BASE_URL/style.css"

if [ ! -s "main.py" ]; then
    echo "HATA: Aether dosyaları indirilemedi."
    exit 1
fi

echo "OK: Aether dosyaları indirildi."

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
    dpkg

# ============================================================
# OLLAMA KURULUMU
# ============================================================

echo ""
echo "==============================================================="
echo "                    OLLAMA KURULUMU"
echo "==============================================================="

if command -v ollama >/dev/null 2>&1; then
    echo "==> Ollama zaten kurulu."
    ollama --version || true
else
    echo "==> Ollama kuruluyor..."

    if ! curl -fsSL https://ollama.com/install.sh | sh; then
        echo "HATA: Ollama kurulumu başarısız."
        exit 1
    fi
fi

# ============================================================
# OLLAMA KULLANICISI
# ============================================================

echo "==> Ollama sistem kullanıcısı kontrol ediliyor..."

if ! id ollama >/dev/null 2>&1; then
    echo "HATA: 'ollama' sistem kullanıcısı bulunamadı."
    echo "Ollama kurulumu eksik görünüyor."
    exit 1
fi

echo "OK: ollama kullanıcısı mevcut."

# ============================================================
# OLLAMA DİZİNLERİ VE İZİNLER
# ============================================================

echo "==> Ollama çalışma dizinleri hazırlanıyor..."

sudo mkdir -p /usr/share/ollama

sudo chown -R ollama:ollama /usr/share/ollama

# Eğer daha önce oluşturulmuşsa mevcut Ollama dizinlerinin
# sahipliğini de garanti altına al.
if [ -d /var/lib/ollama ]; then
    sudo chown -R ollama:ollama /var/lib/ollama
fi

# ============================================================
# OLLAMA SERVİSİ
# ============================================================

echo "==> Ollama systemd servisi kontrol ediliyor..."

if ! systemctl list-unit-files 2>/dev/null | grep -q "^ollama.service"; then
    echo "HATA: ollama.service bulunamadı."
    exit 1
fi

echo "==> Ollama servisi etkinleştiriliyor..."

sudo systemctl enable ollama.service

echo "==> Ollama servisi başlatılıyor..."

sudo systemctl restart ollama.service

# ============================================================
# OLLAMA SERVİS KONTROLÜ
# ============================================================

echo "==> Ollama servisinin başlaması bekleniyor..."

OLLAMA_READY=0

for i in $(seq 1 15); do
    if curl -fsS \
        --max-time 2 \
        http://127.0.0.1:11434/api/version \
        >/dev/null 2>&1; then

        OLLAMA_READY=1
        break
    fi

    sleep 1
done

if [ "$OLLAMA_READY" -ne 1 ]; then
    echo ""
    echo "HATA: Ollama başlatılamadı."
    echo ""
    echo "Ollama servis durumu:"
    systemctl status ollama --no-pager || true
    echo ""
    echo "Son Ollama logları:"
    sudo journalctl -u ollama -n 30 --no-pager || true
    echo ""
    exit 1
fi

echo "OK: Ollama çalışıyor."

# ============================================================
# MODEL
# ============================================================

DEFAULT_MODEL="qwen3:8b"

echo ""
echo "==> Aether varsayılan modeli kontrol ediliyor..."
echo "    Model: $DEFAULT_MODEL"

if ollama list 2>/dev/null | awk 'NR>1 {print $1}' | grep -Fxq "$DEFAULT_MODEL"; then
    echo "OK: $DEFAULT_MODEL zaten kurulu."
else
    echo "==> $DEFAULT_MODEL indiriliyor..."

    if ! ollama pull "$DEFAULT_MODEL"; then
        echo "HATA: $DEFAULT_MODEL indirilemedi."
        exit 1
    fi

    echo "OK: $DEFAULT_MODEL indirildi."
fi

# ============================================================
# .DEB PAKETİ
# ============================================================

echo ""
echo "==============================================================="
echo "                    AETHER PAKETİ"
echo "==============================================================="

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

# ============================================================
# AETHER DOSYALARI
# ============================================================

cp \
    main.py \
    ollama.py \
    database.py \
    config.py \
    style.css \
    "$PKG_DIR/usr/share/aether/"

# ============================================================
# ÇALIŞTIRMA KOMUTU
# ============================================================

cat > "$PKG_DIR/usr/bin/aether" <<'EOF'
#!/bin/sh
exec /usr/bin/python3 /usr/share/aether/main.py "$@"
EOF

chmod 755 "$PKG_DIR/usr/bin/aether"

# ============================================================
# DESKTOP DOSYASI
# ============================================================

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

# ============================================================
# DEBIAN CONTROL
# ============================================================

cat > "$PKG_DIR/DEBIAN/control" <<EOF
Package: $APP_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Maintainer: Murat Özçelik
Depends: python3, python3-gi, gir1.2-gtk-4.0, gir1.2-adw-1
Description: Aether - Ollama tabanlı yerel yapay zeka istemcisi
EOF

# ============================================================
# POSTINST
# ============================================================

cat > "$PKG_DIR/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
fi

exit 0
EOF

chmod 755 "$PKG_DIR/DEBIAN/postinst"

# ============================================================
# DEB OLUŞTUR
# ============================================================

DEB_FILE="$BUILD_DIR/${APP_NAME}_${VERSION}_${ARCH}.deb"

echo "==> .deb paketi oluşturuluyor..."

dpkg-deb --build "$PKG_DIR" "$DEB_FILE"

if [ ! -s "$DEB_FILE" ]; then
    echo "HATA: .deb paketi oluşturulamadı."
    exit 1
fi

echo "OK: Aether paketi oluşturuldu."

# ============================================================
# AETHER KUR
# ============================================================

echo "==> Aether kuruluyor..."

sudo apt install -y "$DEB_FILE"

# ============================================================
# KURULUM KONTROLÜ
# ============================================================

echo ""
echo "==============================================================="
echo "                    KURULUM KONTROLÜ"
echo "==============================================================="

if command -v aether >/dev/null 2>&1; then
    echo "✅ Aether: OK"
else
    echo "❌ Aether: bulunamadı"
    exit 1
fi

if command -v ollama >/dev/null 2>&1; then
    echo "✅ Ollama: OK"
else
    echo "❌ Ollama: bulunamadı"
    exit 1
fi

if curl -fsS \
    --max-time 3 \
    http://127.0.0.1:11434/api/version \
    >/dev/null 2>&1; then

    echo "✅ Ollama API: OK"
else
    echo "❌ Ollama API: erişilemiyor"
    exit 1
fi

if ollama list 2>/dev/null | awk 'NR>1 {print $1}' | grep -Fxq "$DEFAULT_MODEL"; then
    echo "✅ $DEFAULT_MODEL: OK"
else
    echo "❌ $DEFAULT_MODEL: bulunamadı"
    exit 1
fi

# ============================================================
# SONUÇ
# ============================================================

echo ""
echo "======================================"
echo "       AETHER BAŞARIYLA KURULDU"
echo "======================================"
echo ""
echo "Aether:"
echo "  aether"
echo ""
echo "Ollama:"
echo "  http://127.0.0.1:11434"
echo ""
echo "Model:"
echo "  $DEFAULT_MODEL"
echo ""
echo "Kurulum tamamlandı."
echo ""

