# Upstream netns.sh Integration

## Source

- **Upstream (unmodified):** [`test/netns_upstream.sh`](netns_upstream.sh)
- **Patched:** [`test/netns.sh`](netns.sh) (3 lines modified)
- **Diff:** [`test/netns_upstream.diff`](netns_upstream.diff)
- **Origin:** https://git.zx2c4.com/wireguard-go/tree/tests/netns.sh

## Approach

`test/netns_upstream.sh` is the **unmodified** upstream test from wireguard-go.
`test/netns.sh` is the working copy with 3 lines patched for container compatibility.
`test/test.sh` runs `netns.sh` with our Python FFI bridge as `$program`.

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

## Modifications (3 lines)

All changes make `/proc/sys/net/core/message_cost` access non-fatal
when the sysctl does not exist (Docker Desktop macOS VM, minimal kernels):

```diff
-    printf "$orig_message_cost" > /proc/sys/net/core/message_cost
+    printf "$orig_message_cost" > /proc/sys/net/core/message_cost 2>/dev/null || true

-orig_message_cost="$(< /proc/sys/net/core/message_cost)"
+orig_message_cost="$(cat /proc/sys/net/core/message_cost 2>/dev/null || echo 0)"

-printf 0 > /proc/sys/net/core/message_cost
+printf 0 > /proc/sys/net/core/message_cost 2>/dev/null || true
```

No test logic, network topology, or WireGuard configuration is modified.

## Files

| File                  | Purpose                                              |
|-----------------------|------------------------------------------------------|
| `netns_upstream.sh`   | Upstream wireguard-go test — unmodified original     |
| `netns.sh`            | Working copy with 3 lines patched for container      |
| `netns_upstream.diff` | `diff -u netns_upstream.sh netns.sh`                 |
| `test.sh`             | Environment setup + wrapper creation + exec netns.sh |
| `bridge_program.py`   | wireguard-go binary drop-in via FFI                  |

## What test.sh does

1. Locates `wireguard_go_bridge.so`
2. Sets `WIREGUARD_GO_BRIDGE_LIB_PATH` and `PYTHONPATH`
3. Creates a temporary shell wrapper that backgrounds `bridge_program.py`
4. Runs `netns.sh` with the wrapper as `$program`

## What bridge_program.py does (wireguard-go equivalent)

| wireguard-go binary        | bridge_program.py                  |
|----------------------------|------------------------------------|
| `tun.CreateTUN(name, mtu)` | `Run(name, logLevel)` via FFI      |
| `device.NewDevice()`       | (included in Run)                  |
| `ipc.UAPIOpen()`           | (included in Run)                  |
| `ipc.UAPIListen()`         | (included in Run)                  |
| `device.IpcHandle(conn)`   | (included in Run)                  |
| `signal.Notify(SIGTERM)`   | (included in Run)                  |

`Run()` mirrors `main.go` foreground mode exactly — single FFI call.

## Regenerating the diff

```bash
curl -sL "https://git.zx2c4.com/wireguard-go/plain/tests/netns.sh" -o test/netns_upstream.sh
diff -u test/netns_upstream.sh test/netns.sh > test/netns_upstream.diff
```