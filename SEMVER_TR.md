# Phantom-WG Anlamsal Versiyonlama

## Ürün Versiyonları

Phantom-WG çatısı altında iki ürün hattı bulunmaktadır:

| Ürün                  | Açıklama                                          | Branch |
|-----------------------|---------------------------------------------------|--------|
| **Phantom-WG Modern** | Tam platform (daemon + SPA + auth + bridge'ler)   | main   |
| **Phantom-WG Retro**  | Eski nesil, yalnızca çekirdek sürüm               | retro  |

## Versiyon Hiyerarşisi

**Phantom-WG Modern versiyonu = Phantom Daemon versiyonu.**

Daemon, ürün versiyonunu belirleyen merkezi pakettir.
Diğer tüm bileşenler kendi bağımsız semver döngülerine sahip bağımlılıklardır.

```
Phantom-WG Modern v1.0.0
  └── Phantom Daemon v1.0.0             ← ürün versiyonunun kaynağı
        ├── auth-service v1.1.1         ← bağımlılık
        ├── wireguard-go-bridge v2.1.1  ← bağımlılık
        ├── firewall-bridge v2.1.0      ← bağımlılık
        ├── react-spa (build artifact)  ← release ile birlikte paketlenir
        └── nginx config                ← release ile birlikte paketlenir
```

## Daemon Versiyonu (Ürün Versiyonu)

Daemon versiyonu standart semver'i takip eder ve doğrudan
Phantom-WG Modern release versiyonuna eşlenir:

- **Major** — Kırılgan değişiklikler, mimari değişimler
- **Minor** — Yeni özellikler, yeni API uç noktaları
- **Patch** — Hata düzeltmeleri, güvenlik yamaları

Daemon versiyonu, ürün versiyonu için tek doğruluk kaynağıdır.
Yeni bir Phantom-WG Modern release'i çıkarıldığında, daemon versiyonunu taşır.

### Nerede tanımlı

- `phantom_daemon/__init__.py` → `__version__`
- `GET /api/core/hello` → `version` alanı
- Dashboard durum kartı → kullanıcıya gösterilir

## Bağımlılık Versiyonları

Bağımlılıklar kendi semver'lerini bağımsız olarak yönetir. Versiyonları
geliştirme sürecinde sık sık değişir. Bir bağımlılık versiyon artışı,
daemon (ürün) versiyonunu otomatik olarak **artırmaz**.

Daemon versiyon artışı, entegre ürün — daemon + bağımlılıklar —
yeni bir release kilometre taşına ulaştığında gerçekleşir.

### Bağımlılıklar

| Bileşen                 | Versiyonlama         | Branch                   |
|-------------------------|----------------------|--------------------------|
| **auth-service**        | semver               | dev/auth-service         |
| **wireguard-go-bridge** | semver               | dev/wireguard-go-bridge  |
| **firewall-bridge**     | semver               | dev/firewall-bridge      |
| **compose-bridge**      | semver               | dev/tests/compose-bridge |
| **react-spa**           | package.json version | dev/daemon (embedded)    |

### Vendor Dağıtımı

Bridge binary'leri `vendor-artifacts.phantom.tc` üzerinden dağıtılır.
Her bridge, daemon Dockerfile'ının build sırasında çektiği versiyonlanmış
artifact'ler yayınlar. Vendor deposu `dev/vendor` branch'inde bulunur.

## Retro Versiyonu

Phantom-WG Retro kendi bağımsız versiyon hattını (`core-vX.Y.Z`) kullanır
ve `retro` branch'inde yönetilir. Yukarıda açıklanan daemon versiyon
hiyerarşisini takip etmez.