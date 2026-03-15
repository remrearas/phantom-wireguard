# Phantom-WG

[![Release Workflow](https://github.com/ARAS-Workspace/phantom-wg/actions/workflows/release-workflow.yml/badge.svg)](https://github.com/ARAS-Workspace/phantom-wg/actions/workflows/release-workflow.yml)

> [🇬🇧 English](README.md) | 🇹🇷 **Türkçe** | [🇸🇦 العربية](README_AR.md)

```bash
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
```

**Kendi Sunucun. Kendi Ağın. Kendi Gizliliğin.**

Phantom-WG, kendi sunucunuzda WireGuard VPN altyapısı kurmanızı ve yönetmenizi sağlayan
modüler bir araçtır. Temel VPN yönetiminin ötesinde; sansüre dayanıklı bağlantılar, çok katmanlı
şifreleme ve gelişmiş gizlilik senaryoları sunar.

🌎 **https://retro.phantom.tc**

📰 **https://retro-docs.phantom.tc**

---

## Hızlı Kurulum

### Gereksinimler

**Sunucu:**
- İnternet erişimi ve genel (public) IPv4 adresine sahip (zorunlu), desteklenen işletim sistemlerinden birine sahip sunucu. IPv6 opsiyoneldir ve dual-stack bağlantı için desteklenir.
- Root erişimi

**İşletim Sistemi:**
- Debian 12, 13
- Ubuntu 22.04, 24.04

> **Kaynak Kullanımı:** WireGuard kernel modülü olarak çalıştığı için minimal sistem kaynağı kullanır.
> Detaylı performans bilgisi için [WireGuard Performance](https://www.wireguard.com/performance/) sayfasına bakınız.

> **Sağlayıcı mı arıyorsunuz?** Hangi sağlayıcıyı seçeceğinize karar veremediyseniz, [Spin & Deploy](https://retro.phantom.tc/wheel/index-tr.html) aracını deneyin — gizlilik odaklı, kripto dostu VPS sağlayıcıları arasından rastgele seçim yapın!

### Kurulum

```bash
curl -sSL https://install.phantom.tc | bash
```

![Installation](assets/recordings/installation-dark.gif#gh-dark-mode-only)
![Installation](assets/recordings/installation-light.gif#gh-light-mode-only)

> 📺 Tüm özelliklerin video anlatımları için https://retro-docs.phantom.tc/tr/feature-showcase/modules/core/add-client/ adresini ziyaret edin.

> `install.phantom.tc` servisi, tamamen bu GitHub reposundan maintain edilen ve GitHub Actions ile deploy edilen bir Cloudflare Worker'dır. Herhangi bir veri toplama, telemetri veya loglama işlemi gerçekleştirmez. Detaylar için [Privacy Notice](tools/phantom-install/PRIVACY_TR.md) dökümanına bakınız.

### Kurulum Sonrası

Kurulum başarıyla tamamlandığında aşağıdaki çıktıyı göreceksiniz:

```
========================================
   PHANTOM-WG INSTALLED!
========================================

Commands:
  phantom-wg - Interactive UI
  phantom-api       - API access

Quick Start:
  1. Run: phantom-wg
  2. Select 'Core Management'
  3. Add your first client

API Example:
  phantom-api core list_clients
```

---

## Senaryolar

### Core - Merkezi Yönetim Paneli

İstemci yönetimi, kriptografik anahtar üretimi, otomatik IP tahsisi ve servis kontrolü
tek merkezden yönetilir.

![Core Flow](documentation/docs/assets/static/images/index/flow-diagrams/connection-flow-core.svg)

**Temel Özellikler:**
- İstemci ekleme/kaldırma ve QR kod ile yapılandırma paylaşımı
- Sunucu durumu ve bağlantı istatistikleri
- Güvenlik duvarı yönetimi
- Subnet değişikliği ve IP yeniden haritalama

> **Detaylı Kullanım:** [Özellik Tanıtımı - Core Modülü](https://retro-docs.phantom.tc/tr/feature-showcase/modules/core/add-client/)

---

### Multihop - Çift VPN Katmanı

Trafiğinizi harici WireGuard sunucuları üzerinden zincirleyin. Kendi sunucularınızı veya
ticari VPN sağlayıcılarını kullanarak çift şifreleme katmanı oluşturun.

![Multihop Flow](documentation/docs/assets/static/images/index/flow-diagrams/connection-flow-multihop.svg)

**Temel Özellikler:**
- Herhangi bir WireGuard yapılandırma dosyasını içe aktarma
- Otomatik yönlendirme kuralları ve NAT yapılandırması
- Bağlantı izleme ve otomatik yeniden bağlanma
- VPN bağlantı testleri

---

### Ghost - Hayalet Modu

WireGuard trafiğiniz standart HTTPS web trafiği olarak maskelenir. DPI (Derin Paket İnceleme)
sistemlerini ve güvenlik duvarı engellemelerini atlayarak sansüre dirençli bağlantı sağlar.

![Ghost Flow](documentation/docs/assets/static/images/index/flow-diagrams/connection-flow-ghost.svg)

**Temel Özellikler:**
- WebSocket üzerinden tünel (wstunnel)
- Otomatik Let's Encrypt SSL sertifikası
- `phantom-casper` ile istemci yapılandırma dışa aktarımı

---

### MultiGhost - Maksimum Gizlilik

Ghost ve Multihop modüllerini birlikte kullanarak en yüksek düzeyde gizlilik ve sansür
direnci elde edin. Bağlantınız HTTPS olarak maskelenir ve çift VPN katmanı üzerinden
yönlendirilir.

![MultiGhost Flow](documentation/docs/assets/static/images/index/flow-diagrams/connection-flow-multighost.svg)

**Etkinleştirme:**
```bash
# 1. Ghost Mode'u etkinleştir
phantom-api ghost enable domain="cdn.example.com"

# 2. Harici VPN'i içe aktar
phantom-api multihop import_vpn_config config_path="/path/to/vpn.conf"

# 3. Multihop'u etkinleştir
phantom-api multihop enable_multihop exit_name="vpn-exit"
```

---

## Erişim Yöntemleri

| Yöntem                   | Komut                          | Açıklama                           |
|--------------------------|--------------------------------|------------------------------------|
| **İnteraktif CLI**       | `phantom-wg`                   | Rich TUI tabanlı kullanıcı arayüzü |
| **API**                  | `phantom-api <modül> <eylem>`  | Programatik erişim, JSON çıktı     |
| **Ghost Export**         | `phantom-casper <istemci>`     | Ghost Mode istemci yapılandırması  |
| **Ghost Export for iOS** | `phantom-casper-ios <istemci>` | Ghost Mode iOS JSON yapılandırması |

---

## Dökümanlar

| Döküman                                              | Açıklama                                |
|------------------------------------------------------|-----------------------------------------|
| [API Dökümanı (TR)](https://retro-docs.phantom.tc/tr/api/) | Tüm API eylemlerinin detaylı açıklaması |
| [Modül Mimarisi](phantom/modules/README_TR.md)       | Teknik mimari ve veri modelleri         |

---

## Ticari Marka Bildirimi

Bu proje, [WireGuard](https://www.wireguard.com/) protokolünü kullanan bağımsız bir VPN yönetim
implementasyonudur. Jason A. Donenfeld, ZX2C4 veya Edge Security ile herhangi bir bağlantısı,
ortaklığı veya onayı bulunmamaktadır.

WireGuard® Jason A. Donenfeld'in tescilli ticari markasıdır.

---

## Lisans

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>

Bu yazılım AGPL-3.0 lisansı altında lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakınız.

Üçüncü taraf lisansları için [THIRD_PARTY_LICENSES](THIRD_PARTY_LICENSES) dosyasına bakınız.

---

## 🎖️ Teşekkürler

Bu proje, aşağıdaki açık kaynak projeler olmadan mümkün olamazdı:

- **[WireGuard](https://www.wireguard.com/)** 
- **[wstunnel](https://github.com/erebe/wstunnel)** 
- **[Let's Encrypt](https://letsencrypt.org/)** 
- **[Rich](https://github.com/Textualize/rich)**
- **[TinyDB](https://github.com/msiemens/tinydb)** 
- **[qrcode](https://github.com/lincolnloop/python-qrcode)** 

---

## Destek

Phantom-WG açık kaynak bir projedir. Projeyi desteklemek isterseniz:

**Monero (XMR):**
```
84KzoZga5r7avaAqrWD4JhXaM6t69v3qe2gyCGNNxAaaJgFizt1NzAQXtYoBk1xJPXEHNi6GKV1SeDZWUX7rxzaAQeYyZwQ
```

**Bitcoin (BTC):**
```
bc1qnjjrsfdatnc2qtjpkzwpgxpmnj3v4tdduykz57
```

---

<!--suppress HtmlDeprecatedAttribute -->

<div align="center">

![Phantom Logo](documentation/docs/assets/static/images/phantom-horizontal-master-midnight-phantom.svg#gh-light-mode-only)
![Phantom Logo](documentation/docs/assets/static/images/phantom-horizontal-master-stellar-silver.svg#gh-dark-mode-only)

</div>