# Upstream netns.sh Integration

## Source

| File | Description |
|------|-------------|
| [`netns_upstream.sh`](netns_upstream.sh) | Upstream wireguard-go test — unmodified |
| [`netns.sh`](netns.sh) | Patched copy (3 lines) for container compatibility |
| [`netns_upstream.diff`](netns_upstream.diff) | `diff -u` between upstream and patched |
| [`test.sh`](test.sh) | Orchestrator — sets env, creates wrapper, runs netns.sh |
| [`bridge_program.py`](bridge_program.py) | wireguard-go drop-in replacement via FFI `Run()` |

**Origin:** https://git.zx2c4.com/wireguard-go/tree/tests/netns.sh

## How It Works

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

`Run()` mirrors wireguard-go `main.go` foreground mode:
CreateTUN → NewDevice → UAPIOpen → UAPIListen → accept loop → wait for SIGTERM.

## Modifications (3 lines)

Makes `/proc/sys/net/core/message_cost` access non-fatal for environments
where this sysctl does not exist (Docker Desktop macOS VM, minimal kernels):

```diff
-    printf "$orig_message_cost" > /proc/sys/net/core/message_cost
+    printf "$orig_message_cost" > /proc/sys/net/core/message_cost 2>/dev/null || true

-orig_message_cost="$(< /proc/sys/net/core/message_cost)"
+orig_message_cost="$(cat /proc/sys/net/core/message_cost 2>/dev/null || echo 0)"

-printf 0 > /proc/sys/net/core/message_cost
+printf 0 > /proc/sys/net/core/message_cost 2>/dev/null || true
```

No test logic, network topology, or WireGuard configuration is modified.

## Running

Inside the Docker test container:
```bash
tests/netns-test/test.sh /workspace/wireguard_go_bridge.so
```

Or standalone:
```bash
docker run --rm --privileged --cap-add NET_ADMIN \
  --device /dev/net/tun:/dev/net/tun \
  wireguard-go-bridge-v2-test:latest \
  bash -c "tests/netns-test/test.sh /workspace/wireguard_go_bridge.so"
```

## Regenerating the diff

```bash
cd tests/netns-test
curl -sL "https://git.zx2c4.com/wireguard-go/plain/tests/netns.sh" -o netns_upstream.sh
diff -u netns_upstream.sh netns.sh > netns_upstream.diff
```