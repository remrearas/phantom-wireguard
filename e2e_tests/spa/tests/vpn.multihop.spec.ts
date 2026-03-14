import { test, expect } from "@playwright/test";
import { execSync } from "child_process";
import { writeFileSync, unlinkSync } from "fs";
import { tmpdir } from "os";
import { join } from "path";

const ADMIN_USER = "admin";
const EXIT_NAME = "spa-exit";

// ── Helpers (top-level, same pattern as vpn.wireguard.spec.ts) ──

function containerName(project: string, service: string): string {
  return `${project}-${service}-1`;
}

function dockerExecOn(container: string, cmd: string): string {
  return execSync(`docker exec ${container} ${cmd}`, {
    encoding: "utf-8",
    timeout: 30_000,
  }).trim();
}

function dockerExecRc(container: string, cmd: string): { rc: number; stdout: string } {
  try {
    const stdout = dockerExecOn(container, cmd);
    return { rc: 0, stdout };
  } catch (err: unknown) {
    const e = err as { status?: number; stdout?: string };
    return { rc: e.status ?? 1, stdout: (e.stdout ?? "").trim() };
  }
}

function writeConfigToContainer(config: string, container: string): void {
  const tmpFile = join(tmpdir(), `wg0-mh-${Date.now()}.conf`);
  writeFileSync(tmpFile, config, "utf8");
  try {
    execSync(`docker cp ${tmpFile} ${container}:/etc/wireguard/wg0.conf`, { stdio: "pipe" });
  } finally {
    unlinkSync(tmpFile);
  }
}

async function apiCall<T>(
  page: import("@playwright/test").Page,
  method: string,
  path: string,
  body?: Record<string, unknown>,
): Promise<T> {
  return await page.evaluate(
    async ({ method, path, body }) => {
      const token = localStorage.getItem("token") ?? "";
      const r = await fetch(path, {
        method,
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        ...(body ? { body: JSON.stringify(body) } : {}),
      });
      return r.json();
    },
    { method, path, body },
  );
}

function info(label: string, value: string) {
  console.log(`  [INFO] ${label}: ${value}`);
}

// ── Login helper ────────────────────────────────────────────────

async function loginAndGoMultihop(
  page: import("@playwright/test").Page,
  password: string,
) {
  await page.goto("/login");
  await page.getByTestId("login-username").fill(ADMIN_USER);
  await page.getByTestId("login-password").fill(password);
  await page.getByTestId("login-submit").click();
  await expect(page).toHaveURL("/");
  await page.goto("/vpn/multihop");
  await expect(page.getByTestId("vpn-mh-status-tile")).toBeVisible({
    timeout: 10_000,
  });
}

// ── Suite ────────────────────────────────────────────────────────

test.describe.serial("VPN Multihop", () => {
  let adminPassword: string;
  let exitConf: string;
  let projectName: string;

  test.beforeAll(() => {
    adminPassword = process.env.ADMIN_PASSWORD ?? "";
    const b64 = process.env.EXIT_CONF_B64 ?? "";
    exitConf = b64 ? Buffer.from(b64, "base64").toString("utf-8") : "";
    projectName = process.env.COMPOSE_PROJECT_NAME ?? "";
  });

  // ── 1. Page loads + cleanup stale state from previous runs ────
  test("Multihop page shows status card", async ({ page }) => {
    await loginAndGoMultihop(page, adminPassword);
    await expect(page.getByTestId("vpn-mh-status-tile")).toBeVisible();
    await expect(page.getByTestId("vpn-mh-status-tag")).toBeVisible();

    // Cleanup stale exit from previous failed runs (if any)
    const row = page.getByTestId(`vpn-mh-row-${EXIT_NAME}`);
    if (await row.isVisible().catch(() => false)) {
      await apiCall(page, "POST", "/api/multihop/disable");
      await page.reload();
      await expect(page.getByTestId("vpn-mh-status-tile")).toBeVisible({ timeout: 10_000 });

      await page.getByTestId(`vpn-mh-overflow-${EXIT_NAME}`).click();
      await page.getByTestId(`vpn-mh-action-remove-${EXIT_NAME}`).click();
      await expect(row).not.toBeVisible({ timeout: 5_000 });
    }
  });

  // ── 2. Import invalid config — error shown ────────────────────
  test("Import invalid config shows error", async ({ page }) => {
    await loginAndGoMultihop(page, adminPassword);

    await page.getByTestId("vpn-mh-import-btn").click();
    const modal = page.getByTestId("vpn-mh-import-modal");
    await expect(modal).toBeVisible();

    await page.getByTestId("vpn-mh-import-name").fill("bad-exit");
    await page.getByTestId("vpn-mh-import-config").fill("not a valid config");

    await modal.locator(".cds--modal-footer .cds--btn--primary").click();

    await expect(
      modal.locator(".cds--inline-notification--error"),
    ).toBeVisible({ timeout: 5_000 });

    await modal.locator(".cds--modal-footer .cds--btn--secondary").click();
    await expect(modal).not.toBeVisible();
  });

  // ── 3. Import valid exit config ───────────────────────────────
  test("Import exit config via modal", async ({ page }) => {
    test.skip(!exitConf, "EXIT_CONF not provided");
    await loginAndGoMultihop(page, adminPassword);

    await page.getByTestId("vpn-mh-import-btn").click();
    const modal = page.getByTestId("vpn-mh-import-modal");
    await expect(modal).toBeVisible();

    await page.getByTestId("vpn-mh-import-name").fill(EXIT_NAME);
    await page.getByTestId("vpn-mh-import-config").fill(exitConf);

    const submitBtn = modal.locator(".cds--modal-footer .cds--btn--primary");
    await expect(submitBtn).toBeEnabled();
    await submitBtn.click();

    await expect(modal).not.toBeVisible({ timeout: 10_000 });
    await expect(page.getByTestId(`vpn-mh-row-${EXIT_NAME}`)).toBeVisible();
  });

  // ── 4. Enable multihop ─────────────────────────────────────────
  // Carbon Toggle data-testid lands on wrapper div, not the clickable
  // <button>. Clicking the wrapper does not reliably trigger onToggle
  // in Playwright. We enable via authenticated API call and reload —
  // the UI reads toggle state from GET /api/multihop/status on mount.
  test("Enable multihop via API", async ({ page }) => {
    test.skip(!exitConf, "EXIT_CONF not provided");
    await loginAndGoMultihop(page, adminPassword);

    const res = await apiCall<{ ok: boolean }>(
      page, "POST", "/api/multihop/enable", { name: EXIT_NAME },
    );
    expect(res.ok).toBe(true);

    await page.reload();
    await expect(page.getByTestId("vpn-mh-active-name")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("vpn-mh-active-name")).toHaveText(EXIT_NAME);

    info("multihop", "enabled");
  });

  // ── 5. Verify daemon → exit-server connectivity (ping) ────────
  test("Daemon reaches exit-server via tunnel", async () => {
    test.skip(!exitConf, "EXIT_CONF not provided");

    // Wait for WG handshake
    await new Promise((r) => setTimeout(r, 5_000));

    const daemon = containerName(projectName, "daemon");
    const { rc, stdout } = dockerExecRc(daemon, "ping -c 3 -W 3 10.0.2.1");
    info("daemon → exit-server (10.0.2.1)", rc === 0 ? "OK" : "FAIL");
    for (const line of stdout.split("\n").slice(-3)) {
      info("  ping", line);
    }
    expect(rc).toBe(0);
  });

  // ── 6. WG client connects through multihop chain ──────────────
  test("WG client connects and pings through multihop", async ({ page }) => {
    test.skip(!exitConf, "EXIT_CONF not provided");
    test.setTimeout(60_000);
    await loginAndGoMultihop(page, adminPassword);

    // Create a client via API
    const createRes = await apiCall<{ ok: boolean; data: { name: string } }>(
      page, "POST", "/api/core/clients/assign", { name: "mh-e2e-client" },
    );
    expect(createRes.ok).toBe(true);
    info("client created", "mh-e2e-client");

    // Get client WG config (v4)
    const configRes = await apiCall<{ ok: boolean; data: string }>(
      page, "POST", "/api/core/clients/config", { name: "mh-e2e-client", version: "v4" },
    );
    expect(configRes.ok).toBe(true);

    const rawConfig = Buffer.from(configRes.data, "base64").toString("utf8");

    // Adapt config for wg-client container
    const adaptedLines: string[] = [];
    for (const line of rawConfig.split("\n")) {
      const stripped = line.trim();
      if (stripped.startsWith("DNS")) continue;
      let adapted = line;
      if (stripped.startsWith("Address") && stripped.includes("/32")) {
        adapted = adapted.replace("/32", "/24");
      }
      if (stripped.startsWith("AllowedIPs") && stripped.includes("0.0.0.0/0")) {
        adapted = adapted.replace("0.0.0.0/0", "10.0.0.0/8");
      }
      adaptedLines.push(adapted);
    }
    const clientConf = adaptedLines.join("\n");
    info("client config", `${clientConf.split("\n").length} lines`);

    // Write config and bring up WG on wg-client container
    const wgClient = containerName(projectName, "wg-client");
    writeConfigToContainer(clientConf, wgClient);
    dockerExecOn(wgClient, "wg-quick up wg0");

    // Wait for handshake
    await new Promise((r) => setTimeout(r, 5_000));

    // Show WG state
    const wgShow = dockerExecRc(wgClient, "wg show wg0");
    info("wg show", wgShow.stdout.includes("latest handshake") ? "handshake OK" : "no handshake");

    // Ping daemon WG interface (gateway)
    const pingGw = dockerExecRc(wgClient, "ping -c 3 -W 3 10.8.0.1");
    info("client → daemon WG (10.8.0.1)", pingGw.rc === 0 ? "OK" : "FAIL");
    expect(pingGw.rc).toBe(0);

    // Ping exit-server through multihop
    const pingExit = dockerExecRc(wgClient, "ping -c 3 -W 3 10.0.2.1");
    info("client → exit-server (10.0.2.1) via multihop", pingExit.rc === 0 ? "OK" : "FAIL");
    expect(pingExit.rc).toBe(0);

    // Cleanup: tear down wg-client
    dockerExecRc(wgClient, "wg-quick down wg0");
  });

  // ── 7. Disable multihop ────────────────────────────────────────
  // Same API approach as enable — reliable state transition.
  test("Disable multihop via API", async ({ page }) => {
    test.skip(!exitConf, "EXIT_CONF not provided");
    await loginAndGoMultihop(page, adminPassword);

    const res = await apiCall<{ ok: boolean }>(page, "POST", "/api/multihop/disable");
    expect(res.ok).toBe(true);

    await page.reload();
    await expect(page.getByTestId("vpn-mh-active-name")).not.toBeVisible({ timeout: 10_000 });

    info("multihop", "disabled");
  });

  // ── 8. Cleanup — remove exit and revoke client ────────────────
  test("Cleanup — remove exit and revoke client", async ({ page }) => {
    test.skip(!exitConf, "EXIT_CONF not provided");
    await loginAndGoMultihop(page, adminPassword);

    // Remove exit via overflow menu
    await page.getByTestId(`vpn-mh-overflow-${EXIT_NAME}`).click();
    await page.getByTestId(`vpn-mh-action-remove-${EXIT_NAME}`).click();
    await expect(page.getByTestId(`vpn-mh-row-${EXIT_NAME}`)).not.toBeVisible({ timeout: 5_000 });

    // Revoke client via API
    await apiCall(page, "POST", "/api/core/clients/revoke", { name: "mh-e2e-client" });

    info("cleanup", "exit removed + client revoked");
  });
});
