import { test, expect } from "@playwright/test";
import { authenticator } from "otplib";

const ADMIN_USER = "admin";

test.describe.serial("Auth flow", () => {
  let adminPassword: string;
  let newPassword: string;
  let totpSecret: string;

  test.beforeAll(() => {
    adminPassword = process.env.ADMIN_PASSWORD ?? "";
  });

  test("Reject Invalid Credentials", async ({ page }) => {
    await page.goto("/login");
    await page.getByTestId("login-username").fill("wrong");
    await page.getByTestId("login-password").fill("wrong");
    await page.getByTestId("login-submit").click();
    await expect(page).toHaveURL(/\/login/);
    await expect(page.getByTestId("login-error")).toBeVisible();
  });

  test("Login & Enable TOTP", async ({ page }) => {
    await page.goto("/login");
    await page.getByTestId("login-username").fill(ADMIN_USER);
    await page.getByTestId("login-password").fill(adminPassword);
    await page.getByTestId("login-submit").click();
    await expect(page).toHaveURL("/");

    // Navigate to TOTP status page
    await page.goto("/account/totp");
    await expect(page.getByTestId("totp-status-tag")).toBeVisible();
    await page.getByTestId("totp-enable-btn").click();

    // Step 1: confirm current password
    await page.getByTestId("totp-enable-password").fill(adminPassword);
    await page.getByTestId("totp-enable-confirm").click();

    // Step 2: save secret, scroll to backup codes, proceed
    const secretEl = page.getByTestId("totp-enable-secret");
    await expect(secretEl).toBeVisible();
    totpSecret = (await secretEl.textContent()) ?? "";
    expect(totpSecret).toBeTruthy();
    await page.getByTestId("totp-enable-backup").scrollIntoViewIfNeeded();
    await page.getByTestId("totp-enable-next").click();

    // Step 3: generate and submit TOTP code
    const code = authenticator.generate(totpSecret);
    await page.getByTestId("totp-enable-code").fill(code);
    await page.getByTestId("totp-enable-verify").click();

    // Step 4: done — go back and verify status
    await expect(page.getByTestId("totp-enable-done")).toBeVisible();
    await page.getByTestId("totp-enable-goback").click();
    await expect(page.getByTestId("totp-status-tag")).toContainText("Enabled");
  });

  test("Login with TOTP, Disable TOTP, Logout, Login without TOTP", async ({ page }) => {
    await page.goto("/login");
    await page.getByTestId("login-username").fill(ADMIN_USER);
    await page.getByTestId("login-password").fill(adminPassword);
    await page.getByTestId("login-submit").click();

    // Complete TOTP challenge
    await expect(page.getByTestId("login-totp-code")).toBeVisible();
    const loginCode = authenticator.generate(totpSecret);
    await page.getByTestId("login-totp-code").fill(loginCode);
    await page.getByTestId("login-totp-submit").click();
    await expect(page).toHaveURL("/");

    // Navigate to TOTP page and disable
    await page.goto("/account/totp");
    await expect(page.getByTestId("totp-status-tag")).toContainText("Enabled");
    await page.getByTestId("totp-disable-btn").click();

    await page.getByTestId("totp-disable-password").fill(adminPassword);
    await page.getByTestId("totp-disable-confirm").click();

    // Done — go back and verify status
    await expect(page.getByTestId("totp-disable-done")).toBeVisible();
    await page.getByTestId("totp-disable-goback").click();
    await expect(page.getByTestId("totp-status-tag")).toContainText("Disabled");

    // Logout and log back in without TOTP
    await page.getByTestId("header-logout").click();
    await expect(page).toHaveURL(/\/login/);

    await page.getByTestId("login-username").fill(ADMIN_USER);
    await page.getByTestId("login-password").fill(adminPassword);
    await page.getByTestId("login-submit").click();
    await expect(page).toHaveURL("/");
  });

  test("Create 5 Users", async ({ page }) => {
    await page.goto("/login");
    await page.getByTestId("login-username").fill(ADMIN_USER);
    await page.getByTestId("login-password").fill(adminPassword);
    await page.getByTestId("login-submit").click();
    await expect(page).toHaveURL("/");

    await page.goto("/admin/users");
    await expect(page.getByTestId("um-add-user")).toBeVisible();

    for (let i = 1; i <= 5; i++) {
      const username = `e2e-user-${String(i).padStart(2, "0")}`;

      await page.getByTestId("um-add-user").click();
      const modal = page.getByTestId("um-create-modal");
      await expect(modal).toBeVisible();

      // Wait for modal to reset before filling
      const usernameInput = page.getByTestId("um-create-username");
      await expect(usernameInput).toBeVisible();
      await expect(usernameInput).toHaveValue("");
      await usernameInput.fill(username);

      // Generate password and verify all policy checks pass
      await page.getByTestId("um-create-generate").click();
      const passed = page.getByTestId("um-create-checklist").locator(".um__check--pass");
      await expect(passed).toHaveCount(5);

      await modal.locator(".cds--modal-footer .cds--btn--primary").click();

      // Wait for modal to close and row to appear in table
      await expect(modal).not.toBeVisible();
      await expect(page.getByTestId(`um-row-${username}`)).toBeVisible();

      // Dismiss success notification
      const notification = page.getByTestId("um-notification");
      await expect(notification).toBeVisible();
      await notification.locator(".cds--inline-notification__close-button").click();
      await expect(notification).not.toBeVisible();
    }
  });

  test("Change Password for 5 Users", async ({ page }) => {
    await page.goto("/login");
    await page.getByTestId("login-username").fill(ADMIN_USER);
    await page.getByTestId("login-password").fill(adminPassword);
    await page.getByTestId("login-submit").click();
    await expect(page).toHaveURL("/");

    await page.goto("/admin/users");
    await expect(page.getByTestId("um-table")).toBeVisible();

    for (let i = 1; i <= 5; i++) {
      const username = `e2e-user-${String(i).padStart(2, "0")}`;

      await page.getByTestId(`um-overflow-${username}`).click();
      await page.getByTestId(`um-action-password-${username}`).click();

      const modal = page.getByTestId("um-password-modal");
      await expect(modal).toBeVisible();

      // Generate password and verify all policy checks pass
      await page.getByTestId("um-password-generate").click();
      const passed = page.getByTestId("um-password-checklist").locator(".um__check--pass");
      await expect(passed).toHaveCount(5);

      await modal.locator(".cds--modal-footer .cds--btn--primary").click();

      // Wait for modal to close, then dismiss notification
      await expect(modal).not.toBeVisible();
      const notification = page.getByTestId("um-notification");
      await expect(notification).toBeVisible();
      await notification.locator(".cds--inline-notification__close-button").click();
      await expect(notification).not.toBeVisible();
    }
  });

  test("Delete 5 Users", async ({ page }) => {
    await page.goto("/login");
    await page.getByTestId("login-username").fill(ADMIN_USER);
    await page.getByTestId("login-password").fill(adminPassword);
    await page.getByTestId("login-submit").click();
    await expect(page).toHaveURL("/");

    await page.goto("/admin/users");
    await expect(page.getByTestId("um-table")).toBeVisible();

    for (let i = 1; i <= 5; i++) {
      const username = `e2e-user-${String(i).padStart(2, "0")}`;

      await page.getByTestId(`um-overflow-${username}`).click();
      await page.getByTestId(`um-action-delete-${username}`).click();

      // Confirm deletion — verify username shown in danger modal
      const modal = page.getByTestId("um-delete-modal");
      await expect(modal).toBeVisible();
      await expect(page.getByTestId("um-delete-username")).toHaveText(username);

      await modal.locator(".cds--modal-footer .cds--btn--danger").click();

      // Wait for modal to close and row to disappear
      await expect(modal).not.toBeVisible();
      await expect(page.getByTestId(`um-row-${username}`)).not.toBeVisible();

      // Dismiss success notification
      const notification = page.getByTestId("um-notification");
      await expect(notification).toBeVisible();
      await notification.locator(".cds--inline-notification__close-button").click();
      await expect(notification).not.toBeVisible();
    }
  });

  test("Audit Log", async ({ page }) => {
    await page.goto("/login");
    await page.getByTestId("login-username").fill(ADMIN_USER);
    await page.getByTestId("login-password").fill(adminPassword);
    await page.getByTestId("login-submit").click();
    await expect(page).toHaveURL("/");

    await page.goto("/admin/audit");
    const table = page.getByTestId("audit-table");
    await expect(table).toBeVisible();

    // Previous tests should have produced audit entries
    const rows = table.locator("tbody tr");
    await expect(rows.first()).toBeVisible();

    // Open detail modal for the first row
    const firstOverflow = page.locator("[data-testid^='audit-overflow-']").first();
    await firstOverflow.click();
    const firstDetail = page.locator("[data-testid^='audit-show-detail-']").first();
    await firstDetail.click();

    const modal = page.getByTestId("audit-detail-modal");
    await expect(modal).toBeVisible();
    await modal.locator(".cds--modal-footer .cds--btn--primary").click();
    await expect(modal).not.toBeVisible();
  });

  test("Change Password & Re-login", async ({ page }) => {
    await page.goto("/login");
    await page.getByTestId("login-username").fill(ADMIN_USER);
    await page.getByTestId("login-password").fill(adminPassword);
    await page.getByTestId("login-submit").click();
    await expect(page).toHaveURL("/");

    await page.goto("/account/password-change");

    // Step 1: verify current password
    await page.getByTestId("pwchange-current-password").fill(adminPassword);
    await page.getByTestId("pwchange-verify-confirm").click();

    // Step 2: enter new password
    newPassword = `Test@${Date.now().toString().slice(-6)}1aA`;
    await page.getByTestId("pwchange-new-password").fill(newPassword);
    await page.getByTestId("pwchange-change-confirm").click();

    // Step 3: done — wait for auto-logout countdown to redirect
    await expect(page.getByTestId("pwchange-done")).toBeVisible();
    await expect(page).toHaveURL(/\/login/, { timeout: 10000 });

    // Re-login with new password and verify dashboard
    await page.getByTestId("login-username").fill(ADMIN_USER);
    await page.getByTestId("login-password").fill(newPassword);
    await page.getByTestId("login-submit").click();
    await expect(page).toHaveURL("/");
    await expect(page.getByTestId("dashboard-page")).toBeVisible();
  });

  test("Re-login & Restore Password", async ({ page }) => {
    await page.goto("/login");
    await page.getByTestId("login-username").fill(ADMIN_USER);
    await page.getByTestId("login-password").fill(newPassword);
    await page.getByTestId("login-submit").click();
    await expect(page).toHaveURL("/");

    await page.goto("/account/password-change");

    // Step 1: verify current (changed) password
    await page.getByTestId("pwchange-current-password").fill(newPassword);
    await page.getByTestId("pwchange-verify-confirm").click();

    // Step 2: restore original password
    await page.getByTestId("pwchange-new-password").fill(adminPassword);
    await page.getByTestId("pwchange-change-confirm").click();

    // Step 3: done — wait for auto-logout countdown to redirect
    await expect(page.getByTestId("pwchange-done")).toBeVisible();
    await expect(page).toHaveURL(/\/login/, { timeout: 10000 });

    // Re-login with restored password and verify dashboard
    await page.getByTestId("login-username").fill(ADMIN_USER);
    await page.getByTestId("login-password").fill(adminPassword);
    await page.getByTestId("login-submit").click();
    await expect(page).toHaveURL("/");
    await expect(page.getByTestId("dashboard-page")).toBeVisible();
  });
});