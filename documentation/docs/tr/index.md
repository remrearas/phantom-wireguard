---
extra_javascript:
  - assets/javascripts/asciinema-player.js
  - assets/javascripts/phantom-ascii.js
  - assets/javascripts/animated-ascii-art.js

---
# Phantom-WG Retro

!!! warning "Kullanımdan Kaldırıldı"
    Phantom-WG Retro kullanımdan kaldırılmıştır. Aktif geliştirme [Phantom-WG Modern](https://github.com/ARAS-Workspace/phantom-wg) üzerinde devam etmektedir. Bu kod tabanı aktif geliştirilmeye devam etmeyecektir. Güncellemeler nadir ve önemli düzeltmeleri içerecektir.

<div class="ascii-demo-container">
  <pre id="phantom-ascii-pulse" class="ascii-art" data-effect="pulse"></pre>
</div>

**Kendi Sunucun. Kendi Ağın. Kendi Gizliliğin.**

Phantom-WG, kendi sunucunuzda WireGuard VPN altyapısı kurmanızı ve yönetmenizi sağlayan
modüler bir araçtır. Temel VPN yönetiminin ötesinde; sansüre dayanıklı bağlantılar, çok katmanlı
şifreleme ve gelişmiş gizlilik senaryoları sunar.


:fontawesome-solid-globe: **[https://retro.phantom.tc](https://retro.phantom.tc)**

:fontawesome-brands-github: **[Github](https://github.com/ARAS-Workspace/phantom-wg)**


## Hızlı Başlangıç

### Gereksinimler

**Sunucu:**

- İnternet erişimi ve genel (public) IPv4 adresine sahip, desteklenen işletim sistemlerinden birine sahip sunucu
- Root erişimi

**İşletim Sistemi:**

- Debian 12, 13
- Ubuntu 22.04, 24.04

> **Kaynak Kullanımı:** WireGuard kernel modülü olarak çalıştığı için minimal sistem kaynağı kullanır.
> Detaylı performans bilgisi için [WireGuard Performance](https://www.wireguard.com/performance/) sayfasına bakınız.

### Kurulum

```bash
curl -sSL https://install.phantom.tc | bash
```

<div class="asciinema-player-container">
    <div class="asciinema-player-header">
        <h3>Phantom-WG</h3>
        <span class="asciinema-player-info">Terminal Kaydı</span>
    </div>
    <div class="asciinema-player-wrapper">
        <div class="asciinema-player" 
             data-cast-file="recordings/index/installation"
             data-cols="120"
             data-rows="48"
             data-autoplay="false"
             data-loop="false"
             data-speed="1.5"
             data-poster="text"
             data-font-size="small">
        </div>
    </div>
</div>

---

## Senaryolar

### Core - Merkezi Yönetim Paneli

İstemci yönetimi, kriptografik anahtar üretimi, otomatik IP tahsisi ve servis kontrolü
tek merkezden yönetilir.

![Core Flow](../assets/static/images/index/flow-diagrams/connection-flow-core.svg)

**Temel Özellikler:**

- İstemci ekleme/kaldırma ve QR kod ile yapılandırma paylaşımı
- Sunucu durumu ve bağlantı istatistikleri
- Güvenlik duvarı yönetimi
- Subnet değişikliği ve IP yeniden haritalama

---

### Multihop - Çift VPN Katmanı

Trafiğinizi harici WireGuard sunucuları üzerinden zincirleyin. Kendi sunucularınızı veya
ticari VPN sağlayıcılarını kullanarak çift şifreleme katmanı oluşturun.

![Multihop Flow](../assets/static/images/index/flow-diagrams/connection-flow-multihop.svg)

**Temel Özellikler:**

- Herhangi bir WireGuard yapılandırma dosyasını içe aktarma
- Otomatik yönlendirme kuralları ve NAT yapılandırması
- Bağlantı izleme ve otomatik yeniden bağlanma
- VPN bağlantı testleri

---

### Ghost - Hayalet Modu

WireGuard trafiğiniz standart HTTPS web trafiği olarak maskelenir. DPI (Derin Paket İnceleme)
sistemlerini ve güvenlik duvarı engellemelerini atlayarak sansüre dirençli bağlantı sağlar.

![Ghost Flow](../assets/static/images/index/flow-diagrams/connection-flow-ghost.svg)

**Temel Özellikler:**

- WebSocket üzerinden tünel (wstunnel)
- Otomatik Let's Encrypt SSL sertifikası
- `phantom-casper` ile istemci yapılandırma dışa aktarımı

---

### MultiGhost - Maksimum Gizlilik

Ghost ve Multihop modüllerini birlikte kullanarak en yüksek düzeyde gizlilik ve sansür
direnci elde edin. Bağlantınız HTTPS olarak maskelenir ve çift VPN katmanı üzerinden
yönlendirilir.

![MultiGhost Flow](../assets/static/images/index/flow-diagrams/connection-flow-multighost.svg)

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

| Yöntem             | Komut                         | Açıklama                            |
|--------------------|-------------------------------|-------------------------------------|
| **İnteraktif CLI** | `phantom-wg`                  | Rich TUI tabanlı kullanıcı arayüzü  |
| **API**            | `phantom-api <modül> <eylem>` | Programatik erişim, JSON çıktı      |
| **Ghost Export**   | `phantom-casper <istemci>`    | Ghost Mode istemci yapılandırması   |

---

## Ticari Marka Bildirimi

Bu proje, [WireGuard](https://www.wireguard.com/) protokolünü kullanan bağımsız bir VPN yönetim
implementasyonudur. Jason A. Donenfeld, ZX2C4 veya Edge Security ile herhangi bir bağlantısı,
ortaklığı veya onayı bulunmamaktadır.

WireGuard® Jason A. Donenfeld'in tescilli ticari markasıdır.

---

## Lisans

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>

Bu yazılım AGPL-3.0 lisansı altında lisanslanmıştır. Detaylar için [LICENSE](https://raw.githubusercontent.com/ARAS-Workspace/phantom-wg/refs/heads/retro/LICENSE) dosyasına bakınız.

Üçüncü taraf lisansları için [THIRD_PARTY_LICENSES](https://raw.githubusercontent.com/ARAS-Workspace/phantom-wg/refs/heads/retro/THIRD_PARTY_LICENSES) dosyasına bakınız.

