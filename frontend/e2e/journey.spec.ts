import { expect, test, type Page } from '@playwright/test';

async function signIn(page: Page, role: 'coordinator' | 'reviewer') {
  await page.getByLabel('Demo access token').fill(process.env['E2E_' + role.toUpperCase() + '_TOKEN']!);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('navigation')).toBeVisible();
}

test('completes the patient journey through all five screens', async ({ page }) => {
  await page.goto('/');
  await signIn(page, 'coordinator');
  await page.getByRole('button', { name: 'Load demo patient' }).click();
  await expect(page.getByText('Amira Haddad')).toBeVisible();
  await page.getByRole('link', { name: 'Open workspace' }).click();
  await page.getByRole('button', { name: 'Register pregnancy' }).click();
  await expect(page.getByText('Pregnancy coordination').first()).toBeVisible();
  await page.getByRole('link', { name: /Preconception follow up/ }).click();
  await expect(page.getByRole('heading', { name: 'Clinical obligation passport' })).toBeVisible();
  await expect(page.getByText('must close before')).toBeVisible();
  await page.getByRole('button', { name: 'Verify closure' }).click();
  await expect(page.getByRole('alert')).toContainText('completion evidence is missing');
  await page.getByRole('button', { name: 'Run care-resolution agent' }).click();
  await page.getByRole('link', { name: 'Care-resolution center' }).click();
  await expect(page.getByText('Missing closure evidence')).toBeVisible();
  await page.getByRole('link', { name: 'Evidence & audit', exact: true }).click();
  await page.getByRole('combobox', { name: 'Obligation' }).selectOption({ label: 'Preconception follow up · demo-amira' });
  await page.getByRole('button', { name: 'Add verified evidence' }).click();
  await expect(page.getByRole('status')).toContainText('Verified fixture submitted');
  await page.getByRole('button', { name: 'Sign out' }).click();
  await signIn(page, 'reviewer');
  await page.getByRole('link', { name: 'Care-resolution center' }).click();
  await expect(page.getByRole('button', { name: 'Request additional evidence' })).toBeVisible();
  await page.getByRole('button', { name: 'Approve', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Reviewer decision recorded');
  await page.getByRole('button', { name: 'Sign out' }).click();
  await signIn(page, 'coordinator');
  await page.getByRole('link', { name: 'Obligation passport', exact: true }).click();
  await page.getByRole('combobox', { name: 'Obligation' }).selectOption({ label: 'Preconception follow up · demo-amira' });
  await page.getByRole('button', { name: 'Verify closure' }).click();
  await expect(page.getByRole('status')).toContainText('Closure verified');
  await page.getByRole('link', { name: 'Evidence & audit', exact: true }).click();
  const verification = page.getByRole('heading', { name: 'Verification results' }).locator('../..');
  await expect(verification.getByText('Closure blocked')).toBeVisible();
  await expect(verification.getByText('Closure verified')).toBeVisible();
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download FHIR bundle' }).click();
  expect((await downloadPromise).suggestedFilename()).toBe('demo-amira-r4.json');
  await page.reload();
  await expect(verification.getByText('Closure verified')).toBeVisible();
});
