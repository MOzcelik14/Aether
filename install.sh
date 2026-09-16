#!/usr/bin/env bash

set -Eeuo pipefail

APP_NAME="aether"
APP_TITLE="Aether"
AETHER_REF="${AETHER_REF:-main}"
BASE_URL="https://raw.githubusercontent.com/MOzcelik14/Aether/${AETHER_REF}"

if [[ ${EUID} -eq 0 ]]; then
    SUDO=()
else
    if ! command -v sudo >/dev/null 2>&1; then
        echo "Hata: sudo bulunamadı."
        exit 1
    fi
    SUDO=(sudo)
fi

say() {
    printf '\n\033[1;35m%s\033[0m\n' "$1"
}

ok() {
    printf '  \033[32m✔\033[0m %s\n' "$1"
}

warn() {
    printf '  \033[33m⚠\033[0m %s\n' "$1"
}

fail() {
    printf '  \033[31m✘ %s\033[0m\n' "$1" >&2
    exit 1
}

if [[ ${1:-} == "--uninstall" ]]; then
    say "Aether kaldırılıyor"
    "${SUDO[@]}" apt-get remove -y "$APP_NAME"
    ok "Uygulama kaldırıldı."
    printf '  Kullanıcı verileri korundu: ~/.config/aether ve ~/.local/share/aether\n'
    exit 0
fi

command -v apt-get >/dev/null 2>&1 \
    || fail "Bu kurucu şu anda Debian/Ubuntu/Mint/Pardus gibi APT tabanlı sistemleri destekliyor."

if [[ ${#SUDO[@]} -gt 0 ]]; then
    say "Yetki kontrolü"
    sudo -v || fail "sudo yetkisi alınamadı."
fi

if ! command -v curl >/dev/null 2>&1; then
    say "curl kuruluyor"
    "${SUDO[@]}" apt-get install -y --no-install-recommends curl \
        || fail "curl kurulamadı. Önce 'sudo apt update' çalıştırmayı deneyin."
fi

say "Sistem bağımlılıkları"

PACKAGES=(
    python3
    python3-gi
    gir1.2-gtk-4.0
    gir1.2-adw-1
    desktop-file-utils
    dpkg
)

MISSING=()
for package in "${PACKAGES[@]}"; do
    if ! dpkg-query -W -f='${Status}' "$package" 2>/dev/null \
        | grep -q "ok installed"; then
        MISSING+=("$package")
    fi
done

if [[ ${#MISSING[@]} -gt 0 ]]; then
    printf '  Kurulacak: %s\n' "${MISSING[*]}"
    "${SUDO[@]}" apt-get install -y --no-install-recommends "${MISSING[@]}" \
        || fail "Bağımlılıklar kurulamadı. Paket listesi eskiyse 'sudo apt update' çalıştırın."
else
    ok "Gerekli sistem paketleri zaten kurulu."
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
cd "$TMP_DIR"

say "Aether ${AETHER_REF} indiriliyor"

FILES=(
    aether.py
    main.py
    ollama.py
    database.py
    config.py
    version.py
    style.css
    LICENSE
    data/com.murat.Aether.desktop
    data/com.murat.Aether.metainfo.xml
    data/com.murat.Aether.svg
)

for file in "${FILES[@]}"; do
    mkdir -p "$(dirname "$file")"
    curl -fLsS "${BASE_URL}/${file}" -o "$file" \
        || fail "${file} indirilemedi."
done

VERSION="$(
    python3 - <<'PY'
namespace = {}
with open("version.py", "r", encoding="utf-8") as file:
    exec(file.read(), namespace)
print(namespace["__version__"])
PY
)"

ok "Aether ${VERSION} indirildi."

say "DEB paketi oluşturuluyor"

PKG_DIR="$TMP_DIR/pkg"
mkdir -p \
    "$PKG_DIR/DEBIAN" \
    "$PKG_DIR/usr/bin" \
    "$PKG_DIR/usr/share/aether" \
    "$PKG_DIR/usr/share/applications" \
    "$PKG_DIR/usr/share/metainfo" \
    "$PKG_DIR/usr/share/icons/hicolor/scalable/apps" \
    "$PKG_DIR/usr/share/doc/aether"

install -m 755 aether.py "$PKG_DIR/usr/share/aether/aether.py"
install -m 644 main.py ollama.py database.py config.py version.py style.css \
    "$PKG_DIR/usr/share/aether/"
install -m 644 data/com.murat.Aether.desktop \
    "$PKG_DIR/usr/share/applications/com.murat.Aether.desktop"
install -m 644 data/com.murat.Aether.metainfo.xml \
    "$PKG_DIR/usr/share/metainfo/com.murat.Aether.metainfo.xml"
install -m 644 data/com.murat.Aether.svg \
    "$PKG_DIR/usr/share/icons/hicolor/scalable/apps/com.murat.Aether.svg"
install -m 644 LICENSE "$PKG_DIR/usr/share/doc/aether/copyright"

cat > "$PKG_DIR/usr/bin/aether" <<'EOF'
#!/bin/sh
exec /usr/bin/python3 /usr/share/aether/aether.py "$@"
EOF
chmod 755 "$PKG_DIR/usr/bin/aether"

cat > "$PKG_DIR/DEBIAN/control" <<EOF
Package: aether
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: all
Maintainer: Murat Özçelik
Depends: python3 (>= 3.10), python3-gi, gir1.2-gtk-4.0, gir1.2-adw-1
Description: Aether - Ollama tabanlı yerel yapay zeka istemcisi
 Yerel veya uzak Ollama sunucularıyla GTK4/Libadwaita üzerinden sohbet edin.
EOF

cat > "$PKG_DIR/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor >/dev/null 2>&1 || true
fi
exit 0
EOF
chmod 755 "$PKG_DIR/DEBIAN/postinst"

DEB_FILE="$TMP_DIR/aether_${VERSION}_all.deb"
dpkg-deb --build "$PKG_DIR" "$DEB_FILE" >/dev/null \
    || fail "DEB paketi oluşturulamadı."

"${SUDO[@]}" apt-get install -y "$DEB_FILE" \
    || fail "Aether kurulamadı."

ok "Aether ${VERSION} kuruldu."

say "Ollama kontrolü"

if command -v ollama >/dev/null 2>&1; then
    ok "Ollama kurulu."

    if curl -fsS --max-time 2 \
        http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
        ok "Yerel Ollama API erişilebilir."

        if [[ "$(ollama list 2>/dev/null | sed 1d | wc -l)" -eq 0 ]]; then
            warn "Henüz model yok. Örnek: ollama pull qwen3:4b"
        fi
    else
        warn "Ollama kurulu fakat API şu anda erişilemiyor."
        printf '  Servisi dağıtımınıza uygun şekilde başlatın ve Aether içinden bağlantıyı tekrar kontrol edin.\n'
    fi
else
    warn "Ollama kurulu değil. Aether yine kuruldu; Ollama'yı ayrıca kurabilirsiniz."
    printf '  Resmi kurulum: curl -fsSL https://ollama.com/install.sh | sh\n'
fi

printf '\n\033[1;32mAether hazır.\033[0m Uygulama menüsünden veya terminalde `aether` komutuyla açabilirsiniz.\n'
