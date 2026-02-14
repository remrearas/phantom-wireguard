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

## Derleme & Tedarik Zinciri

### iOS Uygulaması

 iOS uygulamasının kaynak kodu bu reponun [`ios/main`](https://github.com/ARAS-Workspace/phantom-wg/tree/ios/main) dalında yer alır.
Uygulama GitHub Actions üzerinden derlenir ve Apple'a iletilir.

| Detay       | Değer                                                                    |
|-------------|--------------------------------------------------------------------------|
| Versiyon    | `1.0.2`                                                                  |
| Build       | `20260213.1313`                                                          |
| Kaynak kodu | [`ios/main`](https://github.com/ARAS-Workspace/phantom-wg/tree/ios/main) |

**Build Action:** [phantom-wg /actions/runs/21983006116](https://github.com/ARAS-Workspace/phantom-wg/actions/runs/21983006116)

### wstunnel — iOS için FFI

Upstream [wstunnel](https://github.com/erebe/wstunnel) projesi, Rust tabanlı bir
WebSocket tünelleme aracıdır. iOS üzerinde kullanabilmek için FFI (Foreign Function
Interface) aracılığıyla statik kütüphane olarak derlenir ve **WstunnelKit** adıyla
paketlenir — iOS uygulamasının bağlandığı, Swift uyumlu bir framework.

Derleme süreci GitHub Actions üzerinde çalışır. Workflow `ios/main` dalını checkout
ettiğinde, Rust kaynak kodunu Apple hedefleri için derler ve framework'ü `Libraries/`
dizini altında üretir. Ortaya çıkan artifact **checksum doğrulaması** içerir; böylece
iOS projesi, bağladığı binary'nin CI'ın ürettiğiyle birebir aynı olduğunu
doğrulayabilir — elle derleme yok, doğrulanmamış binary yok.

| Kaynak               | Link                                                                                                       |
|----------------------|------------------------------------------------------------------------------------------------------------|
| Kaynak (ios etiketi) | [wstunnel/tree/ios/v10.5.2](https://github.com/ARAS-Workspace/wstunnel/tree/ios/v10.5.2)                   |
| Build Action         | [wstunnel /actions/runs/ 21937285430](https://github.com/ARAS-Workspace/wstunnel/actions/runs/21937285430) |

### WireGuard — iOS Fork'u

iOS üzerindeki WireGuard entegrasyonu, upstream [wireguard-apple](https://github.com/WireGuard/wireguard-apple)
projesinin minimal bir fork'una dayanır ve Phantom-WG'nin Ghost Mode gereksinimleri
doğrultusunda uyarlanmıştır.

| Kaynak    | Link                                                                                                              |
|-----------|-------------------------------------------------------------------------------------------------------------------|
| Fork dalı | [wireguard-apple / tree / ios/ phantom-wg](https://github.com/ARAS-Workspace/wireguard-apple/tree/ios/phantom-wg) |

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
