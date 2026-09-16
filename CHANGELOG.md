# Changelog

Bu projedeki önemli değişiklikler bu dosyada takip edilir.

## [1.1.0] - 2026-09-16

### Eklendi
- Mesaj ve kod bloğu kopyalama.
- Son Aether yanıtını yeniden üretme.
- Sohbeti Markdown olarak dışa aktarma.
- Sohbet silme ve model silme için onay akışları.
- Sohbet başlıklarının yanında mesaj içeriklerinde de arama.
- Model silme arayüzü.
- Top P, Top K, repeat penalty ve maksimum çıktı token ayarları.
- Kullanıcı tarafından değiştirilebilir system prompt.
- Checkbox, yatay çizgi, link ve strikethrough dahil geliştirilmiş Markdown render.
- Ctrl+N, Ctrl+, ve Ctrl+K kısayolları.
- XDG uyumlu ayar ve veri dizinleri.
- Flatpak manifesti, AppStream metadata ve uygulama ikonu.
- GitHub Actions doğrulama iş akışı ve temel unit testleri.
- Yeni özellikler için modüler `aether_app` uygulama katmanı.

### Değişti
- Kurulum betiği artık Ollama'yı, servisini veya modeli zorla kurup değiştirmez.
- Tema CSS'i sistem açık/koyu görünümünü takip edecek şekilde yenilendi.
- Monospace font yalnızca kod alanlarında kullanılıyor.
- Sürüm numarası tek bir kaynaktan 1.1.0 olarak yönetiliyor.
- Sohbetler son güncellenme zamanına göre sıralanıyor.
- Ayarlar atomik olarak kaydediliyor ve kullanıcıya özel dosya izinleri uygulanıyor.

### Düzeltildi
- Üretim durdurulduğunda yarım yanıtın oturumla tutarsız kalması.
- Boş yarım asistan yanıtının bellekte kalması.
- Sohbet silmede geri dönüşsüz işlemin onaysız yapılması.
- Eski `local-ai` config/veri yollarından Aether yollarına geçiş.

## [1.0.0] - 2026-09-05
- İlk genel sürüm.
