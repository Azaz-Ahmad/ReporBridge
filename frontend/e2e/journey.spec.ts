import { expect, test, type Locator, type Page } from '@playwright/test';
import { mkdir, readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { performance } from 'node:perf_hooks';

async function signIn(page: Page, role: 'coordinator' | 'reviewer') {
  await page.getByLabel('Demo access token').fill(process.env['E2E_' + role.toUpperCase() + '_TOKEN']!);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('navigation')).toBeVisible();
}

const preconception = 'Preconception metabolic assessment review · demo-amira';

test('completes the patient journey through all five screens', async ({ page }, testInfo) => {
  test.setTimeout(90_000);
  const timings: Record<string, number> = {};
  await page.setViewportSize({ width: 1440, height: 1000 });
  const captureDir = process.env.REPROBRIDGE_CAPTURE_DIR;
  async function capture(name: string, region?: Locator) {
    if (!captureDir) return;
    await mkdir(captureDir, { recursive: true });
    await page.evaluate(() => document.fonts.ready.then(() => undefined));
    const options = { path: join(captureDir, name + '.png'), animations: 'disabled' as const };
    if (region) await region.screenshot(options);
    else {
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.screenshot({ ...options, fullPage: true });
    }
  }
  const started = performance.now();
  await page.goto('/');
  await signIn(page, 'coordinator');
  await expect(page.getByRole('heading', { name: 'Population intelligence' })).toBeVisible();
  timings.dashboardLoadAndSignInMs = Math.round(performance.now() - started);
  await page.getByRole('button', { name: 'Load demo patient' }).click();
  await expect(page.getByRole('link', { name: 'Open Amira’s journey' })).toBeVisible();
  await expect(page.getByRole('link', { name: /1 Open obligations/ })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Prevention Decision Queue' })).toBeVisible();
  await expect(page.locator('.decision-counts button').filter({ hasText: 'Awaiting evidence' }).locator('strong')).toHaveText('1');
  await expect(page.getByRole('link', { name: /0 Blocked or escalated/ })).toBeVisible();
  if (captureDir) {
    await page.getByText('Six innovations', { exact: true }).click();
    await page.getByText('Technical evaluation', { exact: true }).click();
    await capture('01-population');
  }
  const navigating = performance.now();
  await page.getByRole('link', { name: 'Open workspace' }).click();
  await expect(page.getByRole('heading', { name: 'Amira Haddad' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Decision Timeline' })).toBeVisible();
  timings.workspaceNavigationMs = Math.round(performance.now() - navigating);
  await expect(page.getByText('Patient/demo-amira')).toBeVisible();
  await page.getByRole('link', { name: /Preconception metabolic assessment review/ }).first().click();
  await expect(page.getByText('Required completion evidence is missing.')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Prevention Decision', exact: true })).toBeVisible();
  await expect(page.getByText('Timing not established.', { exact: true })).toBeVisible();
  if (await page.locator('#provenance').getAttribute('open') === null)
    await page.getByText('Source evidence and provenance', { exact: true }).click();
  await expect(page.locator('#provenance')).toContainText('Observation/demo-initial-flag');
  await expect(page.locator('#provenance')).toContainText('preconception-follow-up@1.0.0');
  await page.getByRole('link', { name: 'Women’s health workspace' }).click();
  await page.getByRole('button', { name: 'Register pregnancy' }).click();
  await expect(page.getByText('Pregnancy handoff review').first()).toBeVisible();
  const stages = page.getByRole('list', { name: 'Reproductive life stages' });
  await expect(stages.locator('[aria-current="step"]')).toContainText('Pregnancy');
  await expect(stages).toContainText('Planned');
  await expect(page.getByText('must close before')).toBeVisible();
  await expect(page.getByText(/Pregnancy is registered and this assessment is still open/)).toBeVisible();
  await expect(page.getByText(/This prerequisite applies to closing the linked review/)).toBeVisible();
  await capture('02-patient-workspace');
  await capture('07-cross-pathway-dependencies', page.locator('#dependencies'));
  await page.getByRole('link', { name: /Pregnancy handoff review.*Observation\/demo-amira-pregnancy/ }).click();
  await expect(page.locator('#provenance')).toHaveAttribute('open', '');
  await expect(page.locator('#provenance')).toContainText('Observation/demo-amira-pregnancy');
  await page.getByRole('link', { name: 'Women’s health workspace' }).click();
  await page.getByRole('link', { name: /Preconception metabolic assessment review/ }).first().click();
  await expect(page.getByRole('heading', { name: 'Clinical obligation passport' })).toBeVisible();
  await expect(page.getByText('must close before')).toBeVisible();
  await expect(page.getByText('Illustrative — Not Clinically Approved')).toBeVisible();
  if (await page.locator('#provenance').getAttribute('open') === null)
    await page.getByText('Source evidence and provenance', { exact: true }).click();
  await expect(page.getByText('Recorded finding')).toBeVisible();
  await capture('03-obligation-passport');
  await page.getByRole('link', { name: 'Open review queue' }).click();
  await expect(page.getByRole('heading', { name: 'Clinical Evidence Investigation' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Decision Readiness Investigation' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Run Decision Readiness Investigation' })).toBeDisabled();
  await expect(page.locator('section').filter({ has: page.getByRole('heading', { name: 'Clinical Evidence Investigation', exact: true }) })
    .getByText('AI-generated evidence summary — requires clinical review.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Run Investigation', exact: true })).toBeDisabled();
  await expect(page.getByText(/The Clinical Evidence Agent is unavailable/)).toBeVisible();
  await expect(page.getByText('Not started', { exact: true })).toBeVisible();
  await expect(page.getByRole('list', { name: 'Configured LangGraph steps' }).getByRole('listitem')).toHaveCount(4);
  await expect(page.getByRole('list', { name: 'Recorded LangGraph nodes' })).toHaveCount(0);
  await expect(page.getByText(/Amira Haddad · Preconception metabolic assessment review/)).toBeVisible();
  await expect(page.getByRole('link', { name: 'Open selected passport' })).toBeVisible();
  await capture('04-resolution-before');
  await page.getByRole('button', { name: 'Run care-resolution agent' }).click();
  await expect(page.getByText('Waiting for review', { exact: true })).toBeVisible();
  await expect(page.getByText('Missing closure evidence')).toBeVisible();
  const trace = page.getByRole('list', { name: 'Recorded LangGraph nodes' });
  await expect(trace.getByRole('listitem')).toHaveText(['Retrieve evidence', 'Reconcile evidence', 'Prepare proposal', 'Route to human review']);

  await page.getByRole('button', { name: 'Sign out' }).click();
  await signIn(page, 'reviewer');
  await expect(page.getByRole('button', { name: 'Request additional evidence' })).toBeVisible();
  await capture('05-resolution-after');
  await page.getByRole('button', { name: 'Approve', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Reviewer decision recorded');
  await page.getByRole('button', { name: 'Sign out' }).click();
  await signIn(page, 'coordinator');
  await page.getByRole('link', { name: 'Obligation passport', exact: true }).click();
  await page.getByRole('combobox', { name: 'Passport obligation', exact: true }).selectOption({ label: preconception });
  await page.getByRole('button', { name: 'Verify closure' }).click();
  await expect(page.getByRole('alert')).toContainText('completion evidence is missing');

  await page.getByRole('link', { name: 'Evidence & audit', exact: true }).click();
  await page.getByRole('combobox', { name: 'Completion evidence obligation' }).selectOption({ label: preconception });
  await page.getByRole('button', { name: 'Add verified evidence' }).click();
  await expect(page.getByRole('status')).toContainText('Verified fixture submitted');
  await page.getByRole('link', { name: 'Obligation passport', exact: true }).click();
  await page.getByRole('combobox', { name: 'Passport obligation', exact: true }).selectOption({ label: preconception });
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
  await page.getByRole('combobox', { name: 'Passport obligation', exact: true }).selectOption({ label: preconception });
  await page.getByRole('button', { name: 'Verify closure' }).click();
  await expect(page.getByRole('status')).toContainText('Closure verified');

  await page.getByRole('link', { name: 'Evidence & audit', exact: true }).click();
  const verification = page.getByRole('heading', { name: 'Verification results' }).locator('../..');
  await expect(verification.getByText('Closure blocked')).toHaveCount(2);
  await expect(verification.getByText('Closure verified')).toBeVisible();
  await expect(page.getByText('Care obligation verified as resolved')).toBeVisible();
  await expect(page.getByText(/Qualifying evidence, required approval and any prerequisite/)).toBeVisible();
  await capture('06-evidence-audit');
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

  await page.getByText('Clinical evidence explorer', { exact: true }).click();
  await page.getByRole('button', { name: 'Load Amira’s synthetic dataset' }).click();
  await expect(page.getByText('Synthetic dataset available.')).toBeVisible();
  await page.getByLabel('Search evidence').fill('reconciliation');
  await page.getByRole('button', { name: 'Search', exact: true }).click();
  const clinicalNote = page.locator('.clinical-results li')
    .filter({ has: page.getByText('DocumentReference/demo-m08-note', { exact: true }) });
  await clinicalNote.locator('summary').click();
  await expect(clinicalNote.getByText('Source excerpt · untrusted clinical text')).toBeVisible();
  await expect(clinicalNote.getByText('Clinician reconciliation remains outstanding.', { exact: true })).toBeVisible();

  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
    'Expanded clinical explorer fits at 390 px').toBe(true);
  await expect(stages.locator('[aria-current="step"]')).toContainText('Pregnancy');
  for (const route of ['/workspace?patient=demo-amira', '/passport', '/resolution', '/audit', '/']) {
    await page.goto(route);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), route + ' fits at 390 px').toBe(true);
    if (route.startsWith('/workspace')) await capture('08-mobile-workspace');
  }

  await page.getByText('Reset Amira demo', { exact: true }).click();
  await page.getByRole('button', { name: 'Confirm reset' }).click();
  await expect(page.getByRole('status')).toContainText('Amira is ready at preconception');
  await expect(page.getByRole('link', { name: /2 Synthetic patients/ })).toBeVisible();
  await expect(page.getByRole('link', { name: /1 Open obligations/ })).toBeVisible();
  await expect(page.getByRole('link', { name: /0 Verified closures/ })).toBeVisible();
  await expect(page.getByRole('link', { name: /0 Active transitions/ })).toBeVisible();
  await page.getByRole('link', { name: 'Open Amira’s journey' }).click();
  await expect(stages.locator('[aria-current="step"]')).toContainText('Preconception');
  await page.getByRole('link', { name: 'Evidence & audit', exact: true }).click();
  await page.getByText('Archived Amira demo runs', { exact: true }).click();
  await expect(page.getByText(/\d+ audit events · Coordinator/)).toBeVisible();

  await page.goto('/passport');
  await page.getByRole('button', { name: 'Sign out' }).click();
  await signIn(page, 'reviewer');
  await page.getByLabel('Clinical decision rationale').fill('Synthetic reviewer requests a reconciliation note.');
  await page.getByRole('button', { name: 'Begin clinician review' }).click();
  await page.getByLabel('Outstanding follow-up actions, one per line').fill('Obtain a synthetic clinician reconciliation note.');
  await page.getByRole('checkbox', { name: 'I reviewed the current evidence snapshot and take responsibility for this decision.' }).check();
  await page.getByRole('button', { name: 'Record clinical decision', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Clinical decision recorded' })).toBeVisible();
  const decisionSnapshot = await page.request.get('/api/snapshot', { headers: { Authorization: 'Bearer ' + process.env.E2E_COORDINATOR_TOKEN } });
  const decisionClinical = await decisionSnapshot.json();
  expect(decisionClinical.clinical_approvals).toHaveLength(0);
  expect(decisionClinical.closure_evidence).toHaveLength(0);
  expect(decisionClinical.clinical_obligations[0].status).toBe('open');
  await page.getByRole('button', { name: 'Sign out' }).click();
  await signIn(page, 'coordinator');
  await page.getByRole('button', { name: 'Initiate follow-up 1' }).click();
  await page.goto('/audit');
  const decisionHistory = page.locator('section').filter({ has: page.getByRole('heading', { name: 'Decision History' }) });
  await expect(decisionHistory.getByText('Decision recorded', { exact: true })).toBeVisible();
  await expect(decisionHistory.getByText('Follow up initiated', { exact: true })).toBeVisible();
  await page.goto('/');
  await page.getByRole('button', { name: 'Load illustrative timing scenario' }).click();
  await expect(page.locator('.decision-counts button').filter({ hasText: 'Due soon' }).locator('strong')).toHaveText('1');
  await expect(page.locator('.decision-counts button').filter({ hasText: 'Overdue' }).locator('strong')).toHaveText('1');
});
