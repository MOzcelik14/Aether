# Aether

**Ollama tabanlı yerel yapay zeka istemcisi**

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg) ![License](https://img.shields.io/badge/license-MIT-green.svg) ![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg) ![GTK](https://img.shields.io/badge/GTK-4.0%2B-red.svg) ![Platform](https://img.shields.io/badge/platform-Linux-lightgrey.svg) ![Ollama](https://img.shields.io/badge/Ollama-ready-orange.svg)

---

## ✨ Özellikler

- 💬 **Sohbet arayüzü**
- 📦 **Model yönetimi**
- ⚙️ **Model ayarları** (sıcaklık, token vb.)
- 🎨 **Modern GTK4/Libadwaita arayüz**
- 🔒 **Tamamen yerel ve gizli**
- ⚡ **Hafif ve hızlı**

## 📋 Gereksinimler

- Linux (Debian tabanlı herhangi bir dağıtım)
- Python 3.10+
- GTK 4.0+
- Ollama

## 🚀 Kurulum

### Tek Satır Kurulum

`curl -fsSL https://raw.githubusercontent.com/MOzcelik14/Aether/main/install.sh | bash`

### Manuel Kurulum

```
git clone https://github.com/MOzcelik14/Aether.git
cd Aether
chmod +x install.sh
./install.sh
```

## 💻 Kullanım

Uygulamayı başlatmak için terminale aşağıdaki komutu girin:

`aether`

## 🛠️ Sorun Giderme

**Ollama bağlanmıyorsa:**
`sudo systemctl start ollama`

**GTK hatası alıyorsanız:**
`sudo apt install --reinstall python3-gi gir1.2-gtk-4.0 gir1.2-adw-1`

## 🤝 Katkıda Bulunma

Projeye katkıda bulunmak isterseniz, lütfen bir Issue açın veya Pull Request gönderin. 

## 📄 Lisans

Bu proje **MIT** lisansı ile lisanslanmıştır.

## 🙏 Teşekkürler

Aether'i beğendiyseniz ve geliştirmeme destek olmak isterseniz repoya ⭐ **yıldız vermeyi** unutmayın!
