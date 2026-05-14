# ADR-0001 — Architectural Decision Records

## Durum

Kabul Edildi — 2026-04-20

## Bağlam

Phantom-WG Mac uygulaması, sıradan bir VPN istemcisi değil; Retro döneminin mirası üzerine Ghost Mode (wstunnel + WireGuard), Split-Tunneling, Reset Connection ve Session-Scoped Logs gibi ayrı yapı taşları eklenerek olgunlaşmış bir ürün.

Bu yapı taşlarının her birinin ardında *X yerine Y neden seçildi* sorusuna karşılık gelen somut bir karar var.

Projeyi solo geliştirici olarak yürüttüğüm için mimari kararlar bu süre boyunca kendi zihnimde, cihazımda tuttuğum notlarda ve uzun commit mesajlarında dağınık biçimde birikti. Bu dağınıklık hızlı iterasyonda işimi kolaylaştırıyordu, ancak kalıcı bir belleğe dönüşmüyor; zımni bilgiye evriliyordu. Kritik kararları 1.2.0 sürümünün yapısında kristalize ettim; 1.2.1 sürümüyle bu kararlara son cilalamaları yaptığımda yazılı ve değişmez bir kayda bağlamaya karar verdim. Phantom-WG Mac mimarisinin bu noktada retrospektif olarak belgelenebilecek olgunluğa ulaştığını belirtmek doğru olacaktır. Mimari kararların yazılı izinin tutulduğu yer bu ADR dizinidir; gelecekteki karar değişiklikleri de burada kayıt altına alınır.

## Karar

1. **Format — Nygard ADR.** Her belge dört bölümden oluşur:
   
   - **Durum**: `Önerildi` / `Kabul Edildi` / `Yerini ADR-XXXX Aldı` / `İptal Edildi`
   - **Bağlam**: kararı doğuran gerekçe, kısıt, alternatifler
   - **Karar**: somut olarak ne yapıldı
   - **Sonuçlar**: bu karar hangi ödünleri getirdi, nelere yol açtı
   
2. **Numaralandırma — sıralı, dört basamaklı.** `0001`, `0002`, ... Numaralar boşluk bırakılmadan artar; silinen ADR olsa bile numarası yeniden kullanılmaz.

3. **Dil akışı — TR taslağı → onay → EN çeviri.** ADR'lar önce Türkçe yazılır, üzerinden geçilir, Production (Üretim) onayı alır; ardından İngilizce çevirisi hazırlanır. İki dil paraleldir ama kronoloji seridir.

4. **Dizin yapısı.** Dokümantasyon kod tabanıyla aynı repoda (`ARAS-Workspace/phantom-wg`), `app/mac` branch'inde yaşar:
   ```
   Documentation/
   └── ADR/
       ├── Turkish/
       │   └── NNNN-title.md
       └── English/
           └── NNNN-title.md
   ```

5. **Değiştirilmezlik ilkesi.** Kabul edilmiş bir ADR düzeltme amacıyla değiştirilmez. Yalnızca imla/dil düzeltmeleri yapılabilir. Kararın kendisi değişiyorsa:
   - Eski ADR durumu `Yerini ADR-XXXX Aldı` olarak güncellenir.
   - Yeni ADR açılır; bağlam bölümünde önceki karar referans gösterilir.

6. **ADR'ın sınırı.** Bir ADR tek bir kararı kayıt altına alır — *"X yapıldı, Y değil, çünkü Z"*. Karar alındığı anda yazılır ve sonrasında değişmez. Yalnızca mimariyi değiştiren kararlar ADR'a girer; mevcut yapının bütününü tarif etmek ADR'ın işi değil.

7. **Kapsam — yalnızca Mac uygulaması.** Bu dizin (`Documentation/ADR/`) yalnızca Mac istemci uygulamasının mimari kararlarını içerir.

## Sonuçlar

- Her yeni mimari karar aynı formata doğal uyumlanır.
- Değiştirilmezlik kuralı ilk yazımda netliği zorunlu kılar.
- TR/EN ikili akış yazım yükünü artırır, dil engeli olmadan okunur kılar.
- Eski kararların tarihçesi (yerini alma zinciri) izlenebilir kalır.

