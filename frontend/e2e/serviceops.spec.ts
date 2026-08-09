import { expect, test, type Page } from "@playwright/test";

const operator = {
  username: process.env.SERVICEOPS_OPERATOR_USERNAME ?? "operator",
  password: process.env.SERVICEOPS_OPERATOR_PASSWORD ?? "operator_dev_2026",
};
const viewer = {
  username: process.env.SERVICEOPS_VIEWER_USERNAME ?? "viewer",
  password: process.env.SERVICEOPS_VIEWER_PASSWORD ?? "viewer_dev_2026",
};

async function signIn(page: Page, credentials: { username: string; password: string }) {
  await page.goto("/");
  await page.getByLabel("Username").fill(credentials.username);
  await page.getByLabel("Password").fill(credentials.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Turn incoming issues into clear priorities." })).toBeVisible();
}

test.describe.serial("Kubernetes browser acceptance", () => {
  test("rejects invalid credentials without exposing the workspace", async ({ page }) => {
    await page.goto("/");
    await page.getByLabel("Username").fill("operator");
    await page.getByLabel("Password").fill("definitely-not-the-password");
    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(page.getByRole("alert")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Sign in to ServiceOps" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Create a support ticket" })).toHaveCount(0);
  });

  test("enforces viewer read-only access and renders cited guidance", async ({ page }) => {
    await signIn(page, viewer);

    await expect(page.getByLabel("Read-only access")).toContainText("Viewer access");
    await expect(page.getByRole("heading", { name: "Create a support ticket" })).toHaveCount(0);

    await page
      .getByLabel("What do you need help with?")
      .fill("What should I capture for repeated HTTP 500 API errors?");
    await page.getByRole("button", { name: "Find grounded answer" }).click();
    await expect(page.getByRole("heading", { name: "Source-backed answer" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Sources" })).toBeVisible();
    await expect(page.locator(".knowledge-sources li")).toHaveCount(2);

    const firstTicket = page.locator(".ticket-link").first();
    await expect(firstTicket).toBeVisible();
    await firstTicket.click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toContainText("Viewer access is read-only");
    await expect(page.getByLabel("Update status")).toHaveCount(0);
    await dialog.getByRole("button", { name: "Close ticket details" }).click();
    await page.getByRole("button", { name: "Sign out" }).click();
    await expect(page.getByRole("heading", { name: "Sign in to ServiceOps" })).toBeVisible();
  });

  test("creates, classifies, and resolves a ticket as operator", async ({ page }) => {
    await signIn(page, operator);
    const title = `Browser outage ${Date.now()}`;

    await page.getByLabel("Title").fill(title);
    await page
      .getByLabel("Description")
      .fill("Production API requests return HTTP 500 errors for multiple customers.");
    await page.getByLabel("Reported priority").selectOption("HIGH");
    await page.getByRole("button", { name: "Create ticket" }).click();

    await expect(page.getByText("Ticket created. Prediction is now in progress.")).toBeVisible();
    const dialog = page.getByRole("dialog");
    await expect(dialog.getByRole("heading", { name: title })).toBeVisible();
    const predictionFields = dialog.locator(".detail-grid > div");
    await expect(predictionFields.filter({ hasText: "ML category" })).toContainText("Technical", {
      timeout: 60_000,
    });
    await expect(predictionFields.filter({ hasText: "ML priority" })).toContainText("High");

    await dialog.getByLabel("Update status").selectOption("RESOLVED");
    await expect(dialog.getByRole("status")).toHaveText("Status updated to Resolved.");
    await expect(predictionFields.filter({ hasText: "Status" })).toContainText("Resolved");
    await dialog.getByRole("button", { name: "Close ticket details" }).click();
    await expect(page.getByRole("row", { name: new RegExp(title) })).toContainText("Resolved");
  });
});
