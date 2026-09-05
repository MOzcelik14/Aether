#!/bin/bash

set -e

# ============================================================
# RENKLER VE STİL
# ============================================================

if [ -t 1 ]; then
    BOLD="\033[1m"
    DIM="\033[2m"
    RESET="\033[0m"

    RED="\033[38;5;203m"
    GREEN="\033[38;5;114m"
    YELLOW="\033[38;5;221m"
    BLUE="\033[38;5;75m"
    CYAN="\033[38;5;80m"
    MAGENTA="\033[38;5;177m"
    GRAY="\033[38;5;244m"
else
    BOLD=""; DIM=""; RESET=""
    RED=""; GREEN=""; YELLOW=""; BLUE=""; CYAN=""; MAGENTA=""; GRAY=""
fi

CHECK="${GREEN}✔${RESET}"
CROSS="${RED}✘${RESET}"
ARROW="${CYAN}➜${RESET}"
INFO="${BLUE}ℹ${RESET}"
WARN="${YELLOW}⚠${RESET}"

# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

hr() {
    local width="${1:-63}"
    printf "${GRAY}"
    printf '─%.0s' $(seq 1 "$width")
    printf "${RESET}\n"
}

banner() {
    echo ""
    printf "${MAGENTA}${BOLD}"
    cat <<'EOF'
     █████╗ ███████╗████████╗██╗  ██╗███████╗██████╗
    ██╔══██╗██╔════╝╚══██╔══╝██║  ██║██╔════╝██╔══██╗
    ███████║█████╗     ██║   ███████║█████╗  ██████╔╝
    ██╔══██║██╔══╝     ██║   ██╔══██║██╔══╝  ██╔══██╗
    ██║  ██║███████╗   ██║   ██║  ██║███████╗██║  ██║
    ╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝
EOF
    printf "${RESET}"
    echo -e "         ${DIM}MOzcelik14 tarafından geliştirildi${RESET}"
    echo ""
    hr
}

section() {
    echo ""
    echo -e "${BOLD}${BLUE}▌ $1${RESET}"
    hr
}

step() {
    echo -e "  ${ARROW} $1"
}

ok() {
    echo -e "  ${CHECK} $1"
}

warn() {
    echo -e "  ${WARN} ${YELLOW}$1${RESET}"
}

fail() {
    echo ""
    echo -e "  ${CROSS} ${RED}${BOLD}HATA:${RESET} ${RED}$1${RESET}"
    echo ""
    exit 1
}

# Bir komutu spinner ile çalıştırır, çıktısını gizler (hata olursa gösterir)
run_spinner() {
    local msg="$1"
    shift
    local logfile
    logfile=$(mktemp)

    ("$@" >"$logfile" 2>&1) &
    local pid=$!

    local frames='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    local i=0

    tput civis 2>/dev/null || true
    while kill -0 "$pid" 2>/dev/null; do
        i=$(( (i + 1) % ${#frames} ))
        printf "\r\033[K  ${CYAN}%s${RESET} %s" "${frames:$i:1}" "$msg"
        sleep 0.1
    done
    tput cnorm 2>/dev/null || true

    if wait "$pid"; then
        printf "\r\033[K  ${CHECK} %s\n" "$msg"
        rm -f "$logfile"
        return 0
    else
        printf "\r\033[K  ${CROSS} ${RED}%s${RESET}\n" "$msg"
        echo -e "${DIM}"
        tail -n 20 "$logfile"
        echo -e "${RESET}"
        rm -f "$logfile"
        return 1
    fi
}

progress_bar() {
    local current=$1 total=$2 label=$3
    local width=30
    local filled=$(( current * width / total ))
    local empty=$(( width - filled ))

    printf "\r\033[K  ${CYAN}["
    [ "$filled" -gt 0 ] && printf '█%.0s' $(seq 1 "$filled")
    [ "$empty" -gt 0 ] && printf '░%.0s' $(seq 1 "$empty")
    printf "]${RESET} %s" "$label"

    if [ "$current" -eq "$total" ]; then
        echo ""
    fi
}

# ============================================================
# BAŞLANGIÇ
# ============================================================

clear 2>/dev/null || true
banner

# ============================================================
# ROOT KONTROLÜ
# ============================================================

if [ "$EUID" -eq 0 ]; then
    fail "Bu script sudo ile değil, normal kullanıcı olarak çalıştırılmalı."
fi

# ============================================================
# SUDO OTURUMU
# ============================================================
# Script boyunca arka planda çalışan (spinner'lı) sudo komutlarının
# şifre sorusu görünmeden takılmaması için oturumu önden alıp canlı tutuyoruz.

step "Sudo yetkisi isteniyor..."
sudo -v || fail "Sudo yetkisi alınamadı."

( while true; do sudo -n true; sleep 60; done ) 2>/dev/null &
SUDO_KEEPALIVE_PID=$!

# ============================================================
# TEMİZLİK
# ============================================================

TMP_DIR=""

cleanup() {
    kill "$SUDO_KEEPALIVE_PID" 2>/dev/null || true
    if [ -n "$TMP_DIR" ] && [ -d "$TMP_DIR" ]; then
        rm -rf "$TMP_DIR"
    fi
}

trap cleanup EXIT

# ============================================================
# INTERNET KONTROLÜ
# ============================================================

section "Ön Kontroller"

step "Internet bağlantısı kontrol ediliyor..."
if ! curl -Is --max-time 5 https://github.com >/dev/null 2>&1; then
    fail "Internet bağlantısı bulunamadı."
fi
ok "Internet bağlantısı mevcut"

# ============================================================
# ÇALIŞMA DİZİNİ
# ============================================================

step "Çalışma dizini hazırlanıyor..."
TMP_DIR=$(mktemp -d)
cd "$TMP_DIR"
ok "Dizin: ${DIM}$TMP_DIR${RESET}"

# ============================================================
# DOSYALARI İNDİR
# ============================================================

section "Aether Dosyaları"

BASE_URL="https://raw.githubusercontent.com/MOzcelik14/Aether/main"
FILES=(main.py ollama.py database.py config.py style.css)
TOTAL=${#FILES[@]}
COUNT=0

for f in "${FILES[@]}"; do
    COUNT=$((COUNT + 1))
    curl -fLsS -o "$f" "$BASE_URL/$f"
    progress_bar "$COUNT" "$TOTAL" "$f indirildi"
done

if [ ! -s "main.py" ]; then
    fail "Aether dosyaları indirilemedi."
fi
ok "Tüm Aether dosyaları indirildi"

# ============================================================
# APT BAĞIMLILIKLARI
# ============================================================

section "Sistem Bağımlılıkları"

run_spinner "APT paket listesi güncelleniyor" sudo apt update || fail "APT güncellenemedi."

step "Bağımlılıklar kuruluyor: ${DIM}python3, python3-gi, gtk4, libadwaita, curl, dpkg${RESET}"
run_spinner "Bağımlılıklar kuruluyor" sudo apt install -y \
    python3 \
    python3-gi \
    gir1.2-gtk-4.0 \
    gir1.2-adw-1 \
    curl \
    dpkg || fail "Bağımlılıklar kurulamadı."

# ============================================================
# OLLAMA KURULUMU
# ============================================================

section "Ollama Kurulumu"

if command -v ollama >/dev/null 2>&1; then
    OLLAMA_VER=$(ollama --version 2>/dev/null | head -n1 || echo "bilinmiyor")
    ok "Ollama zaten kurulu ${DIM}($OLLAMA_VER)${RESET}"
else
    run_spinner "Ollama kuruluyor" bash -c "curl -fsSL https://ollama.com/install.sh | sh" \
        || fail "Ollama kurulumu başarısız."
fi

# ============================================================
# OLLAMA KULLANICISI
# ============================================================

step "Ollama sistem kullanıcısı kontrol ediliyor..."
if ! id ollama >/dev/null 2>&1; then
    fail "'ollama' sistem kullanıcısı bulunamadı. Ollama kurulumu eksik görünüyor."
fi
ok "ollama kullanıcısı mevcut"

# ============================================================
# OLLAMA DİZİNLERİ VE İZİNLER
# ============================================================

step "Ollama çalışma dizinleri hazırlanıyor..."
sudo mkdir -p /usr/share/ollama
sudo chown -R ollama:ollama /usr/share/ollama

if [ -d /var/lib/ollama ]; then
    sudo chown -R ollama:ollama /var/lib/ollama
fi
ok "Dizin izinleri ayarlandı"

# ============================================================
# OLLAMA SERVİSİ
# ============================================================

step "Ollama systemd servisi kontrol ediliyor..."
if ! systemctl list-unit-files 2>/dev/null | grep -q "^ollama.service"; then
    fail "ollama.service bulunamadı."
fi

run_spinner "Ollama servisi etkinleştiriliyor" sudo systemctl enable ollama.service \
    || fail "Servis etkinleştirilemedi."
run_spinner "Ollama servisi başlatılıyor" sudo systemctl restart ollama.service \
    || fail "Servis başlatılamadı."

# ============================================================
# OLLAMA SERVİS KONTROLÜ
# ============================================================

step "Ollama servisinin hazır olması bekleniyor..."

OLLAMA_READY=0
for i in $(seq 1 15); do
    progress_bar "$i" 15 "servis kontrol ediliyor ($i/15)"
    if curl -fsS --max-time 2 http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
        OLLAMA_READY=1
        break
    fi
    sleep 1
done
echo ""

if [ "$OLLAMA_READY" -ne 1 ]; then
    echo ""
    warn "Ollama servis durumu:"
    systemctl status ollama --no-pager || true
    echo ""
    warn "Son Ollama logları:"
    sudo journalctl -u ollama -n 30 --no-pager || true
    echo ""
    fail "Ollama başlatılamadı."
fi

ok "Ollama çalışıyor"

# ============================================================
# MODEL
# ============================================================

section "Yapay Zeka Modeli"

DEFAULT_MODEL="qwen3:8b"
step "Varsayılan model kontrol ediliyor: ${BOLD}$DEFAULT_MODEL${RESET}"

if ollama list 2>/dev/null | awk 'NR>1 {print $1}' | grep -Fxq "$DEFAULT_MODEL"; then
    ok "$DEFAULT_MODEL zaten kurulu"
else
    run_spinner "$DEFAULT_MODEL indiriliyor (bu biraz sürebilir)" ollama pull "$DEFAULT_MODEL" \
        || fail "$DEFAULT_MODEL indirilemedi."
fi

# ============================================================
# .DEB PAKETİ
# ============================================================

section "Aether Paketleniyor"

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

cp \
    main.py \
    ollama.py \
    database.py \
    config.py \
    style.css \
    "$PKG_DIR/usr/share/aether/"

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
Package: $APP_NAME
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

run_spinner ".deb paketi oluşturuluyor" dpkg-deb --build "$PKG_DIR" "$DEB_FILE" \
    || fail ".deb paketi oluşturulamadı."

if [ ! -s "$DEB_FILE" ]; then
    fail ".deb paketi oluşturulamadı."
fi

run_spinner "Aether kuruluyor" sudo apt install -y "$DEB_FILE" \
    || fail "Aether kurulamadı."

# ============================================================
# KURULUM KONTROLÜ
# ============================================================

section "Kurulum Kontrolü"

ALL_OK=1

if command -v aether >/dev/null 2>&1; then
    ok "Aether"
else
    echo -e "  ${CROSS} Aether"
    ALL_OK=0
fi

if command -v ollama >/dev/null 2>&1; then
    ok "Ollama"
else
    echo -e "  ${CROSS} Ollama"
    ALL_OK=0
fi

if curl -fsS --max-time 3 http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
    ok "Ollama API"
else
    echo -e "  ${CROSS} Ollama API"
    ALL_OK=0
fi

if ollama list 2>/dev/null | awk 'NR>1 {print $1}' | grep -Fxq "$DEFAULT_MODEL"; then
    ok "$DEFAULT_MODEL"
else
    echo -e "  ${CROSS} $DEFAULT_MODEL"
    ALL_OK=0
fi

if [ "$ALL_OK" -ne 1 ]; then
    fail "Kurulum kontrolünde bir veya daha fazla bileşen eksik."
fi

# ============================================================
# SONUÇ
# ============================================================

echo ""
printf "${GREEN}${BOLD}"
hr
echo "        ✔  AETHER BAŞARIYLA KURULDU"
hr
printf "${RESET}"
echo ""
echo -e "  ${BOLD}Başlatmak için:${RESET}     ${CYAN}aether${RESET}"
echo -e "  ${BOLD}Ollama API:${RESET}         ${DIM}http://127.0.0.1:11434${RESET}"
echo -e "  ${BOLD}Model:${RESET}              ${DIM}$DEFAULT_MODEL${RESET}"
echo ""
echo -e "${GREEN}Kurulum tamamlandı.${RESET}"
echo ""
