# Upstream netns.sh Entegrasyon Raporu

## Kaynak

| Dosya | Açıklama |
|-------|----------|
| [`netns_upstream.sh`](netns_upstream.sh) | Upstream wireguard-go testi — değiştirilmemiş orijinal |
| [`netns.sh`](netns.sh) | Container uyumluluğu için yamalanmış kopya (3 satır) |
| [`netns_upstream.diff`](netns_upstream.diff) | Upstream ile yamalanmış arasındaki fark |
| [`test.sh`](test.sh) | Ortam hazırlığı, sarmalayıcı oluşturma, netns.sh çalıştırma |
| [`bridge_program.py`](bridge_program.py) | wireguard-go ikili dosyasının FFI karşılığı |

**Orijin:** https://git.zx2c4.com/wireguard-go/tree/tests/netns.sh

## Nasıl Çalışır

```
test.sh → netns.sh $WRAPPER
                      ↓
              $WRAPPER wg1
                      ↓
        python3 bridge_program.py wg1
                      ↓
            wireguard_go_bridge.so
                  Run("wg1")
```

`Run()` wireguard-go `main.go` ön plan modunu birebir yansıtır:
CreateTUN → NewDevice → UAPIOpen → UAPIListen → accept döngüsü → SIGTERM bekle.

## Değişiklikler (3 satır)

`/proc/sys/net/core/message_cost` erişimini, bu sysctl parametresinin
bulunmadığı ortamlarda (Docker Desktop macOS VM, minimal çekirdekler)
hata vermeyecek şekilde düzenler:

```diff
-    printf "$orig_message_cost" > /proc/sys/net/core/message_cost
+    printf "$orig_message_cost" > /proc/sys/net/core/message_cost 2>/dev/null || true

-orig_message_cost="$(< /proc/sys/net/core/message_cost)"
+orig_message_cost="$(cat /proc/sys/net/core/message_cost 2>/dev/null || echo 0)"

-printf 0 > /proc/sys/net/core/message_cost
+printf 0 > /proc/sys/net/core/message_cost 2>/dev/null || true
```

Test mantığı, ağ topolojisi veya WireGuard yapılandırması değiştirilmemiştir.

## Çalıştırma

Docker test container'ı içinde:
```bash
tests/netns-test/test.sh /workspace/wireguard_go_bridge.so
```

Veya bağımsız:
```bash
docker run --rm --privileged --cap-add NET_ADMIN \
  --device /dev/net/tun:/dev/net/tun \
  wireguard-go-bridge-v2-test:latest \
  bash -c "tests/netns-test/test.sh /workspace/wireguard_go_bridge.so"
```

## Fark Dosyasının Yeniden Oluşturulması

```bash
cd tests/netns-test
curl -sL "https://git.zx2c4.com/wireguard-go/plain/tests/netns.sh" -o netns_upstream.sh
diff -u netns_upstream.sh netns.sh > netns_upstream.diff
```