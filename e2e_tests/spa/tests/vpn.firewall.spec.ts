import { test, expect } from "@playwright/test";

const ADMIN_USER = "admin";

test.describe.serial("VPN Firewall", () => {
  let adminPassword: string;

  test.beforeAll(() => {
    adminPassword = process.env.ADMIN_PASSWORD ?? "";
  });

  // ── Helper: login and navigate to firewall page ─────────────────
  async function loginAndGoFirewall(page: import("@playwright/test").Page) {
    await page.goto("/login");
    await page.getByTestId("login-username").fill(ADMIN_USER);
    await page.getByTestId("login-password").fill(adminPassword);
    await page.getByTestId("login-submit").click();
    await expect(page).toHaveURL("/");
    await page.goto("/vpn/firewall");
    await expect(page.getByTestId("vpn-fw-table")).toBeVisible({ timeout: 10_000 });
  }

  // ── 1. Groups table loads ───────────────────────────────────────
  test("Groups table shows firewall groups", async ({ page }) => {
    await loginAndGoFirewall(page);

    // Table should have at least one row (daemon creates default groups)
    const rows = page.locator("[data-testid^='vpn-fw-row-']");
    const count = await rows.count();
    expect(count).toBeGreaterThan(0);

    // Each row should have an overflow menu
    for (let i = 0; i < count; i++) {
      const row = rows.nth(i);
      await expect(row.locator("[data-testid^='vpn-fw-overflow-']")).toBeVisible();
    }
  });

  // ── 2. Group detail modal ───────────────────────────────────────
  test("Group detail modal shows JSON sections", async ({ page }) => {
    await loginAndGoFirewall(page);

    // Get the first group's name from the first row's overflow menu testid
    const firstOverflow = page.locator("[data-testid^='vpn-fw-overflow-']").first();
    await firstOverflow.click();

    // Click "View Details" on the first group
    const detailAction = page.locator("[data-testid^='vpn-fw-action-details-']").first();
    await detailAction.click();

    // Modal should open
    const modal = page.getByTestId("vpn-fw-detail-modal");
    await expect(modal).toBeVisible();

    // All three CodeSnippet sections should be present
    await expect(page.getByTestId("vpn-fw-detail-group")).toBeVisible();
    await expect(page.getByTestId("vpn-fw-detail-rules")).toBeVisible();
    await expect(page.getByTestId("vpn-fw-detail-routing")).toBeVisible();

    // Group section should contain valid JSON with expected fields
    const groupSnippet = page.getByTestId("vpn-fw-detail-group");
    const groupText = await groupSnippet.textContent();
    expect(groupText).toContain('"name"');
    expect(groupText).toContain('"group_type"');
    expect(groupText).toContain('"enabled"');

    // Close modal
    await modal.locator(".cds--modal-footer .cds--btn--primary").click();
    await expect(modal).not.toBeVisible();
  });

  // ── 3. Raw table modal ──────────────────────────────────────────
  test("Raw table modal shows nftables JSON", async ({ page }) => {
    await loginAndGoFirewall(page);

    // Open overflow on first group and click "Raw Table"
    const firstOverflow = page.locator("[data-testid^='vpn-fw-overflow-']").first();
    await firstOverflow.click();

    const rawAction = page.locator("[data-testid^='vpn-fw-action-raw-']").first();
    await rawAction.click();

    // Modal should open with CodeSnippet
    const modal = page.getByTestId("vpn-fw-raw-modal");
    await expect(modal).toBeVisible();

    const snippet = page.getByTestId("vpn-fw-raw-snippet");
    await expect(snippet).toBeVisible();

    // Raw table should contain JSON content (nftables structure)
    const content = await snippet.textContent();
    expect(content).toBeTruthy();
    expect(content!.length).toBeGreaterThan(2); // More than just "{}"

    // Close modal
    await modal.locator(".cds--modal-footer .cds--btn--primary").click();
    await expect(modal).not.toBeVisible();
  });

  // ── 4. Refresh button ───────────────────────────────────────────
  test("Refresh reloads groups table", async ({ page }) => {
    await loginAndGoFirewall(page);

    // Click refresh
    await page.getByTestId("vpn-fw-refresh").click();

    // Table should still be visible after refresh
    await expect(page.getByTestId("vpn-fw-table")).toBeVisible({ timeout: 10_000 });

    // Rows should still be present
    const rows = page.locator("[data-testid^='vpn-fw-row-']");
    const count = await rows.count();
    expect(count).toBeGreaterThan(0);
  });
});
