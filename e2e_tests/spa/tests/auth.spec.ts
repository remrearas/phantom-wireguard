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

  test("reject invalid credentials", async ({ page }) => {
    await page.goto("/login");
    await page.fill("#username", "wrong");
    await page.fill("#password", "wrong");
    await page.getByRole("button", { name: /sign in/i }).click();

    await expect(page.locator(".login-page__notification")).toBeVisible();
  });

  test("login and enable TOTP", async ({ page }) => {
    await page.goto("/login");
    await page.fill("#username", ADMIN_USER);
    await page.fill("#password", adminPassword);
    await page.getByRole("button", { name: /sign in/i }).click();
    await page.waitForURL("/");

    await page.getByRole("button", { name: "User Operations" }).click();
    const totpLink = page.getByRole("link", { name: "TOTP" });
    await expect(totpLink).toBeVisible();
    await totpLink.click();

    await expect(page.getByText("Disabled")).toBeVisible();
    await page.getByRole("button", { name: "Enable TOTP" }).click();

    // Step 1: password
    await expect(page.locator("#totp-enable-password")).toBeVisible();
    await page.fill("#totp-enable-password", adminPassword);
    await page.getByRole("button", { name: "Confirm" }).click();

    // Step 2: secret
    const secretEl = page.locator(".totp-wizard__secret-value");
    await expect(secretEl).toBeVisible();
    totpSecret = (await secretEl.textContent()) ?? "";
    expect(totpSecret).toBeTruthy();
    await page.locator(".totp-wizard__backup").scrollIntoViewIfNeeded();
    await page.getByRole("button", { name: "Confirm" }).click();

    // Step 3: verify
    await expect(page.locator("#totp-enable-code")).toBeVisible();
    const code = authenticator.generate(totpSecret);
    await page.fill("#totp-enable-code", code);
    await page.getByRole("button", { name: "Verify" }).click();

    // Step 4: done
    await expect(page.locator(".totp-wizard__done-icon")).toBeVisible();
    await page.getByRole("button", { name: "Go Back" }).click();
    await expect(page.getByText("Enabled")).toBeVisible();
  });

  test("login with TOTP, disable TOTP, logout, login without TOTP", async ({ page }) => {
    await page.goto("/login");
    await page.fill("#username", ADMIN_USER);
    await page.fill("#password", adminPassword);
    await page.getByRole("button", { name: /sign in/i }).click();

    await expect(page.locator("#totp-code")).toBeVisible();
    const loginCode = authenticator.generate(totpSecret);
    await page.fill("#totp-code", loginCode);
    await page.getByRole("button", { name: "Verify" }).click();
    await page.waitForURL("/");
    await expect(page.getByRole("heading", { name: "Phantom-WG Dashboard" })).toBeVisible();

    // Navigate to TOTP, disable
    await page.getByRole("button", { name: "User Operations" }).click();
    const totpLink = page.getByRole("link", { name: "TOTP" });
    await expect(totpLink).toBeVisible();
    await totpLink.click();

    await expect(page.getByText("Enabled")).toBeVisible();
    await page.getByRole("button", { name: "Disable TOTP" }).click();

    await expect(page.locator("#totp-disable-password")).toBeVisible();
    await page.fill("#totp-disable-password", adminPassword);
    await page.getByRole("button", { name: "Confirm" }).click();

    await expect(page.locator(".totp-wizard__done-icon")).toBeVisible();
    await page.getByRole("button", { name: "Go Back" }).click();
    await expect(page.getByText("Disabled")).toBeVisible();

    // Logout
    await page.getByRole("button", { name: "Logout" }).click();
    await page.waitForURL("/login");

    // Login without TOTP
    await page.fill("#username", ADMIN_USER);
    await page.fill("#password", adminPassword);
    await page.getByRole("button", { name: /sign in/i }).click();
    await page.waitForURL("/");
    await expect(page.getByRole("heading", { name: "Phantom-WG Dashboard" })).toBeVisible();
  });

  test("change password and relogin", async ({ page }) => {
    await page.goto("/login");
    await page.fill("#username", ADMIN_USER);
    await page.fill("#password", adminPassword);
    await page.getByRole("button", { name: /sign in/i }).click();
    await page.waitForURL("/");

    // Navigate to Change Password
    await page.getByRole("button", { name: "User Operations" }).click();
    const pwLink = page.getByRole("link", { name: "Change Password" });
    await expect(pwLink).toBeVisible();
    await pwLink.click();

    // Step 1: verify current password
    await expect(page.locator("#current-password")).toBeVisible();
    await page.fill("#current-password", adminPassword);
    await page.getByRole("button", { name: "Confirm" }).click();

    // Step 2: new password
    await expect(page.locator("#new-password")).toBeVisible();
    newPassword = `Test@${Date.now().toString().slice(-6)}1aA`;
    await page.fill("#new-password", newPassword);
    await page.getByRole("button", { name: "Confirm" }).click();

    // Step 3: done — wait for auto-logout countdown
    await expect(page.locator(".totp-wizard__done-icon")).toBeVisible();
    await page.waitForURL("/login", { timeout: 10000 });

    // Relogin with new password
    await expect(page.locator("#username")).toBeVisible();
    await page.fill("#username", ADMIN_USER);
    await page.fill("#password", newPassword);
    await page.getByRole("button", { name: /sign in/i }).click();
    await page.waitForURL("/");
    await expect(page.getByRole("heading", { name: "Phantom-WG Dashboard" })).toBeVisible();

    // Dashboard confirmed after password change
    await expect(page).toHaveURL("/");
  });
});