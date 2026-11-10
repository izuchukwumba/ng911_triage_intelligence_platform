import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';

// Design v1.2, section 11.2: keyboard navigation, accessible labels, readable
// contrast, no colour-only priority signals, and the simulation warning on
// every screen. axe checks WCAG 2.0/2.1 A and AA rules on each screen.

const CALLS = [
  'My father is not breathing at 12 Oak Street.',
  'Smoke coming from the garage at 4 Cedar Court, Springfield.',
  'Someone scratched my car last night, nobody is hurt.',
];

test.beforeAll(async ({ request }) => {
  for (const text of CALLS) {
    const response = await request.post('/v1/incidents', { data: { text, synthetic: true } });
    expect(response.status()).toBe(202);
  }
});

async function expectNoViolations(page: Page, screen: string) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();
  const summary = results.violations.map(
    (v) => `${v.id} (${v.impact}): ${v.help} — ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`,
  );
  expect(summary, `accessibility violations on the ${screen} screen`).toEqual([]);
}

function queue(page: Page) {
  return page.getByRole('region', { name: 'Incident queue' });
}

function simulationWarning(page: Page) {
  return page.getByText(/not for live dispatch/i);
}

async function openView(page: Page, name: 'Queue' | 'Replay' | 'Evaluation') {
  await page.getByRole('button', { name, exact: true }).click();
}

async function openCriticalIncident(page: Page) {
  await queue(page).getByRole('button').filter({ hasText: 'P0' }).first().click();
  await expect(page.getByRole('heading', { name: /why this recommendation/i })).toBeVisible();
}

test('queue screen', async ({ page }) => {
  await page.goto('/');
  await expect(simulationWarning(page)).toBeVisible();
  await expect(queue(page).getByRole('button').first()).toBeVisible();
  await expectNoViolations(page, 'queue');
});

test('incident detail screen', async ({ page }) => {
  await page.goto('/');
  await openCriticalIncident(page);
  await expect(simulationWarning(page)).toBeVisible();
  await expectNoViolations(page, 'incident detail');
});

test('replay screen', async ({ page }) => {
  await page.goto('/');
  await openView(page, 'Replay');
  await page.getByRole('button', { name: /replay all incidents/i }).click();
  await expect(page.getByText(/reproducible/).first()).toBeVisible();
  await expect(simulationWarning(page)).toBeVisible();
  await expectNoViolations(page, 'replay');
});

test('evaluation screen', async ({ page }) => {
  await page.goto('/');
  await openView(page, 'Evaluation');
  await expect(page.getByText('Version pins')).toBeVisible();
  await expect(simulationWarning(page)).toBeVisible();
  await expectNoViolations(page, 'evaluation');
});

test('priorities are stated in text, not only by colour', async ({ page }) => {
  await page.goto('/');
  await expect(queue(page).getByText(/\bP[0-4]\b/).first()).toBeVisible();
});

test('triage works from the keyboard alone', async ({ page }) => {
  await page.goto('/');
  // Views can be switched without a mouse.
  await page.getByRole('button', { name: 'Evaluation', exact: true }).focus();
  await page.keyboard.press('Enter');
  await expect(page.getByText('Version pins')).toBeVisible();
  await page.getByRole('button', { name: 'Queue', exact: true }).focus();
  await page.keyboard.press('Enter');

  // A message can be typed and submitted, and the new incident opens.
  await page.getByLabel('Synthetic transcript', { exact: true }).focus();
  await page.keyboard.type('A man is waving a knife outside 22 Oak Avenue.');
  await page.keyboard.press('Tab');
  await expect(page.getByRole('button', { name: 'Submit' })).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('heading', { name: /why this recommendation/i })).toBeVisible();

  // A queued incident can be opened with the keyboard.
  await page.goto('/');
  await queue(page).getByRole('button').filter({ hasText: 'P0' }).first().focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('heading', { name: /why this recommendation/i })).toBeVisible();
});
