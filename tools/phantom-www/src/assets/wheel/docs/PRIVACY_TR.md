 <!--
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
-->

# Gizlilik Bildirimi — Spin & Deploy (Provider Wheel)

**Son Güncelleme:** Şubat 2026

## Genel Bakış

Spin & Deploy, Phantom-WG projesinin bir parçası olan açık kaynaklı, tamamen istemci tarafında çalışan bir sağlayıcı seçim aracıdır. Sunucu ve çıkış düğümü yapılandırmalarınız için gizlilik odaklı VPS sağlayıcılarını rastgele seçmenize yardımcı olur. Bu bildirim, aracın nasıl çalıştığını, hangi verileri işlediğini ve listelenen sağlayıcıların ne anlama geldiğini açıklamaktadır.

## Listelenen Sağlayıcılar Hakkında

Bu araçta listelenen sağlayıcılar, arama motorları üzerinde yapılan araştırmalar ve yapay zekâ destekli analizler sonucunda belirlenmiştir. Seçim kriterleri şunlardır:

- **Kripto para ödeme desteği** — Her sağlayıcı, ödeme yöntemi olarak bir veya daha fazla kripto parayı (BTC, XMR, ETH, LTC) kabul etmektedir
- **Gizlilik odaklı yaklaşım** — Barındırma hizmetlerinde kullanıcı gizliliğine saygı duyduğu bilinen sağlayıcılar
- **Yerleşik varlık** — Her sağlayıcının resmî bir alan adı, tanınmış bir kullanıcı tabanı ve barındırma topluluklarında bir geçmişi bulunmaktadır

Bu sağlayıcılar, Phantom-WG yapılandırmalarınızı barındırmak için seçenekler olarak sunulmaktadır. Phantom-WG, yapılandırmanızla tam uyum sağlamak için bir araç olarak burada bulunmaktadır. Hangi sağlayıcıyı seçeceğinize karar veremediyseniz, bu araç bu kararı vermenize yardımcı olabilir.

## Üçüncü Taraf Sorumluluk Reddi

**Phantom-WG'nin listelenen sağlayıcılardan herhangi biriyle ortaklığı, iş birliği, sponsorluğu veya ticari ilişkisi bulunmamaktadır.** Sağlayıcılar bu araçta yalnızca yukarıda açıklanan kriterlere dayanarak yer almaktadır. Dâhil edilmeleri, hizmetlerinin onaylanması, tavsiye edilmesi veya garanti edilmesi anlamına gelmez.

Her sağlayıcı bağımsız olarak faaliyet göstermektedir ve kendi hizmet şartları, gizlilik politikaları ve kabul edilebilir kullanım politikaları geçerlidir. Herhangi bir hizmet satın almadan önce ilgili sağlayıcının şartlarını incelemek ve kabul etmek sizin sorumluluğunuzdadır.

## Affiliate Bağlantısı Yoktur

Bu araç **hiçbir affiliate bağlantısı, yönlendirme kodu veya izleme parametresi içermez**. Tüm sağlayıcı URL'leri doğrudan resmî web sitelerine yönlendirmektedir. Phantom-WG, sağlayıcı seçiminizden veya sonraki herhangi bir satın alma işleminizden hiçbir malî kazanç, komisyon veya tazminat almamaktadır.

## Bu Araç Hangi Verileri Toplar?

### Hiçbiri.

Bu araç kesinlikle **hiçbir veri toplamaz, iletmez veya saklamaz**. Ayrıntılı olarak:

| Konu                     | Detay                                                                                                     |
|--------------------------|-----------------------------------------------------------------------------------------------------------|
| **Analitik**             | Yoktur — izleme betiği, piksel veya telemetri bulunmaz                                                    |
| **Çerezler**             | Yoktur — hiçbir çerez oluşturulmaz veya okunmaz                                                           |
| **Ağ istekleri**         | Aynı kaynaktan `providers.json` yüklemek için tek bir `fetch` çağrısı — harici API çağrısı yoktur         |
| **Kullanıcı girdisi**    | Araç, buton tıklamaları dışında hiçbir kullanıcı girdisi kabul etmez                                      |
| **Depolama**             | localStorage, sessionStorage, IndexedDB veya başka herhangi bir tarayıcı depolama mekanizması kullanılmaz |
| **Sunucu tarafı işleme** | Yoktur — araç, arka ucu olmayan statik bir HTML/CSS/JS sayfasıdır                                         |

### Çark Nasıl Çalışır

1. Sağlayıcı verileri yerel bir `providers.json` dosyasından yüklenir (aynı kaynak, harici istek yok)
2. Çark dönüşü, tarayıcınızda `Math.random()` kullanır — seçim tamamen istemci tarafındadır
3. Hiçbir seçim sonucu kaydedilmez, iletilmez veya herhangi bir yerde saklanmaz
4. Sayfayı kapattığınızda tüm durum tamamen silinir

## Harici Bağlantılar

**Bu araç hiçbir harici bağlantı kurmaz.** Fontlar, stil dosyaları, betikler ve sağlayıcı verileri dâhil tüm varlıklar proje içinde paketlenmiştir ve yerel olarak yüklenir. Uygulama kodu tarafından hiçbir harici CDN, API veya üçüncü taraf hizmetine bağlantı kurulmaz.

## Barındırma ve Altyapı

[phantom.tc](https://www.phantom.tc) üzerinden erişildiğinde, bu araç **Cloudflare Pages** aracılığıyla sunulmaktadır. Bu nedenle standart web altyapısı geçerlidir:

- Cloudflare, sayfayı sunarken standart HTTP meta verilerini (IP adresi, User-Agent, istek başlıkları) işleyebilir
- Bu, bir CDN üzerinden sunulan herhangi bir web sitesi için geçerli olup bu araca özgü değildir
- Phantom-WG, herhangi bir Cloudflare analitik, günlük kaydı veya izleme özelliğini yapılandırmaz, bunlara erişmez veya kontrol etmez
- Phantom-WG tarafından ek telemetri, çerez veya izleme betiği eklenmez

Cloudflare'ın verileri nasıl işlediğine dair ayrıntılar için [Cloudflare Gizlilik Politikası](https://www.cloudflare.com/privacypolicy/) sayfasına bakınız.

CDN düzeyindeki herhangi bir işlemden kaçınmayı tercih ediyorsanız, depoyu klonlayarak HTML dosyalarını doğrudan tarayıcınızda açabilirsiniz.

## Açık Kaynak ve Şeffaflık

Bu araç, Phantom-WG açık kaynaklı projesinin bir parçasıdır. Sağlayıcı listesi, seçim mantığı ve bu gizlilik bildirimi dâhil olmak üzere kaynak kodun tamamı GitHub üzerinde herkese açık ve denetlenebilir durumdadır.

Sağlayıcı listesi, herkesin inceleyebileceği düz bir `providers.json` dosyasında tutulmaktadır. Seçim algoritması, ağırlıklandırma, yanlılık veya önceden belirlenmiş sonuçlar içermeyen standart tarayıcı rastgeleleştirmesini kullanmaktadır.

## Bu Bildirimde Yapılacak Değişiklikler

Bu gizlilik bildirimi, araç geliştikçe güncellenebilir. Değişiklikler, güncellenmiş tarih ile bu dosyaya yansıtılır.

## İletişim

Bu gizlilik bildirimi veya Spin & Deploy aracı hakkında sorularınız için:

**Rıza Emre ARAS** — [r.emrearas@proton.me](mailto:r.emrearas@proton.me)
