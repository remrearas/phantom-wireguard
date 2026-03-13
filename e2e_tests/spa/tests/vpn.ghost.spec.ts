import { test, expect } from "@playwright/test";
import { execSync } from "child_process";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";

const ADMIN_USER = "admin";

// ── Cert generation helper ──────────────────────────────────────

interface KeyPair {
  cert: string;
  key: string;
}

function generateKeypair(cn: string): KeyPair {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "ghost-e2e-"));
  const certPath = path.join(tmpDir, "cert.pem");
  const keyPath = path.join(tmpDir, "key.pem");
  execSync(
    `openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 ` +
      `-keyout ${keyPath} -out ${certPath} -days 1 -nodes -subj "/CN=${cn}" ` +
      `-addext "subjectAltName=DNS:${cn}"`,
    { stdio: "pipe" },
  );
  const cert = fs.readFileSync(certPath, "utf-8");
  const key = fs.readFileSync(keyPath, "utf-8");
  fs.rmSync(tmpDir, { recursive: true });
  return { cert, key };
}

// ── Tests ───────────────────────────────────────────────────────

test.describe.serial("VPN Ghost", () => {
  let adminPassword: string;
  let certA: KeyPair; // CN=ghost.test.local
  let certB: KeyPair; // CN=other.test.local (for mismatch)

  test.beforeAll(() => {
    adminPassword = process.env.ADMIN_PASSWORD ?? "";
    certA = generateKeypair("ghost.test.local");
    certB = generateKeypair("other.test.local");
  });

  // ── Helper: login and navigate ────────────────────────────────

  async function loginAndGoGhost(page: import("@playwright/test").Page) {
    await page.goto("/login");
    await page.getByTestId("login-username").fill(ADMIN_USER);
    await page.getByTestId("login-password").fill(adminPassword);
    await page.getByTestId("login-submit").click();
    await expect(page).toHaveURL("/");
    await page.goto("/vpn/ghost");
    // Wait for either wizard or status to appear
    await expect(
      page
        .getByTestId("ghost-enable-domain")
        .or(page.getByTestId("ghost-status-running")),
    ).toBeVisible({ timeout: 10_000 });
  }

  async function ensureDisabled(page: import("@playwright/test").Page) {
    const disableBtn = page.getByTestId("ghost-disable-btn");
    if (await disableBtn.isVisible()) {
      await disableBtn.click();
      const modal = page.getByTestId("ghost-disable-modal");
      await expect(modal).toBeVisible();
      await modal
        .locator(".cds--modal-footer .cds--btn--danger")
        .click();
      await expect(page.getByTestId("ghost-enable-domain")).toBeVisible({
        timeout: 10_000,
      });
    }
  }

  // ── 1. Page loads with wizard ─────────────────────────────────

  test("Ghost page shows wizard when disabled", async ({ page }) => {
    await loginAndGoGhost(page);
    await ensureDisabled(page);
    await expect(page.getByTestId("ghost-enable-domain")).toBeVisible();
  });

  // ── 2. Domain SAN mismatch — client-side warning ─────────────

  test("Cert for different domain shows SAN warning", async ({ page }) => {
    await loginAndGoGhost(page);
    await ensureDisabled(page);

    // Step 1: domain
    await page.getByTestId("ghost-enable-domain").fill("ghost.test.local");
    await page.getByTestId("ghost-enable-domain-next").click();

    // Step 2: cert B (CN=other.test.local) → SAN mismatch warning
    await page.getByTestId("ghost-enable-cert").fill(certB.cert);
    await expect(
      page.locator(".cds--inline-notification--warning"),
    ).toBeVisible();
  });

  // ── 3. Keypair mismatch — API error ───────────────────────────

  test("Keypair mismatch shows error on confirm", async ({ page }) => {
    await loginAndGoGhost(page);
    await ensureDisabled(page);

    // Step 1: domain
    await page.getByTestId("ghost-enable-domain").fill("ghost.test.local");
    await page.getByTestId("ghost-enable-domain-next").click();

    // Step 2: cert A + key B (mismatch)
    await page.getByTestId("ghost-enable-cert").fill(certA.cert);
    await page.getByTestId("ghost-enable-key").fill(certB.key);
    await page.getByTestId("ghost-enable-cert-next").click();

    // Step 3: confirm → API rejects
    await page.getByTestId("ghost-enable-submit").click();
    await expect(
      page.locator(".cds--inline-notification--error"),
    ).toBeVisible();
  });

  // ── 4. Manual cert — enable + status + disable ────────────────

  test("Enable with valid cert, verify status, disable", async ({ page }) => {
    await loginAndGoGhost(page);
    await ensureDisabled(page);

    // Step 1: domain
    await page.getByTestId("ghost-enable-domain").fill("ghost.test.local");
    await page.getByTestId("ghost-enable-domain-next").click();

    // Step 2: valid cert + key
    await page.getByTestId("ghost-enable-cert").fill(certA.cert);
    await page.getByTestId("ghost-enable-key").fill(certA.key);
    await page.getByTestId("ghost-enable-cert-next").click();

    // Step 3: confirm
    await page.getByTestId("ghost-enable-submit").click();

    // Done
    await expect(page.getByTestId("ghost-enable-done")).toBeVisible({
      timeout: 10_000,
    });
    await page.getByTestId("ghost-enable-view-status").click();

    // Status — verify fields
    await expect(page.getByTestId("ghost-status-running")).toBeVisible();
    await expect(page.getByTestId("ghost-status-enabled")).toBeVisible();
    await expect(page.getByTestId("ghost-status-bind-url")).toBeVisible();
    await expect(page.getByTestId("ghost-status-path-prefix")).toBeVisible();

    // Disable
    await page.getByTestId("ghost-disable-btn").click();
    const modal = page.getByTestId("ghost-disable-modal");
    await expect(modal).toBeVisible();
    await modal
      .locator(".cds--modal-footer .cds--btn--danger")
      .click();
    await expect(modal).not.toBeVisible();

    // Back to wizard
    await expect(page.getByTestId("ghost-enable-domain")).toBeVisible({
      timeout: 10_000,
    });
  });

  // ── 5. Self-signed generator — enable + status + disable ──────

  test("Generate self-signed cert, enable, verify, disable", async ({
    page,
  }) => {
    await loginAndGoGhost(page);
    await ensureDisabled(page);

    // Step 1: domain
    await page.getByTestId("ghost-enable-domain").fill("ghost.test.local");
    await page.getByTestId("ghost-enable-domain-next").click();

    // Step 2: open generator
    await page.getByTestId("ghost-enable-generate-toggle").click();
    await expect(page.getByTestId("ghost-gen-validity")).toBeVisible();

    // Generate (default 1 year)
    await page.getByTestId("ghost-gen-submit").click();

    // TextAreas populated with generated PEM
    await expect(page.getByTestId("ghost-enable-cert")).toHaveValue(
      /BEGIN CERTIFICATE/,
      { timeout: 10_000 },
    );
    await expect(page.getByTestId("ghost-enable-key")).toHaveValue(
      /BEGIN PRIVATE KEY/,
    );

    // Cert preview visible
    await expect(page.locator(".ghost-wizard__cert-preview")).toBeVisible();

    await page.getByTestId("ghost-enable-cert-next").click();

    // Step 3: confirm
    await page.getByTestId("ghost-enable-submit").click();

    // Done
    await expect(page.getByTestId("ghost-enable-done")).toBeVisible({
      timeout: 10_000,
    });
    await page.getByTestId("ghost-enable-view-status").click();

    // Status
    await expect(page.getByTestId("ghost-status-running")).toBeVisible();

    // Disable
    await page.getByTestId("ghost-disable-btn").click();
    const modal = page.getByTestId("ghost-disable-modal");
    await expect(modal).toBeVisible();
    await modal
      .locator(".cds--modal-footer .cds--btn--danger")
      .click();
    await expect(modal).not.toBeVisible();

    // Back to wizard
    await expect(page.getByTestId("ghost-enable-domain")).toBeVisible({
      timeout: 10_000,
    });
  });
});