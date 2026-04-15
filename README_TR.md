# compose-bridge

Docker Compose v5 SDK üzerine Python FFI. Compose projelerini
programatik olarak yönetir (`up` / `down` / `exec` / `logs` / `ps`) —
`docker compose` subprocess çağrısı yok.

Phantom-WG ekosistemi için dahili test-orkestrasyon aracı. Son
kullanıcıya dağıtılmaz ve public vendor paketinin parçası değildir.

## Amaç

Compose projelerini Python tarafında Docker SDK ile ayağa kaldırıp
test süreci boyunca programatik olarak `exec` göndermek doğrudan mümkün
değildi. Çünkü Docker SDK tekil container seviyesinde çalışır, compose
orkestrasyon yüzeyi bulunmaz. Bu boşluğu kapatmak için compose-bridge Go
tarafındaki Docker Compose SDK'sını FFI üzerinden Python'a açar.

## Kullananlar

- [`dev/daemon`](https://github.com/ARAS-Workspace/phantom-wg/tree/dev/daemon)
  — multihop, chaos ve senaryo E2E testleri,
  [`tools/dev.sh fetch-compose-bridge`](https://github.com/ARAS-Workspace/phantom-wg/blob/dev/daemon/tools/lib/test.sh)
  ile çekiliyor.
- [`dev/firewall-bridge`](https://github.com/ARAS-Workspace/phantom-wg/tree/dev/firewall-bridge)
  — multihop v4/v6 E2E testleri,
  [`fetch_compose_bridge.sh`](https://github.com/ARAS-Workspace/phantom-wg/blob/dev/firewall-bridge/fetch_compose_bridge.sh)
  ile çekiliyor.

İki taraf da en son başarılı publish run'ını takip eder.

## Kullanım

```python
from compose_bridge import ComposeBridge

with ComposeBridge("docker-compose.yml", project_name="mh-test") as bridge:
    bridge.up()

    result = bridge.exec("daemon", ["pytest", "-v"])
    assert result.exit_code == 0

    bridge.down()
```

Bridge oluşturulurken `project_name`'e 6 karakterlik rastgele hex
suffix eklenir; paralel test oturumları aynı Docker namespace'inde
çakışmaz.

Mevcut metodlar: `up`, `down`, `ps`, `exec`, `logs`, `version`. Tüm
hatalar tipli exception'lara (`BridgeError`, `ProjectUpError`,
`ExecError`, …) Go tarafındaki son hata mesajı ile birlikte fırlatılır.

## Geliştirme & Test

```bash
python test_runner.py --build
python test_runner.py
```

`test_runner.py` küçük bir `alpine` compose servisi ayağa kaldırır ve
tüm FFI export'larını uçtan uca doğrular.

## Lisans

AGPL-3.0 — bkz. [LICENSE](LICENSE).
