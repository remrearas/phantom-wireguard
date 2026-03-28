# Phantom-WG iOS İstemci (Client) Uygulaması (Beta)

> iOS'ta Ghost Mode — WireGuard over WebSocket

Phantom-WG iOS istemcisi, Ghost Mode'u cebinize taşır. Phantom-WG sunucunuza
WebSocket tüneli (wstunnel) üzerinden bağlanır ve WireGuard trafiğinizi standart
HTTPS trafiği olarak aktarır.

**TestFlight betasına katılın:**

[![TestFlight](https://img.shields.io/badge/TestFlight-Betaya_Katıl-blue?style=for-the-badge&logo=apple)](https://testflight.apple.com/join/5Kt55AXd)

---

## Nasıl Çalışır

### Sunucu Kurulumu

Sunucu yöneticisi, `phantom-casper-ios` komutu ile istemci yapılandırmasını dışa aktarır.
Bu komut; WireGuard arayüz ayarlarını, peer bilgilerini ve wstunnel parametrelerini içeren
bir JSON çıktısı üretir — iOS uygulamasına taranmaya veya aktarılmaya hazır halde.

![Sunucu tarafı son kullanıcı iş akışı](assets/feature-ios-app/recordings/end-user-workflow-opt.gif)

### İstemci Bağlantısı

iOS tarafında uygulama, yapılandırmayı okur ve bağlantıyı kurar: wstunnel sunucuya
bir WebSocket tüneli açar, WireGuard ise trafiği bu tünel üzerinden yönlendirir —
tümü uygulama içinde şeffaf bir şekilde gerçekleşir.

![iOS istemci bağlantısı](assets/feature-ios-app/ios_recording.gif)

---

## Lisans

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>

Bu yazılım AGPL-3.0 lisansı altında lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakınız.

Üçüncü taraf lisansları için [THIRD_PARTY_LICENSES](THIRD_PARTY_LICENSES) dosyasına bakınız.

---

<!--suppress HtmlDeprecatedAttribute -->

<div align="center">

![Phantom Logo](documentation/docs/assets/static/images/phantom-horizontal-master-midnight-phantom.svg)

</div>
