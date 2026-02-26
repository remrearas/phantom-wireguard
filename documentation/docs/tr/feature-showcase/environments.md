# Test Ortamları

Bu bölümdeki kayıtlar ve testler için kullanılan ortamlar.

## DigitalOcean Recording Environment

Çoklu sunucu gerektiren senaryolar için kullanılan gerçek dünya test ortamı.

**Workflow:** [setup-recording-environment.yml](https://github.com/ARAS-Workspace/phantom-wg/blob/main/.github/retired/setup-recording-environment.yml)

### Ortam Yapısı

| Droplet  | Rol                                        |
|----------|--------------------------------------------|
| `master` | Kayıt yapılan ana makine (asciinema)       |
| `server` | Phantom-WG sunucusu                        |
| `client` | İstemci makinesi                           |
| `exit`   | Multihop çıkış noktası                     |

Tüm droplet'ler aynı VPC içinde yer alır ve private IP üzerinden haberleşir.

### Kullanım Alanları

Bu ortamda çekilen kayıtlar:

- **Multihop VPN** - Client → Server → Exit yapılandırması
- **Ghost Mode** - Gizli tünel kurulumu ve doğrulama
- **Installation** - Sıfırdan kurulum senaryoları

### Çalıştırma

1. GitHub Actions üzerinden workflow'u tetikle
2. Session name belirle (örn: `ghost-recording`)
3. Workflow tamamlandığında IP adreslerini ve setup komutlarını al
4. Master'a SSH ile bağlan ve kayıt senaryosunu uygula

### Senaryo Dosyaları

Kayıt senaryoları: `tools/recording-utilities/recording_environment/scenarios/`

| Dosya                 | Açıklama                         |
|-----------------------|----------------------------------|
| `installation.md`     | Sıfırdan kurulum adımları        |
| `multihop_compact.md` | Multihop VPN kurulum adımları    |
| `ghost_compact.md`    | Ghost Mode kurulum adımları      |

Bu senaryolar gerçek dünya kullanımına uygun, adım adım takip edilebilir anlatımlar içerir.

---

## GitHub Actions Test Ortamları

Otomatik test ve kayıt için kullanılan CI/CD ortamları.

### Entegrasyon Testleri

| Workflow                                                                                                                                      | Açıklama                                    |
|-----------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------|
| [test-development-integration.yml](https://github.com/ARAS-Workspace/phantom-wg/blob/main/.github/workflows/test-development-integration.yml) | Docker container içinde geliştirme testleri |
| [test-production-integration.yml](https://github.com/ARAS-Workspace/phantom-wg/blob/main/.github/workflows/test-production-integration.yml)   | Gerçek kurulum üzerinde üretim testleri     |

### Kayıt Oluşturma

[![Generate CLI Recordings](https://github.com/ARAS-Workspace/phantom-wg/actions/workflows/generate-cli-recordings.yml/badge.svg)](https://github.com/ARAS-Workspace/phantom-wg/actions/workflows/generate-cli-recordings.yml)
[![Generate API Recordings](https://github.com/ARAS-Workspace/phantom-wg/actions/workflows/generate-api-recordings.yml/badge.svg)](https://github.com/ARAS-Workspace/phantom-wg/actions/workflows/generate-api-recordings.yml)

| Workflow                                                                                                                            | Açıklama                 |
|-------------------------------------------------------------------------------------------------------------------------------------|--------------------------|
| [generate-api-recordings.yml](https://github.com/ARAS-Workspace/phantom-wg/blob/main/.github/workflows/generate-api-recordings.yml) | API komutları kayıtları  |
| [generate-cli-recordings.yml](https://github.com/ARAS-Workspace/phantom-wg/blob/main/.github/workflows/generate-cli-recordings.yml) | İnteraktif CLI kayıtları |

Bu workflow'lar `workflow_dispatch` ile manuel tetiklenir ve sonuçlar otomatik olarak dokümantasyona commit edilir.

---

## Ortam Karşılaştırması

| Özellik                    | DigitalOcean         | GitHub Actions       |
|----------------------------|----------------------|----------------------|
| Çoklu sunucu desteği       | Evet                 | Hayır                |
| Gerçek network trafiği     | Evet                 | Sınırlı              |
| Maliyet                    | Kullanım başına      | Ücretsiz             |
| Otomatik kayıt             | Manuel               | Otomatik             |
| Kullanım amacı             | Karmaşık senaryolar  | Tekil işlemler       |

