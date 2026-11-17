import { expect, test, type Page } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { performance } from 'node:perf_hooks';

async function signIn(page: Page, role: 'coordinator' | 'reviewer') {
  await page.getByLabel('Demo access token').fill(process.env['E2E_' + role.toUpperCase() + '_TOKEN']!);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('navigation')).toBeVisible();
}

const preconception = 'Preconception follow up · demo-amira';

test('completes the patient journey through all five screens', async ({ page }, testInfo) => {
  const timings: Record<string, number> = {};
  const started = performance.now();
  await page.goto('/');
  await signIn(page, 'coordinator');
  await expect(page.getByRole('heading', { name: 'Population intelligence' })).toBeVisible();
  timings.dashboardLoadAndSignInMs = Math.round(performance.now() - started);
  await page.getByRole('button', { name: 'Load demo patient' }).click();
  await expect(page.getByText('Amira Haddad')).toBeVisible();
  const navigating = performance.now();
  await page.getByRole('link', { name: 'Open workspace' }).click();
  await expect(page.getByRole('heading', { name: 'Amira Haddad' })).toBeVisible();
  timings.workspaceNavigationMs = Math.round(performance.now() - navigating);
  await expect(page.getByText('Patient/demo-amira')).toBeVisible();
  await page.getByRole('link', { name: /Preconception follow up/ }).click();
  await expect(page.getByText('Observation/demo-initial-flag', { exact: true }).first()).toBeVisible();
  await page.getByRole('link', { name: 'Women’s health workspace' }).click();
  await page.getByRole('button', { name: 'Register pregnancy' }).click();
  await expect(page.getByText('Pregnancy coordination').first()).toBeVisible();
  await page.getByRole('link', { name: /Preconception follow up/ }).click();
  await expect(page.getByRole('heading', { name: 'Clinical obligation passport' })).toBeVisible();
  await expect(page.getByText('must close before')).toBeVisible();
  await page.getByRole('button', { name: 'Run care-resolution agent' }).click();
  await page.getByRole('link', { name: 'Care-resolution center' }).click();
  await expect(page.getByText('Missing closure evidence')).toBeVisible();

  await page.getByRole('button', { name: 'Sign out' }).click();
  await signIn(page, 'reviewer');
  await expect(page.getByRole('button', { name: 'Request additional evidence' })).toBeVisible();
  await page.getByRole('button', { name: 'Approve', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Reviewer decision recorded');
  await page.getByRole('button', { name: 'Sign out' }).click();
  await signIn(page, 'coordinator');
  await page.getByRole('link', { name: 'Obligation passport', exact: true }).click();
  await page.getByRole('combobox', { name: 'Obligation' }).selectOption({ label: preconception });
  await page.getByRole('button', { name: 'Verify closure' }).click();
  await expect(page.getByRole('alert')).toContainText('completion evidence is missing');

  await page.getByRole('link', { name: 'Evidence & audit', exact: true }).click();
  await page.getByRole('combobox', { name: 'Obligation' }).selectOption({ label: preconception });
  await page.getByRole('button', { name: 'Add verified evidence' }).click();
  await expect(page.getByRole('status')).toContainText('Verified fixture submitted');
  await page.getByRole('link', { name: 'Obligation passport', exact: true }).click();
  await page.getByRole('combobox', { name: 'Obligation' }).selectOption({ label: preconception });
  await page.getByRole('button', { name: 'Verify closure' }).click();
  await expect(page.getByRole('alert')).toContainText('Reviewer approval');
  await page.getByRole('button', { name: 'Run care-resolution agent' }).click();
  await page.getByRole('link', { name: 'Care-resolution center' }).click();
  await expect(page.getByText('Evidence available')).toBeVisible();
  await page.getByRole('button', { name: 'Sign out' }).click();
  await signIn(page, 'reviewer');
  await page.getByRole('button', { name: 'Approve', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Reviewer decision recorded');
  await page.getByRole('button', { name: 'Sign out' }).click();
  await signIn(page, 'coordinator');
  await page.getByRole('link', { name: 'Obligation passport', exact: true }).click();
  await page.getByRole('combobox', { name: 'Obligation' }).selectOption({ label: preconception });
  await page.getByRole('button', { name: 'Verify closure' }).click();
  await expect(page.getByRole('status')).toContainText('Closure verified');

  await page.getByRole('link', { name: 'Evidence & audit', exact: true }).click();
  const verification = page.getByRole('heading', { name: 'Verification results' }).locator('../..');
  await expect(verification.getByText('Closure blocked')).toHaveCount(2);
  await expect(verification.getByText('Closure verified')).toBeVisible();
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download FHIR bundle' }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe('demo-amira-r4.json');
  const path = testInfo.outputPath('demo-amira-r4.json');
  await download.saveAs(path);
  const bundle = JSON.parse(await readFile(path, 'utf8'));
  expect(bundle.resourceType).toBe('Bundle');
  expect(bundle.entry.filter(({ resource }: { resource: { resourceType: string; status?: string } }) =>
    resource.resourceType === 'Task' && resource.status === 'completed')).toHaveLength(1);
  await testInfo.attach('FHIR R4 export', { path, contentType: 'application/fhir+json' });
  await testInfo.attach('UI timings', { body: JSON.stringify(timings), contentType: 'application/json' });
  console.log('UI timings', JSON.stringify(timings));
  await page.reload();
  await expect(verification.getByText('Closure verified')).toBeVisible();
  await page.getByRole('link', { name: 'Population dashboard' }).click();
  await expect(page.getByRole('link', { name: /1 Verified closures/ })).toBeVisible();
  const otherPatient = {
    resourceType: 'Patient', id: 'demo-other', name: [{ given: ['Noor'], family: 'Demo' }],
    gender: 'female', birthDate: '1993-01-25', meta: { tag: [
      { system: 'https://reprobridge.example/fhir/CodeSystem/demo', code: 'synthetic' },
    ] },
  };
  const imported = await page.request.post('/api/fhir/import', {
    headers: { Authorization: 'Bearer ' + process.env.E2E_COORDINATOR_TOKEN },
    data: { resources: [otherPatient] },
  });
  expect(imported.ok()).toBeTruthy();
  await page.reload();
  await expect(page.getByRole('link', { name: /2 Synthetic patients/ })).toBeVisible();
  await page.getByRole('row', { name: /Noor Demo/ }).getByRole('link', { name: 'Open workspace' }).click();
  await expect(page.getByRole('heading', { name: 'Noor Demo' })).toBeVisible();
  await expect(page.getByText('Observation/demo-initial-flag', { exact: true })).toHaveCount(0);
  await page.getByRole('combobox', { name: 'Patient' }).selectOption('demo-amira');
  await expect(page.getByRole('heading', { name: 'Amira Haddad' })).toBeVisible();
});
