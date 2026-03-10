import { test, expect } from "@playwright/test";

const ADMIN_USER = "admin";
const CLIENT_COUNT = 5;

// Run-scoped prefix prevents name collisions on retry
const RUN_ID = Date.now().toString(36).slice(-4);
const clientName = (i: number) => `e2e-cl-${RUN_ID}-${String(i).padStart(2, "0")}`;

test.describe.serial("VPN Clients", () => {
  let adminPassword: string;

  test.beforeAll(() => {
    adminPassword = process.env.ADMIN_PASSWORD ?? "";
  });

  // ── Helper: login and navigate to clients page ─────────────────
  async function loginAndGoClients(page: import("@playwright/test").Page) {
    await page.goto("/login");
    await page.getByTestId("login-username").fill(ADMIN_USER);
    await page.getByTestId("login-password").fill(adminPassword);
    await page.getByTestId("login-submit").click();
    await expect(page).toHaveURL("/");
    await page.goto("/vpn/clients");
    await expect(page.getByTestId("vpn-cl-add-client")).toBeVisible();
  }

  // ── 1. Create 5 Clients ────────────────────────────────────────
  test("Create 5 Clients", async ({ page }) => {
    await loginAndGoClients(page);

    for (let i = 1; i <= CLIENT_COUNT; i++) {
      const name = clientName(i);

      await page.getByTestId("vpn-cl-add-client").click();
      const modal = page.getByTestId("vpn-cl-create-modal");
      await expect(modal).toBeVisible();

      const nameInput = page.getByTestId("vpn-cl-create-name");
      await expect(nameInput).toBeVisible();
      await expect(nameInput).toHaveValue("");
      await nameInput.fill(name);

      // Wait for name validation to enable the primary button
      const createBtn = modal.locator(".cds--modal-footer .cds--btn--primary");
      await expect(createBtn).toBeEnabled();
      await createBtn.click();

      // Wait for modal to close and row to appear
      await expect(modal).not.toBeVisible();
      await expect(page.getByTestId(`vpn-cl-row-${name}`)).toBeVisible();

      // Dismiss success notification
      const notification = page.getByTestId("vpn-cl-notification");
      await expect(notification).toBeVisible();
      await notification.locator(".cds--inline-notification__close-button").click();
      await expect(notification).not.toBeVisible();
    }
  });

  // ── 2. Config Export (v4, v6, hybrid for each client) ──────────
  test("Config Export — v4, v6, hybrid", async ({ page }) => {
    await loginAndGoClients(page);

    for (let i = 1; i <= CLIENT_COUNT; i++) {
      const name = clientName(i);

      for (const version of ["v4", "v6", "hybrid"] as const) {
        // Open overflow menu and click config action
        await page.getByTestId(`vpn-cl-overflow-${name}`).click();
        await page.getByTestId(`vpn-cl-action-config-${name}`).click();

        const modal = page.getByTestId("vpn-cl-config-modal");
        await expect(modal).toBeVisible();

        // Select version in select phase (data-testid is on the <select> element itself)
        const versionSelect = page.getByTestId("vpn-cl-config-version");
        await expect(versionSelect).toBeEnabled();
        if (version !== "v4") {
          await versionSelect.selectOption(version);
        }

        // Click "Get Config" and wait for it to be enabled (not in loading state)
        const primaryBtn = modal.locator(
          ".cds--modal-footer .cds--btn--primary"
        );
        await expect(primaryBtn).toBeEnabled();
        await primaryBtn.click();

        // Wait for config snippet to appear
        const snippet = page.getByTestId("vpn-cl-config-snippet");
        await expect(snippet).toBeVisible({ timeout: 10000 });

        // Verify config content contains WireGuard markers
        const content = await snippet.textContent();
        expect(content).toContain("[Interface]");
        expect(content).toContain("[Peer]");

        // Close modal (primary in loaded phase = "Close")
        await expect(primaryBtn).toBeEnabled();
        await primaryBtn.click();
        await expect(modal).not.toBeVisible();

        // Wait for modal reset() timer (300ms useEffect delay) before next open
        await page.waitForTimeout(400);
      }
    }
  });

  // ── 3. View Keys for each client ──────────────────────────────
  test("View Keys", async ({ page }) => {
    await loginAndGoClients(page);

    for (let i = 1; i <= CLIENT_COUNT; i++) {
      const name = clientName(i);

      await page.getByTestId(`vpn-cl-overflow-${name}`).click();
      await page.getByTestId(`vpn-cl-action-keys-${name}`).click();

      const modal = page.getByTestId("vpn-cl-keys-modal");
      await expect(modal).toBeVisible();

      // Verify all 3 key fields are present (PasswordInput with value)
      const keyInputs = modal.locator("input[type='password']");
      await expect(keyInputs).toHaveCount(3);

      // Each key should have a non-empty value
      for (let k = 0; k < 3; k++) {
        const value = await keyInputs.nth(k).inputValue();
        expect(value.length).toBeGreaterThan(0);
      }

      // Close modal
      await modal.locator(".cds--modal-footer .cds--btn--primary").click();
      await expect(modal).not.toBeVisible();
    }
  });

  // ── 4. Revoke 5 Clients ────────────────────────────────────────
  test("Revoke 5 Clients", async ({ page }) => {
    await loginAndGoClients(page);

    for (let i = 1; i <= CLIENT_COUNT; i++) {
      const name = clientName(i);

      await page.getByTestId(`vpn-cl-overflow-${name}`).click();
      await page.getByTestId(`vpn-cl-action-revoke-${name}`).click();

      // Confirm revoke — verify client name shown in danger modal
      const modal = page.getByTestId("vpn-cl-revoke-modal");
      await expect(modal).toBeVisible();
      await expect(page.getByTestId("vpn-cl-revoke-name")).toHaveText(name);

      await modal.locator(".cds--modal-footer .cds--btn--danger").click();

      // Wait for modal to close and row to disappear
      await expect(modal).not.toBeVisible();
      await expect(page.getByTestId(`vpn-cl-row-${name}`)).not.toBeVisible();

      // Dismiss success notification
      const notification = page.getByTestId("vpn-cl-notification");
      await expect(notification).toBeVisible();
      await notification.locator(".cds--inline-notification__close-button").click();
      await expect(notification).not.toBeVisible();
    }
  });
});