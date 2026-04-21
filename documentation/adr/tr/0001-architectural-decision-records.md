# ADR-0001 — Architectural Decision Records

## Durum

Kabul Edildi — 2026-04-20

## Bağlam

Phantom-WG Mac uygulaması, sıradan bir VPN istemcisi değil; Retro döneminin mirası üzerine Ghost Mode (wstunnel + WireGuard), Split-Tunneling, Reset Connection ve Session-Scoped Logs gibi ayrı yapı taşları eklenerek olgunlaşmış bir ürün.

Bu yapı taşlarının her birinin ardında *X yerine Y neden seçildi* sorusuna karşılık gelen somut bir karar var.

Projeyi solo geliştirici olarak yürüttüğüm için mimari kararlar bu süre boyunca kendi zihnimde, cihazımda tuttuğum notlarda ve uzun commit mesajlarında dağınık biçimde birikti. Bu dağınıklık hızlı iterasyonda işimi kolaylaştırıyordu, ancak kalıcı bir belleğe dönüşmüyor; zımni bilgiye evriliyordu. Kritik kararları 1.2.0 sürümünün yapısında kristalize ettim; 1.2.1 sürümüyle bu kararlara son cilalamaları yaptığımda yazılı ve değişmez bir kayda bağlamaya karar verdim. Phantom-WG Mac mimarisinin bu noktada retrospektif olarak belgelenebilecek olgunluğa ulaştığını belirtmek doğru olacaktır. Mevcut olgun mimari mühendislik el kitabı (engineering-handbook) altında anlatılırken, gelecekteki karar değişiklikleri bu ADR dizininde kayıt altına alınır.

## Karar

1. **Format — Nygard ADR.** Her belge dört bölümden oluşur:
   
   - **Durum**: `Önerildi` / `Kabul Edildi` / `Yerini ADR-XXXX Aldı` / `İptal Edildi`
   - **Bağlam**: kararı doğuran gerekçe, kısıt, alternatifler
   - **Karar**: somut olarak ne yapıldı
   - **Sonuçlar**: bu karar hangi ödünleri getirdi, nelere yol açtı
   
2. **Numaralandırma — sıralı, dört basamaklı.** `0001`, `0002`, ... Numaralar boşluk bırakılmadan artar; silinen ADR olsa bile numarası yeniden kullanılmaz.

3. **Dil akışı — TR taslağı → onay → EN çeviri.** ADR'lar önce Türkçe yazılır, üzerinden geçilir, Production (Üretim) onayı alır; ardından İngilizce çevirisi hazırlanır. İki dil paraleldir ama kronoloji seridir.

4. **Dizin yapısı.** Dokümantasyon kod tabanıyla aynı repoda (`ARAS-Workspace/phantom-wg`), `app/mac` branch'inde yaşar. İki paralel dizin altında ayrışır:
   ```
   documentation/
   ├── adr/                          — ADR'lar (karar değişim kayıtları)
   │   ├── tr/
   │   │   └── NNNN-title.md
   │   └── en/
   │       └── NNNN-title.md
   └── engineering-handbook/         — olgun mimari anlatımları (retrospektif)
       ├── README.md                 — handbook girişi (EN)
       ├── Turkish/
       │   └── Topic-Name.md
       └── English/
           └── Topic-Name.md
   ```

5. **Değiştirilmezlik ilkesi.** Kabul edilmiş bir ADR düzeltme amacıyla değiştirilmez. Yalnızca imla/dil düzeltmeleri yapılabilir. Kararın kendisi değişiyorsa:
   - Eski ADR durumu `Yerini ADR-XXXX Aldı` olarak güncellenir.
   - Yeni ADR açılır; bağlam bölümünde önceki karar referans gösterilir.

6. **Ölçek ayrımı: ADR vs engineering-handbook.** Bu iki yapı birbirini tamamlar:
   - **ADR** tek bir kararı kayıt altına alır — *"X yapıldı, Y değil, çünkü Z"*. Karar alındığı anda yazılır, değişmez. Yalnızca mimariyi değiştiren kararlar ADR'a girer; mevcut yapının bütününü tarif etmek ADR'ın işi değil.
   - **Engineering handbook** mevcut olgun mimarinin bütünsel, retrospektif anlatımını tutar — bir bütün olarak okunur, mimari değişiklik kristalize olduğunda güncellenir.

   Bir ADR mevcut handbook yapısına referans verebilir; handbook bir ADR'a referans vermez.

7. **Kapsam — yalnızca Mac uygulaması.** Bu dizin (`documentation/adr/`) yalnızca Mac istemci uygulamasının mimari kararlarını içerir.

8. **Engineering handbook başlangıç doluluğu.** Mac mimarisinin mevcut olgun durumu `documentation/engineering-handbook/` dizini altında iki bağımsız belge ile kurulmuştur ([README](../../engineering-handbook/README_TR.md)):

   Bu belgeler `d02e032` kod commit'ine sabitlenmiştir. Mimaride değişen bir şey olduğunda yeni bir ADR açılır; karar kabul edilip kristalize olunca handbook güncellenir.

## Sonuçlar

- Her yeni mimari karar aynı formata doğal uyumlanır.
- Değiştirilmezlik kuralı ilk yazımda netliği zorunlu kılar.
- TR/EN ikili akış yazım yükünü artırır, dil engeli olmadan okunur kılar.
- Eski kararların tarihçesi (yerini alma zinciri) izlenebilir kalır.

