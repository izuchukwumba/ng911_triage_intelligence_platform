import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

// End to end through the real dashboard and API (design v1.2, section 14.1):
// ingest -> assessment and evidence -> human review -> audit -> replay -> report.

test('an operator triages, overrides with a reason, and the decision is replayable', async ({ page }) => {
  await page.goto('/');

  // Ingest a synthetic call; the new incident opens with its machine assessment.
  await page.getByLabel('Synthetic transcript', { exact: true })
    .fill('There is smoke on the second floor at 9 Birch Lane and people are trapped inside.');
  await page.getByRole('button', { name: 'Submit' }).click();
  await expect(page.getByRole('heading', { name: /why this recommendation/i })).toBeVisible();
  const detail = page.getByRole('article', { name: 'Incident detail' });
  await expect(detail.getByText('machine suggestion')).toBeVisible();
  await expect(detail.getByText('P0').first()).toBeVisible();
  // The evidence is quoted from the transcript.
  await expect(detail.getByRole('region', { name: 'Transcript' })).toContainText('people are trapped');

  // Override with a reason; the human decision is shown as such.
  await detail.getByRole('tab', { name: /^Review/ }).click();
  const review = page.getByRole('form', { name: 'Human review' });
  await review.getByLabel('Override priority').check();
  await review.getByLabel('New priority').selectOption('P1');
  await review.getByLabel(/^Reason/).fill('Crews already on scene (synthetic test).');
  await review.getByLabel(/^Reviewer id/).fill('operator_e2e');
  await review.getByRole('button', { name: 'Record review' }).click();
  await expect(detail.getByText('human override')).toBeVisible();
  await expect(detail.getByText('Crews already on scene (synthetic test).')).toBeVisible();
  await expect(detail.getByText(/→ P1/)).toBeVisible();

  // The review is in the audit trail, attributed to the reviewer.
  await detail.getByRole('tab', { name: /audit/i }).click();
  await expect(detail.getByRole('region', { name: 'Audit trail' })).toContainText('operator_e2e');

  // Still accessible with reviews and history on screen.
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze();
  expect(results.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`)).toEqual([]);

  // Replay reproduces every stored assessment exactly; nothing is modified.
  await page.getByRole('button', { name: 'Replay', exact: true }).click();
  await page.getByRole('button', { name: /replay all incidents/i }).click();
  await expect(page.getByText(/reproducible/).first()).toBeVisible();
  await expect(page.getByText(/NOT reproducible/)).toHaveCount(0);

  // And the evaluation report is one click away.
  await page.getByRole('button', { name: 'Evaluation', exact: true }).click();
  await expect(page.getByText('Version pins')).toBeVisible();
});
