import { expect, test } from "@playwright/test";

const login = async (page) => {
  await page.goto("/");
  await page.getByPlaceholder("user").fill("user");
  await page.getByPlaceholder("password").fill("password");
  await page.getByRole("button", { name: /sign in/i }).click();
};

const getColumnByTitle = (page, title: string) =>
  page.locator('[data-testid^="column-"]').filter({
    has: page.locator(`input[aria-label="Column title"][value="${title}"]`),
  });

test("loads the kanban board", async ({ page }) => {
  await login(page);
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
  await expect(page.locator('[data-testid^="column-"]')).toHaveCount(5);
});

test("adds a card to a column", async ({ page }) => {
  await login(page);
  const firstColumn = getColumnByTitle(page, "Backlog");
  await firstColumn.getByRole("button", { name: /^add card$/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill("Playwright card");
  await firstColumn.getByPlaceholder(/details/i).fill("Added via e2e.");
  await firstColumn.getByRole("button", { name: /^add$/i }).click();
  await expect(firstColumn.getByText("Playwright card").first()).toBeVisible();
});

test("moves a card between columns", async ({ page }) => {
  await login(page);
  const card = page.locator("article", { hasText: "Align roadmap themes" }).first();
  const targetColumn = getColumnByTitle(page, "Review");
  await expect(card).toBeVisible();
  const cardBox = await card.boundingBox();
  const columnBox = await targetColumn.boundingBox();
  if (!cardBox || !columnBox) {
    throw new Error("Unable to resolve drag coordinates.");
  }

  await page.mouse.move(
    cardBox.x + cardBox.width / 2,
    cardBox.y + cardBox.height / 2
  );
  await page.mouse.down();
  await page.mouse.move(
    columnBox.x + columnBox.width / 2,
    columnBox.y + 120,
    { steps: 12 }
  );
  await page.mouse.up();
  await expect(targetColumn.getByText("Align roadmap themes")).toBeVisible();
});
