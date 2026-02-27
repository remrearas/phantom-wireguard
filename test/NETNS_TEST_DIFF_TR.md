# Upstream netns.sh Entegrasyon Raporu

## Kaynak

- **Upstream (değiştirilmemiş):** [`test/netns_upstream.sh`](netns_upstream.sh)
- **Yamalanmış:** [`test/netns.sh`](netns.sh) (3 satır değiştirilmiş)
- **Fark dosyası:** [`test/netns_upstream.diff`](netns_upstream.diff)
- **Orijin:** https://git.zx2c4.com/wireguard-go/tree/tests/netns.sh

## Yaklaşım

`test/netns_upstream.sh` wireguard-go projesinden alınan **değiştirilmemiş** orijinal test betiğidir.
`test/netns.sh` container uyumluluğu için 3 satırı yamalanmış çalışma kopyasıdır.
`test/test.sh` Python FFI köprüsünü `$program` olarak vererek `netns.sh`'i çalıştırır.

```
test.sh  →  netns.sh $WRAPPER
                        ↓
                $WRAPPER wg1
                        ↓
          python3 bridge_program.py wg1
                        ↓
              wireguard_go_bridge.so
                    Run("wg1")
```

## Değişiklikler (3 satır)

Tüm değişiklikler `/proc/sys/net/core/message_cost` erişimini, bu sysctl
parametresinin bulunmadığı ortamlarda (Docker Desktop macOS VM, minimal
çekirdekler) hata vermeyecek şekilde düzenler:

```diff
-    printf "$orig_message_cost" > /proc/sys/net/core/message_cost
+    printf "$orig_message_cost" > /proc/sys/net/core/message_cost 2>/dev/null || true

-orig_message_cost="$(< /proc/sys/net/core/message_cost)"
+orig_message_cost="$(cat /proc/sys/net/core/message_cost 2>/dev/null || echo 0)"

-printf 0 > /proc/sys/net/core/message_cost
+printf 0 > /proc/sys/net/core/message_cost 2>/dev/null || true
```

Test mantığı, ağ topolojisi veya WireGuard yapılandırması değiştirilmemiştir.

## Dosya Yapısı

| Dosya                 | Açıklama                                                      |
|-----------------------|---------------------------------------------------------------|
| `netns_upstream.sh`   | Upstream wireguard-go testi — değiştirilmemiş orijinal        |
| `netns.sh`            | Container uyumluluğu için 3 satırı yamalanmış çalışma kopyası |
| `netns_upstream.diff` | `diff -u netns_upstream.sh netns.sh` çıktısı                  |
| `test.sh`             | Ortam hazırlığı, sarmalayıcı oluşturma ve netns.sh çağrısı    |
| `bridge_program.py`   | wireguard-go ikili dosyasının FFI karşılığı                   |

## test.sh Ne Yapar

1. `wireguard_go_bridge.so` konumunu belirler
2. `WIREGUARD_GO_BRIDGE_LIB_PATH` ve `PYTHONPATH` ortam değişkenlerini tanımlar
3. `bridge_program.py`'yi arka planda başlatan geçici bir kabuk sarmalayıcısı oluşturur
4. `netns.sh`'i bu sarmalayıcı ile `$program` olarak çalıştırır

## bridge_program.py — wireguard-go Karşılığı

| wireguard-go ikili dosyası   | bridge_program.py               |
|------------------------------|---------------------------------|
| `tun.CreateTUN(isim, mtu)`   | `Run(isim, günlükSeviyesi)` FFI |
| `device.NewDevice()`         | (Run içinde)                    |
| `ipc.UAPIOpen()`             | (Run içinde)                    |
| `ipc.UAPIListen()`           | (Run içinde)                    |
| `device.IpcHandle(bağlantı)` | (Run içinde)                    |
| `signal.Notify(SIGTERM)`     | (Run içinde)                    |

`Run()` wireguard-go `main.go` ön plan modunu birebir yansıtır — tek FFI çağrısı.

## Fark Dosyasının Yeniden Oluşturulması

```bash
curl -sL "https://git.zx2c4.com/wireguard-go/plain/tests/netns.sh" -o test/netns_upstream.sh
diff -u test/netns_upstream.sh test/netns.sh > test/netns_upstream.diff
```