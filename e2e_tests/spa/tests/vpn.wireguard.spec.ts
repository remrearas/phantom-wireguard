import {expect, test} from "@playwright/test";
import {execSync} from "child_process";
import {unlinkSync, writeFileSync} from "fs";
import {tmpdir} from "os";
import {join} from "path";

const ADMIN_USER = "admin";

// Run-scoped prefix prevents name collisions on retry
const RUN_ID = Date.now().toString(36).slice(-4);
const CLIENT_NAME = `e2e-wg-${RUN_ID}`;

// Container name: resolved from COMPOSE_PROJECT_NAME injected by runner.py
const project = process.env.COMPOSE_PROJECT_NAME ?? "spa";
const WG_CONTAINER = `${project}-wg-client-1`;

// ── Helpers ──────────────────────────────────────────────────────

async function loginAndGoWireGuard(page: import("@playwright/test").Page, password: string) {
  await page.goto("/login");
  await page.getByTestId("login-username").fill(ADMIN_USER);
  await page.getByTestId("login-password").fill(password);
  await page.getByTestId("login-submit").click();
  await expect(page).toHaveURL("/");
  await page.goto("/vpn/wireguard");
  await expect(page.getByTestId("vpn-wg-table")).toBeVisible({ timeout: 10_000 });
}

function dockerExec(cmd: string): void {
  execSync(`docker exec ${WG_CONTAINER} ${cmd}`, { stdio: "pipe" });
}

function writeConfigToContainer(config: string): void {
  const tmpFile = join(tmpdir(), `wg0-${Date.now()}.conf`);
  writeFileSync(tmpFile, config, "utf8");
  try {
    execSync(`docker cp ${tmpFile} ${WG_CONTAINER}:/etc/wireguard/wg0.conf`, { stdio: "pipe" });
  } finally {
    unlinkSync(tmpFile);
  }
}

// ── Suite ────────────────────────────────────────────────────────

test.describe.serial("WireGuard", () => {
  let adminPassword: string;

  test.beforeAll(() => {
    adminPassword = process.env.ADMIN_PASSWORD ?? "";
  });

  test.afterAll(() => {
    // Ensure WireGuard is brought down even if tests fail mid-way
    try {
      dockerExec("wg-quick down wg0");
    } catch {
      // Already down — ignore
    }
  });

  // ── 1. Setup: Create client, connect WireGuard ─────────────────
  test("Setup: Create client and connect", async ({ page }) => {
    await page.goto("/login");
    await page.getByTestId("login-username").fill(ADMIN_USER);
    await page.getByTestId("login-password").fill(adminPassword);
    await page.getByTestId("login-submit").click();
    await expect(page).toHaveURL("/");

    // Create client via daemon API (browser fetch uses stored auth token)
    const assignRes = await page.evaluate(async ({ name }: { name: string }) => {
      const token = localStorage.getItem("token") ?? "";
      const r = await fetch("/api/core/clients/assign", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ name }),
      });
      return r.json();
    }, { name: CLIENT_NAME });
    expect(assignRes.ok).toBe(true);

    // Get v4 WireGuard config (daemon returns base64-encoded text)
    const wgConfigB64: string = await page.evaluate(async ({ name }: { name: string }) => {
      const token = localStorage.getItem("token") ?? "";
      const r = await fetch("/api/core/clients/config", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ name, version: "v4" }),
      });
      const j = await r.json();
      return j.ok ? (j.data as string) : "";
    }, { name: CLIENT_NAME });
    const wgConfig = Buffer.from(wgConfigB64, "base64").toString("utf8");
    expect(wgConfig).toContain("[Interface]");
    expect(wgConfig).toContain("[Peer]");

    // Write config to wg-client container via docker cp
    writeConfigToContainer(wgConfig);

    // Bring up WireGuard tunnel
    dockerExec("wg-quick up wg0");

    // Poll until handshake occurs (daemon sees latest_handshake > 0)
    await expect
      .poll(
        async () => {
          return await page.evaluate(async ({name}: { name: string }) => {
            const token = localStorage.getItem("token") ?? "";
            const r = await fetch("/api/core/wireguard/peer", {
              method: "POST",
              headers: {"Content-Type": "application/json", Authorization: `Bearer ${token}`},
              body: JSON.stringify({name}),
            });
            const j = await r.json();
            return j.ok ? (j.data as { latest_handshake: number }).latest_handshake : 0;
          }, {name: CLIENT_NAME});
        },
        { timeout: 15_000, intervals: [1_000] }
      )
      .toBeGreaterThan(0);
  });

  // ── 2. Interface card ──────────────────────────────────────────
  test("Interface card shows server info", async ({ page }) => {
    await loginAndGoWireGuard(page, adminPassword);

    const card = page.getByTestId("vpn-wg-interface");
    await expect(card).toBeVisible();
    // Listen port should be visible
    await expect(card).toContainText("51820");
    // Public key field should have content (not empty)
    const kvValue = card.locator(".wireguard__kv-value").first();
    const keyText = await kvValue.textContent();
    expect(keyText?.length).toBeGreaterThan(8);
  });

  // ── 3. Peer row — Online status ────────────────────────────────
  test("Peer row shows Online after handshake", async ({ page }) => {
    await loginAndGoWireGuard(page, adminPassword);

    const row = page.getByTestId(`vpn-wg-row-${CLIENT_NAME}`);
    await expect(row).toBeVisible();

    // Online badge (Carbon Tag type="green" renders as cds--tag--green)
    await expect(row.locator(".cds--tag--green")).toBeVisible();
  });

  // ── 4. Peer detail modal ───────────────────────────────────────
  test("Peer detail modal shows full peer info", async ({ page }) => {
    await loginAndGoWireGuard(page, adminPassword);

    await page.getByTestId(`vpn-wg-overflow-${CLIENT_NAME}`).click();
    await page.getByTestId(`vpn-wg-action-details-${CLIENT_NAME}`).click();

    const modal = page.getByTestId("vpn-wg-detail-modal");
    await expect(modal).toBeVisible();

    // Full public key should be visible in detail (not truncated)
    const detailMono = modal.locator(".wireguard__detail-mono").first();
    const keyText = await detailMono.textContent();
    expect(keyText?.length).toBeGreaterThan(20);

    // Allowed IPs section should have content
    await expect(modal.locator(".wireguard__allowed-ips")).toBeVisible();

    // Close modal
    await modal.locator(".cds--modal-footer .cds--btn--primary").click();
    await expect(modal).not.toBeVisible();
  });

  // ── 5. Per-peer refresh ────────────────────────────────────────
  test("Per-peer refresh updates row", async ({ page }) => {
    await loginAndGoWireGuard(page, adminPassword);

    await page.getByTestId(`vpn-wg-overflow-${CLIENT_NAME}`).click();
    await page.getByTestId(`vpn-wg-action-refresh-${CLIENT_NAME}`).click();

    // Row remains visible after refresh
    await expect(page.getByTestId(`vpn-wg-row-${CLIENT_NAME}`)).toBeVisible();
    // Still Online
    await expect(
      page.getByTestId(`vpn-wg-row-${CLIENT_NAME}`).locator(".cds--tag--green")
    ).toBeVisible();
  });

  // ── 6. Cleanup: Disconnect and revoke ─────────────────────────
  test("Cleanup: Disconnect and revoke client", async ({ page }) => {
    // Bring down WireGuard tunnel
    dockerExec("wg-quick down wg0");

    // Revoke client via API
    await page.goto("/login");
    await page.getByTestId("login-username").fill(ADMIN_USER);
    await page.getByTestId("login-password").fill(adminPassword);
    await page.getByTestId("login-submit").click();
    await expect(page).toHaveURL("/");

    const revokeRes = await page.evaluate(async ({ name }: { name: string }) => {
      const token = localStorage.getItem("token") ?? "";
      const r = await fetch("/api/core/clients/revoke", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ name }),
      });
      return r.json();
    }, { name: CLIENT_NAME });
    expect(revokeRes.ok).toBe(true);

    // Navigate to WireGuard page — revoked peer should be gone
    await page.goto("/vpn/wireguard");
    await expect(page.getByTestId("vpn-wg-table")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByTestId(`vpn-wg-row-${CLIENT_NAME}`)).not.toBeVisible();
  });
});