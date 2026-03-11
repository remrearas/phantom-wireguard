import { test, expect } from "@playwright/test";

const ADMIN_USER = "admin";

test.describe.serial("VPN DNS", () => {
  let adminPassword: string;

  // Store original values so we can restore after edits
  let origV4Primary: string;
  let origV4Secondary: string;
  let origV6Primary: string;
  let origV6Secondary: string;

  test.beforeAll(() => {
    adminPassword = process.env.ADMIN_PASSWORD ?? "";
  });

  // ── Helper: login and navigate to DNS page ──────────────────────
  async function loginAndGoDns(page: import("@playwright/test").Page) {
    await page.goto("/login");
    await page.getByTestId("login-username").fill(ADMIN_USER);
    await page.getByTestId("login-password").fill(adminPassword);
    await page.getByTestId("login-submit").click();
    await expect(page).toHaveURL("/");
    await page.goto("/vpn/dns");
    await expect(page.getByTestId("vpn-dns-card-v4")).toBeVisible({ timeout: 10_000 });
  }

  // ── 1. Both cards load ──────────────────────────────────────────
  test("IPv4 and IPv6 cards show DNS values", async ({ page }) => {
    await loginAndGoDns(page);

    // IPv4
    await expect(page.getByTestId("vpn-dns-card-v4")).toBeVisible();
    origV4Primary = (await page.getByTestId("vpn-dns-v4-primary").textContent()) ?? "";
    origV4Secondary = (await page.getByTestId("vpn-dns-v4-secondary").textContent()) ?? "";
    expect(origV4Primary).toBeTruthy();

    // IPv6
    await expect(page.getByTestId("vpn-dns-card-v6")).toBeVisible();
    origV6Primary = (await page.getByTestId("vpn-dns-v6-primary").textContent()) ?? "";
    origV6Secondary = (await page.getByTestId("vpn-dns-v6-secondary").textContent()) ?? "";
    expect(origV6Primary).toBeTruthy();
  });

  // ── 2. Edit IPv4 DNS ────────────────────────────────────────────
  test("Edit IPv4 DNS with valid values", async ({ page }) => {
    await loginAndGoDns(page);

    await page.getByTestId("vpn-dns-edit-v4").click();
    const modal = page.getByTestId("vpn-dns-edit-modal");
    await expect(modal).toBeVisible();

    const primaryInput = page.getByTestId("vpn-dns-edit-primary");
    const secondaryInput = page.getByTestId("vpn-dns-edit-secondary");

    await primaryInput.clear();
    await primaryInput.fill("9.9.9.9");
    await secondaryInput.clear();
    await secondaryInput.fill("149.112.112.112");

    // Save — modal should close on success
    await modal.locator(".cds--modal-footer .cds--btn--primary").click();
    await expect(modal).not.toBeVisible();

    // Success notification on the page
    await expect(page.getByTestId("vpn-dns-notification")).toBeVisible();

    // Card reflects new values
    await expect(page.getByTestId("vpn-dns-v4-primary")).toHaveText("9.9.9.9");
    await expect(page.getByTestId("vpn-dns-v4-secondary")).toHaveText("149.112.112.112");
  });

  // ── 3. Edit IPv6 DNS ────────────────────────────────────────────
  test("Edit IPv6 DNS with valid values", async ({ page }) => {
    await loginAndGoDns(page);

    await page.getByTestId("vpn-dns-edit-v6").click();
    const modal = page.getByTestId("vpn-dns-edit-modal");
    await expect(modal).toBeVisible();

    const primaryInput = page.getByTestId("vpn-dns-edit-primary");
    const secondaryInput = page.getByTestId("vpn-dns-edit-secondary");

    await primaryInput.clear();
    await primaryInput.fill("2620:fe::fe");
    await secondaryInput.clear();
    await secondaryInput.fill("2620:fe::9");

    await modal.locator(".cds--modal-footer .cds--btn--primary").click();
    await expect(modal).not.toBeVisible();

    await expect(page.getByTestId("vpn-dns-notification")).toBeVisible();
    await expect(page.getByTestId("vpn-dns-v6-primary")).toHaveText("2620:fe::fe");
    await expect(page.getByTestId("vpn-dns-v6-secondary")).toHaveText("2620:fe::9");
  });

  // ── 4. Invalid IPv4 — error shown inside modal ─────────────────
  test("Invalid IPv4 DNS shows error in modal", async ({ page }) => {
    await loginAndGoDns(page);

    await page.getByTestId("vpn-dns-edit-v4").click();
    const modal = page.getByTestId("vpn-dns-edit-modal");
    await expect(modal).toBeVisible();

    const primaryInput = page.getByTestId("vpn-dns-edit-primary");
    await primaryInput.clear();
    await primaryInput.fill("not-an-ip");

    await modal.locator(".cds--modal-footer .cds--btn--primary").click();

    // Modal stays open and shows inline error
    await expect(modal).toBeVisible();
    await expect(
      modal.locator(".cds--inline-notification--error"),
    ).toBeVisible();

    // Close via cancel
    await modal.locator(".cds--modal-footer .cds--btn--secondary").click();
    await expect(modal).not.toBeVisible();
  });

  // ── 5. Invalid IPv6 — error shown inside modal ─────────────────
  test("Invalid IPv6 DNS shows error in modal", async ({ page }) => {
    await loginAndGoDns(page);

    await page.getByTestId("vpn-dns-edit-v6").click();
    const modal = page.getByTestId("vpn-dns-edit-modal");
    await expect(modal).toBeVisible();

    const primaryInput = page.getByTestId("vpn-dns-edit-primary");
    await primaryInput.clear();
    await primaryInput.fill("zzz::invalid");

    await modal.locator(".cds--modal-footer .cds--btn--primary").click();

    // Modal stays open and shows inline error
    await expect(modal).toBeVisible();
    await expect(
      modal.locator(".cds--inline-notification--error"),
    ).toBeVisible();

    // Close via cancel
    await modal.locator(".cds--modal-footer .cds--btn--secondary").click();
    await expect(modal).not.toBeVisible();
  });

  // ── 6. Restore original DNS values ─────────────────────────────
  test("Restore original DNS values", async ({ page }) => {
    await loginAndGoDns(page);

    // Restore IPv4
    await page.getByTestId("vpn-dns-edit-v4").click();
    const modal = page.getByTestId("vpn-dns-edit-modal");
    await expect(modal).toBeVisible();

    const primaryInput = page.getByTestId("vpn-dns-edit-primary");
    const secondaryInput = page.getByTestId("vpn-dns-edit-secondary");

    await primaryInput.clear();
    await primaryInput.fill(origV4Primary);
    await secondaryInput.clear();
    await secondaryInput.fill(origV4Secondary);
    await modal.locator(".cds--modal-footer .cds--btn--primary").click();
    await expect(modal).not.toBeVisible();

    await expect(page.getByTestId("vpn-dns-v4-primary")).toHaveText(origV4Primary);

    // Restore IPv6
    await page.getByTestId("vpn-dns-edit-v6").click();
    await expect(modal).toBeVisible();

    await primaryInput.clear();
    await primaryInput.fill(origV6Primary);
    await secondaryInput.clear();
    await secondaryInput.fill(origV6Secondary);
    await modal.locator(".cds--modal-footer .cds--btn--primary").click();
    await expect(modal).not.toBeVisible();

    await expect(page.getByTestId("vpn-dns-v6-primary")).toHaveText(origV6Primary);
  });
});
