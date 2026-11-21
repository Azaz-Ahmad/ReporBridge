import { expect, test, type Locator, type Page } from '@playwright/test';
import { mkdir, readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { performance } from 'node:perf_hooks';

async function signIn(page: Page, role: 'coordinator' | 'reviewer') {
  await page.getByLabel('Demo access token').fill(process.env['E2E_' + role.toUpperCase() + '_TOKEN']!);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('navigation')).toBeVisible();
}

const preconception = 'Preconception metabolic assessment review · Amira Haddad';

test('completes the patient journey through all five screens', async ({ page, browser }, testInfo) => {
  test.setTimeout(210_000);
  const timings: Record<string, number> = {};
  await page.setViewportSize({ width: 1440, height: 1000 });
  const captureDir = process.env.REPROBRIDGE_NO_MEDIA === "true" ? undefined : process.env.REPROBRIDGE_CAPTURE_DIR;
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
  await expect(page.getByRole('heading', { name: 'Ajyra AI - ReproBridge', exact: true })).toBeVisible();
  timings.dashboardLoadAndSignInMs = Math.round(performance.now() - started);
  if (!(await page.locator('.admin-drawer').evaluate(el => (el as HTMLDetailsElement).open))) await page.getByText('Admin', { exact: true }).click();
  await page.getByRole('button', { name: 'Load demo patient' }).click();
  await expect(page.getByRole('link', { name: 'Open Amira’s journey' })).toBeVisible();
  await expect(page.getByRole('link', { name: /1 Open obligations/ })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Prevention Decision Queue' })).toBeVisible();
  await expect(page.locator('.decision-counts button').filter({ hasText: 'Awaiting evidence' }).locator('strong')).toHaveText('1');
  await expect(page.getByRole('link', { name: /0 Blocked or escalated/ })).toBeVisible();
  if (captureDir) {
    await page.getByText('Innovation showcase', { exact: true }).click();
    await page.getByText('Technical evaluation', { exact: true }).click();
    await capture('01-population');
  }
  const navigating = performance.now();
  await page.getByRole('link', { name: 'Open workspace' }).click();
  await expect(page.getByRole('heading', { name: 'Amira Haddad' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Decision Timeline' })).toBeVisible();
  timings.workspaceNavigationMs = Math.round(performance.now() - navigating);
  await expect(page.getByRole('combobox', {name:'Patient',exact:true})).toHaveValue('demo-amira');
  await page.getByRole('link', { name: /Preconception metabolic assessment review/ }).first().click();
  await expect(page.getByText('Required completion evidence is missing.')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Prevention Decision', exact: true })).toBeVisible();
  await expect(page.getByText('Timing not established.', { exact: true })).toBeVisible();
  if (await page.locator('#provenance').getAttribute('open') === null)
    await page.getByText('Source evidence and provenance', { exact: true }).click();
  await expect(page.locator('#provenance')).toContainText('Observation/demo-initial-flag');
  await expect(page.locator('#provenance')).toContainText('preconception-follow-up@1.0.0');
  await page.getByRole('link', { name: 'Workspace' }).click();
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
  await page.locator('.dependency-node').filter({hasText:'Pregnancy handoff review'}).click();
  await expect(page.locator('#provenance')).toHaveAttribute('open', '');
  await expect(page.locator('#provenance')).toContainText('Observation/demo-amira-pregnancy');
  await page.getByRole('link', { name: 'Workspace' }).click();
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
  await expect(page.getByRole('heading', { name: 'Multi-Agent Clinical Intelligence' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Run Multi-Agent Investigation' })).toBeDisabled();
  await expect(page.getByText('No multi-agent investigations recorded for this selection.')).toBeVisible();
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
  await page.getByRole('link', { name: 'Care resolution' }).click();
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
  if(new URL(page.url()).pathname==='/') await page.locator('.admin-drawer').evaluate(el => (el as HTMLDetailsElement).open=true);
  await expect(verification.getByText('Closure verified')).toBeVisible();
  await page.getByRole('link', { name: 'Population' }).click();
  await page.locator('.admin-drawer').evaluate(el => (el as HTMLDetailsElement).open=true);
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
  if(new URL(page.url()).pathname==='/') await page.locator('.admin-drawer').evaluate(el => (el as HTMLDetailsElement).open=true);
  await expect(page.getByRole('link', { name: /2 Synthetic patients/ })).toBeVisible();
  await page.getByRole('row', { name: /Noor Demo/ }).getByRole('link', { name: 'Open workspace' }).click();
  await expect(page.getByRole('heading', { name: 'Noor Demo' })).toBeVisible();
  await expect(page.getByText('Observation/demo-initial-flag', { exact: true })).toHaveCount(0);
  // Source IDs are now in technical details; also assert the clinical data itself is absent.
  const noorEvidence = page.locator('section').filter({has:page.getByRole('heading',{name:'Clinical evidence',exact:true})});
  await expect(noorEvidence.locator('tbody tr')).toHaveCount(0);
  await page.getByRole('combobox', { name: 'Patient' }).selectOption('demo-amira');
  await expect(page.getByRole('heading', { name: 'Amira Haddad' })).toBeVisible();

  await page.getByText('Clinical evidence explorer', { exact: true }).click();
  const datasetResponse=page.waitForResponse(response=>response.request().method()==='POST'&&new URL(response.url()).pathname==='/api/v1/clinical/demo/dataset');
  await page.getByRole('button', { name: 'Load Amira’s synthetic dataset' }).click();
  expect((await datasetResponse).ok()).toBeTruthy();
  await expect(page.getByText('Synthetic dataset available.')).toBeVisible();
  await page.getByLabel('Search evidence').fill('reconciliation');
  await page.getByRole('button', { name: 'Search', exact: true }).click();
  const clinicalNote = page.locator('.clinical-results li[data-source-reference="DocumentReference/demo-m08-note"]');
  await clinicalNote.locator('summary').click();
  await expect(clinicalNote.getByText('Source excerpt · untrusted clinical text')).toBeVisible();
  await expect(clinicalNote.getByText('Clinician reconciliation remains outstanding.', { exact: true })).toBeVisible();

  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
    'Expanded clinical explorer fits at 390 px').toBe(true);
  await expect(stages.locator('[aria-current="step"]')).toContainText('Pregnancy');
  for (const route of ['/workspace?patient=demo-amira', '/passport', '/resolution', '/audit', '/']) {
    await page.goto(route);
    if(route==='/') await page.locator('.admin-drawer').evaluate(el => (el as HTMLDetailsElement).open=true);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    await expect(page.getByLabel('Demo clock banner')).toContainText(/Demo date: .* · synthetic/);
    await expect(page.locator('.app-header').getByLabel('Demo as-of date')).toHaveCount(0);
    if (route.startsWith('/workspace')) await expect(page.getByLabel('Demo as-of date')).toHaveCount(0);
    if (route === '/passport' || route === '/') await expect(page.getByLabel('Demo as-of date')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), route + ' fits at 390 px').toBe(true);
    if (route.startsWith('/workspace')) await capture('08-mobile-workspace');
  }

  if (!(await page.locator('.admin-drawer').evaluate(el => (el as HTMLDetailsElement).open))) await page.getByText('Admin', { exact: true }).click();
  await page.getByText('Reset Amira demo', { exact: true }).click();
  const amiraResetResponse = page.waitForResponse(response => response.url().endsWith('/api/demo/reset-amira') && response.request().method()==='POST');
  await page.getByRole('button', { name: 'Confirm reset' }).click();
  expect((await amiraResetResponse).ok()).toBeTruthy();
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
  // A full-document navigation can abort the mutation; a completed click is not a committed follow-up.
  const followUpResponse = page.waitForResponse(response => response.request().method() === 'POST'
    && /^\/api\/v1\/prevention\/decisions\/[^/]+\/follow-up\/0$/.test(new URL(response.url()).pathname));
  await page.getByRole('button', { name: 'Initiate follow-up 1' }).click();
  const followUp = await followUpResponse;
  expect(followUp.ok()).toBeTruthy();
  const initiatedDecision = await followUp.json();
  expect(initiatedDecision.record.follow_up).toContain('Obtain a synthetic clinician reconciliation note.');
  await page.goto('/audit');
  const decisionHistory = page.locator('section').filter({ has: page.getByRole('heading', { name: 'Decision History' }) });
  await expect(decisionHistory.getByText('Decision recorded', { exact: true })).toBeVisible();
  await expect(decisionHistory.getByText('Follow up initiated', { exact: true })).toBeVisible();
  await page.goto('/');
  if (!(await page.locator('.admin-drawer').evaluate(el => (el as HTMLDetailsElement).open))) await page.getByText('Admin', { exact: true }).click();
  const timingSeed=page.waitForResponse(response=>response.request().method()==='POST'&&new URL(response.url()).pathname==='/api/v1/prevention/demo/timing');
  const timedCounts=page.waitForResponse(async response=>response.request().method()==='GET'&&new URL(response.url()).pathname==='/api/v1/prevention/snapshot'&&!new URL(response.url()).search&&response.ok()&&(await response.json()).counts.due_soon===1);
  await page.getByRole('button', { name: 'Load illustrative timing scenario' }).click();
  expect((await timingSeed).ok()).toBeTruthy();expect((await timedCounts).ok()).toBeTruthy();
  await expect(page.locator('.decision-counts button').filter({ hasText: 'Due soon' }).locator('strong')).toHaveText('1');
  await expect(page.locator('.decision-counts button').filter({ hasText: 'Overdue' }).locator('strong')).toHaveText('1');

  // TSP extension uses the same real backend and existing clinical gates; no model calls.
  const initialTspSeed=page.waitForResponse(response=>response.request().method()==='POST'&&new URL(response.url()).pathname==='/api/v1/tsp/demo/seed');
  await page.getByRole('button', { name: 'Load TSP demo', exact: true }).click();
  expect((await initialTspSeed).ok()).toBeTruthy();
  const tspQueue = page.locator('section').filter({ has: page.getByRole('heading', { name: 'Time-Sensitive Prevention Windows', exact: true }) });
  const amiraWindow = tspQueue.getByRole('row').filter({ has: page.getByRole('cell', { name: 'Amira Haddad', exact: true }) });
  await expect(amiraWindow.getByText('IN WINDOW', { exact: true })).toBeVisible();
  const coordinationQueue = page.locator('section').filter({has:page.getByRole('heading',{name:'Review first',exact:true})});
  const amiraCoordination = coordinationQueue.getByRole('row').filter({has:page.getByRole('cell',{name:/Amira Haddad/})});
  await expect(amiraCoordination.getByRole('link',{name:'Send to reviewer (Coordinator)',exact:true})).toBeVisible();
  const uncertain = tspQueue.getByRole('row').filter({ has: page.getByRole('cell', { name: 'Uncertain dating patient', exact: true }) });
  await expect(uncertain.getByText('HOLD DATING UNCERTAIN')).toBeVisible();
  await expect(uncertain.getByText('No established window')).toBeVisible();
  const auth = { Authorization: 'Bearer ' + process.env.E2E_COORDINATOR_TOKEN };
  const initial = await (await page.request.get('/api/v1/tsp/patients/demo-amira/window', { headers: auth })).json();
  const upcoming = new Date(initial.windows.find((w: { id: string }) => w.id === 'W2').window_start + 'T00:00:00Z');
  upcoming.setUTCDate(upcoming.getUTCDate() - 1);
  await page.getByLabel('Demo as-of date').fill(upcoming.toISOString().slice(0, 10));
  await page.getByRole('button', { name: 'Apply demo date' }).click();
  await expect(amiraWindow.getByText('DUE SOON', { exact: true })).toBeVisible();
  await expect(amiraCoordination.getByRole('link',{name:'Schedule assessment (Coordinator)',exact:true})).toBeVisible();
  await expect(page.getByText(/future[- ]dated|date is in the future/i)).toHaveCount(0);
  await page.getByRole('button', { name: 'Reset demo date', exact: true }).click();
  await expect(amiraWindow.getByText('IN WINDOW', { exact: true })).toBeVisible();
  const tspObligation = initial.obligation_ids[0];
  await page.goto('/passport?obligation=' + tspObligation);
  await page.getByRole('button', { name: 'Add dated synthetic result' }).click();
  const windowPanel = page.locator('section').filter({ has: page.getByRole('heading', { name: 'Time-Sensitive Prevention Window', exact: true }) });
  await expect(windowPanel.getByText('COMPLETED IN WINDOW', { exact: true }).first()).toBeVisible();
  await expect(page.getByText('None — no coordination action specified for this state.',{exact:true})).toBeVisible();
  const task = await (await page.request.post('/api/obligations/' + tspObligation + '/agent', { headers: auth })).json();
  const before = await (await page.request.get('/api/snapshot', { headers: auth })).json();
  const ref = before.clinical_evidence.find((e: { resource: { id: string } }) => e.resource.id === 'demo-' + tspObligation + '-verified');
  const approved = await page.request.post('/api/tasks/' + task.id + '/review', { headers: { Authorization: 'Bearer ' + process.env.E2E_REVIEWER_TOKEN },
    data: { decision: 'approve', evidence_refs: ['Observation/' + ref.resource.id], note: 'Synthetic TSP source reviewed.' } });
  expect(approved.ok()).toBeTruthy();
  const afterApproval = await (await page.request.get('/api/snapshot', { headers: auth })).json();
  expect(afterApproval.clinical_obligations.find((o: { id: string }) => o.id === tspObligation).status).toBe('open');
  expect((await page.request.post('/api/obligations/' + tspObligation + '/close', { headers: auth })).ok()).toBeTruthy();
  await page.reload();
  if(new URL(page.url()).pathname==='/') await page.locator('.admin-drawer').evaluate(el => (el as HTMLDetailsElement).open=true);
  await expect(windowPanel.getByText(/Closure verified through existing gates/)).toBeVisible();
  // The actual Evidence & audit demo control corrects the closing source through M08.
  const originalOwner = afterApproval.clinical_obligations.find((o: {id:string})=>o.id===tspObligation).owner;
  await page.goto('/audit');
  await page.getByLabel('Inspect obligation').selectOption(tspObligation);
  await page.getByRole('button',{name:'Simulate evidence correction (demo)',exact:true}).click();
  const confirmation = page.getByRole('group',{name:'Confirm simulated evidence correction'});
  await expect(confirmation).toBeVisible();
  await capture('action-closed-confirm-correction');
  const correctionResponse = page.waitForResponse(response=>response.request().method()==='POST'&&new URL(response.url()).pathname==='/api/v1/tsp/demo/obligations/'+tspObligation+'/correct-closing-evidence');
  await confirmation.getByRole('button',{name:'Confirm simulated correction',exact:true}).click();
  const corrected = await correctionResponse;
  expect(corrected.ok()).toBeTruthy();
  expect((await corrected.json()).obligation_status).toBe('open');
  await expect(page.getByText('Simulated correction recorded. Obligation open; returned to assigned owner: '+originalOwner+'.', {exact:true})).toBeVisible();
  const reopened = await (await page.request.get('/api/snapshot', { headers: auth })).json();
  const reopenedObligation = reopened.clinical_obligations.find((o: { id: string }) => o.id === tspObligation);
  expect(reopenedObligation.status).toBe('open');
  expect(reopenedObligation.owner).toBe(originalOwner);
  expect(reopened.audit_events.some((event:{action:string;obligation_id:string})=>event.action==='closure_reopened'&&event.obligation_id===tspObligation)).toBe(true);
  await page.goto('/passport?obligation='+tspObligation);
  await expect(windowPanel.getByText('IN WINDOW', { exact: true }).first()).toBeVisible();
  await expect(page.getByLabel('Obligation checkpoints').getByText('Reopened',{exact:true})).toBeVisible();
  await expect(page.getByLabel('Obligation checkpoints').getByText('Correction recorded; returned to '+originalOwner,{exact:true})).toBeVisible();
  const guidelinePanel = page.locator('section').filter({has:page.getByRole('heading',{name:'Guideline traceability',exact:true})});
  await expect(guidelinePanel.getByText('pending clinical confirmation',{exact:true}).first()).toBeVisible();
  await expect(guidelinePanel.getByText('glycemic-assessment-pregnancy · version 1',{exact:true})).toBeVisible();
  await expect(guidelinePanel.getByText('W1: requires a carried preconception obligation.',{exact:true})).toBeVisible();
  await expect(guidelinePanel.getByRole('link',{name:'Open source record'}).first()).toBeVisible();
  await expect(page.getByText('Send to reviewer (Coordinator)',{exact:true})).toBeVisible();
  await guidelinePanel.getByRole('link',{name:'Open source record'}).first().click();
  await expect(guidelinePanel.getByLabel('Guideline source viewer')).toBeVisible();
  await capture('action-reopened-passport');
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'TSP passport fits at 390 px').toBe(true);
  await capture('09-tsp-passport');
  await page.goto('/');
  if (!(await page.locator('.admin-drawer').evaluate(el => (el as HTMLDetailsElement).open))) await page.getByText('Admin', { exact: true }).click();
  await page.getByRole('button', { name: 'Reset TSP demo', exact: true }).click();
  const tspResetResponse=page.waitForResponse(response=>response.request().method()==='POST'&&new URL(response.url()).pathname==='/api/v1/tsp/demo/reset');
  await page.getByRole('button', { name: 'Confirm reset TSP demo', exact: true }).click();
  expect((await tspResetResponse).ok()).toBeTruthy();
  await expect(amiraWindow.getByText('IN WINDOW', { exact: true })).toBeVisible();
  await expect(page.getByLabel('Demo clock banner')).toContainText('2026-11-22');

  const freshProfile=await browser.newContext();
  try {
    const freshPage=await freshProfile.newPage();
    await freshPage.goto(new URL('/',page.url()).href);
    await signIn(freshPage,'coordinator');
    await expect(freshPage.getByLabel('Demo clock banner')).toContainText('2026-11-22');
    await expect(freshPage.getByLabel('Demo as-of date')).toHaveValue('2026-11-22');
  } finally {await freshProfile.close();}

  // SIMULATED inter-facility handoff: genuine local feed/receipts and unchanged clinical gates.
  const simulatedSeed=page.waitForResponse(response=>response.request().method()==='POST'&&new URL(response.url()).pathname==='/api/v1/simulated-handoff/demo/seed');
  await page.getByRole('button', { name: 'Load simulated handoff demo' }).click();
  expect((await simulatedSeed).ok()).toBeTruthy();
  await page.getByRole('link', { name: 'Open simulated handoff workspace' }).click();
  const receivingView = page.locator('section').filter({ has: page.getByRole('heading', { name: 'SIMULATED Hospital B receiving view', exact: true }) });
  await expect(receivingView.getByText('Hospital A — SIMULATED originating care team', { exact: true }).first()).toBeVisible();
  await expect(receivingView.getByRole('button', { name: 'Receive records from Hospital A' })).toBeDisabled();
  const simulatedRegistration=page.waitForResponse(response=>response.request().method()==='POST'&&new URL(response.url()).pathname==='/api/patients/demo-handoff/pregnancy');
  const receivingState=page.waitForResponse(async response=>response.request().method()==='GET'&&new URL(response.url()).pathname==='/api/v1/simulated-handoff/patients/demo-handoff'&&response.ok()&&(await response.json()).stage==='pregnancy');
  await page.getByRole('button', { name: 'Register pregnancy', exact: true }).click();
  expect((await simulatedRegistration).ok()).toBeTruthy();expect((await receivingState).ok()).toBeTruthy();
  await expect(receivingView.getByRole('button', { name: 'Receive records from Hospital A' })).toBeEnabled();
  const simulatedReceipt=page.waitForResponse(response=>response.request().method()==='POST'&&new URL(response.url()).pathname==='/api/v1/simulated-handoff/patients/demo-handoff/receive');
  await receivingView.getByRole('button', { name: 'Receive records from Hospital A' }).click();
  expect((await simulatedReceipt).ok()).toBeTruthy();
  await expect(receivingView.getByText('Hospital B — SIMULATED receiving care team', { exact: true })).toBeVisible();
  await expect(receivingView.getByText(/Origin: Hospital A, received/)).toBeVisible();
  await receivingView.getByText('SIMULATED owner history', { exact: true }).click();
  await expect(receivingView.locator('.handoff-history li').filter({ hasText: 'Hospital A — SIMULATED originating care team → Hospital B — SIMULATED receiving care team' })).toBeVisible();
  const handoffTimeline = page.locator('section').filter({ has: page.getByRole('heading', { name: 'SIMULATED facility timeline', exact: true }) });
  await expect(handoffTimeline.getByText('Unresolved obligation surfaced in the receiving view')).toBeVisible();
  await page.getByText('Clinical evidence explorer', { exact: true }).click();
  await page.getByLabel('Resource type').selectOption('DocumentReference');
  const exchangeNote = page.locator('.clinical-results li[data-source-reference="DocumentReference/demo-handoff-received-note"]');
  await exchangeNote.locator('summary').click();
  await expect(exchangeNote.getByText('SIMULATED · Hospital A', { exact: true })).toBeVisible();
  await expect(exchangeNote.getByText(/received via simulated exchange/)).toBeVisible();
  const handoffState = await (await page.request.get('/api/v1/simulated-handoff/patients/demo-handoff', { headers: auth })).json();
  const receiptReplay = await (await page.request.post('/api/v1/simulated-handoff/patients/demo-handoff/receive', { headers: auth })).json();
  expect(receiptReplay.received_at).toBe(handoffState.received_at);
  const handoffObligation = handoffState.obligation_id;
  const handoffResult = await (await page.request.post('/api/obligations/' + handoffObligation + '/demo-completion', { headers: auth, data: { scenario: 'verified' } })).json();
  const handoffTask = await (await page.request.post('/api/obligations/' + handoffObligation + '/agent', { headers: auth })).json();
  expect((await page.request.post('/api/tasks/' + handoffTask.id + '/review', { headers: { Authorization: 'Bearer ' + process.env.E2E_REVIEWER_TOKEN },
    data: { decision: 'approve', evidence_refs: ['Observation/' + handoffResult.id], note: 'SIMULATED Hospital B reviewer inspected original evidence.' } })).ok()).toBeTruthy();
  const beforeHandoffClose = await (await page.request.get('/api/v1/simulated-handoff/patients/demo-handoff', { headers: auth })).json();
  expect(beforeHandoffClose.obligation_status).toBe('open');
  expect((await page.request.post('/api/obligations/' + handoffObligation + '/close', { headers: auth })).ok()).toBeTruthy();
  await page.goto('/passport?obligation=' + handoffObligation);
  await expect(receivingView.getByText('Closed', { exact: true })).toBeVisible();
  await receivingView.getByRole('button', { name: 'Receive simulated origin invalidation' }).click();
  await expect(receivingView.getByText('Open', { exact: true })).toBeVisible();
  await expect(receivingView.getByText('Hospital B — SIMULATED receiving care team', { exact: true })).toBeVisible();
  const handoffReopened = await (await page.request.get('/api/v1/simulated-handoff/patients/demo-handoff', { headers: auth })).json();
  expect(handoffReopened.obligation_status).toBe('open');
  expect(handoffReopened.original_owner).toContain('Hospital A');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'SIMULATED handoff passport fits at 390 px').toBe(true);
  await testInfo.attach('SIMULATED handoff proof', { body: JSON.stringify({ before: handoffState, after: handoffReopened }), contentType: 'application/json' });
  await capture('10-simulated-handoff');
  expect((await page.request.post('/api/demo/jury-seed',{headers:auth})).ok()).toBeTruthy();
  await page.goto('/');
  await expect(page.getByRole('heading',{name:'Review first'})).toBeVisible();
  await expect(page.getByRole('cell',{name:/Lina Omar/})).toBeVisible();
  await expect(page.getByRole('cell',{name:/Sara Ali/})).toBeVisible();
  await expect(page.getByRole('cell',{name:/Amira Haddad/})).toBeVisible();
  await page.evaluate(()=>document.fonts.ready);
  await mkdir('../demo-assets',{recursive:true});
  for(const [width,height] of [[1366,768],[1920,1080]]) {
    await page.setViewportSize({width,height});
    if(process.env.REPROBRIDGE_NO_MEDIA !== "true") await page.screenshot({path:`../demo-assets/dashboard-${width}x${height}.png`,fullPage:false,animations:'disabled'});
  }
  await page.getByText('Switch demo role', {exact:true}).click();
  await page.getByRole('combobox',{name:'Demo role',exact:true}).selectOption('reviewer');
  await page.getByLabel('Existing role token').fill(process.env.E2E_REVIEWER_TOKEN!);
  await page.getByRole('button',{name:'Switch role',exact:true}).click();
  await expect(page.locator('.role')).toHaveText('Reviewer');
  if(!(await page.getByLabel('Existing role token').isVisible())) await page.getByText('Switch demo role',{exact:true}).click();
  await page.getByRole('combobox',{name:'Demo role',exact:true}).selectOption('coordinator');
  await page.getByLabel('Existing role token').fill(process.env.E2E_COORDINATOR_TOKEN!);
  await page.getByRole('button',{name:'Switch role',exact:true}).click();
  await expect(page.locator('.role')).toHaveText('Coordinator');

  // Historical Amira source -> SIMULATED Hospital B view -> existing W1 -> human review -> closure.
  await page.goto('/workspace?patient=demo-amira');
  const earlier = page.locator('section').filter({has:page.getByRole('heading',{name:'Found in earlier records',exact:true})});
  const windowBefore = await (await page.request.get('/api/v1/tsp/patients/demo-amira/window',{headers:auth})).json();
  const historicalReceiptResponse = page.waitForResponse(response=>response.url().endsWith('/api/v1/history-handoff/patients/demo-amira/receive')&&response.request().method()==='POST');
  await earlier.getByRole('button',{name:'Receive earlier Hospital A records'}).click();
  const historicalReceipt = await historicalReceiptResponse;
  expect(historicalReceipt.ok()).toBeTruthy();
  expect((await historicalReceipt.json()).findings).toHaveLength(2);
  await expect(earlier.getByText('documented PCOS diagnosis',{exact:true})).toBeVisible();
  await expect(earlier.getByText('Recorded 2011-07-10 · version 1',{exact:true})).toHaveCount(2);
  await expect(earlier.getByText('Documented finding linked to existing W1',{exact:true})).toBeVisible();
  await expect(earlier.getByText(/Age 16 at the 2011 record; age 31/)).toBeVisible();
  const historyState = await (await page.request.get('/api/v1/history-handoff/patients/demo-amira',{headers:auth})).json();
  expect(historyState.window.status).toBe(windowBefore.status);
  expect(historyState.rule_traces[0].triggered).toBe(true);
  expect(historyState.findings.every((item:{provenance:{facility:{origin:string;receiving:string}}})=>item.provenance.facility.origin==='Hospital A'&&item.provenance.facility.receiving==='Hospital B')).toBe(true);
  // A distinct, non-actionable candidate is now created by the deterministic observer.
  const detectedCandidates=await (await page.request.get('/api/v1/historical-candidates/patients/demo-amira',{headers:auth})).json();
  expect(detectedCandidates).toHaveLength(1);
  expect(detectedCandidates[0].status).toBe('candidate');
  expect(detectedCandidates[0].owner_role).toBe('Reviewer');
  await page.goto('/');
  const identifiedBadge=page.getByRole('link',{name:'Identified from earlier records · 1',exact:true});
  await expect(identifiedBadge).toBeVisible();
  await expect(page.getByText(/Historical screening review identified from earlier records for Amira H\./)).toBeVisible();
  await identifiedBadge.click();
  await expect(page.getByText('Candidate: needs clinician confirmation',{exact:true})).toBeVisible();
  await expect(page.getByRole('heading',{name:'Early-pregnancy glycemic screening review - identified from earlier record',exact:true})).toBeVisible();
  await page.getByRole('link',{name:'Read source documents',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Source documents',exact:true})).toBeVisible();
  await expect(page.locator('nav a[aria-current="page"]')).toContainText('Source documents');
  await page.getByRole('button',{name:/Adolescent clinic note/}).click();
  await expect(page.getByLabel('Full stored document text')).toContainText('Hospital A recorded:');
  await expect(page.locator('.stored-document mark')).toHaveText('documented PCOS diagnosis');
  await expect(page.getByText('Accepted formats today: plain text and Markdown. PDF and scanned documents are on the roadmap.',{exact:true})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Read-only documents fit the viewport').toBe(true);
  await capture('11-source-documents');
  await page.getByRole('link',{name:'View where it is cited',exact:true}).click();
  await expect(page.getByText('Candidate: needs clinician confirmation',{exact:true})).toBeVisible();

  await expect(page.getByRole('button',{name:'Confirm historical candidate',exact:true})).toHaveCount(0);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Candidate passport fits at 390 px').toBe(true);
  await page.goto('/workspace?patient=demo-amira');
  await expect(page.getByLabel('Historical detection timeline')).toContainText('2026-11-22');
  await earlier.getByRole('button',{name:'Open source document',exact:true}).click();
  await expect(earlier.locator('.history-document')).toContainText('Hospital A recorded: documented PCOS diagnosis');
  await earlier.getByRole('button',{name:'Close source',exact:true}).click();
  const historicalObligation = historyState.rule_traces[0].obligation_ids[0];
  await page.goto('/passport?obligation='+historicalObligation);
  await expect(earlier.getByText('documented PCOS diagnosis',{exact:true})).toBeVisible();
  const historicalCompletion = {resourceType:'Observation',id:'demo-browser-history-reviewed',meta:{tag:[{system:'https://reprobridge.example/fhir/CodeSystem/demo',code:'synthetic'}]},subject:{reference:'Patient/demo-amira'},status:'final',code:{coding:[{system:'https://reprobridge.example/fhir/CodeSystem/demo',code:'follow-up-reconciled'}]},valueString:'verified',effectiveDateTime:'2026-11-15'};
  expect((await page.request.post('/api/fhir/import',{headers:auth,data:{resources:[historicalCompletion]}})).ok()).toBeTruthy();
  const historicalTask = await (await page.request.post('/api/obligations/'+historicalObligation+'/agent',{headers:auth})).json();
  expect((await page.request.post('/api/tasks/'+historicalTask.id+'/review',{headers:{Authorization:'Bearer '+process.env.E2E_REVIEWER_TOKEN},data:{decision:'approve',evidence_refs:['Observation/'+historicalCompletion.id],note:'Reviewed the simulated earlier source and pending rule; no risk conclusion.'}})).ok()).toBeTruthy();
  const reviewedHistory = await (await page.request.get('/api/v1/history-handoff/patients/demo-amira',{headers:auth})).json();
  expect(reviewedHistory.rule_traces[0].triggered).toBe(true); // Approval alone leaves work open.
  expect((await page.request.post('/api/obligations/'+historicalObligation+'/close',{headers:auth})).ok()).toBeTruthy();
  const closedHistory = await (await page.request.get('/api/v1/history-handoff/patients/demo-amira',{headers:auth})).json();
  expect(closedHistory.rule_traces[0].triggered).toBe(false);
  expect(closedHistory.window.status).toBe('COMPLETED_IN_WINDOW');
  expect(closedHistory.findings.map((item:{digest:string})=>item.digest)).toEqual(historyState.findings.map((item:{digest:string})=>item.digest));
  await page.reload();
  await expect(earlier.getByText('No trigger from this historical rule',{exact:true})).toBeVisible();
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Earlier-record passport fits at 390 px').toBe(true);
  const ruleFallbackResponse=page.waitForResponse(response=>response.request().method()==='POST'&&new URL(response.url()).pathname==='/api/v1/history-handoff/patients/demo-amira/explanations');
  await earlier.getByRole('button',{name:'Explain cited earlier record'}).click();
  const fallbackRun=await (await ruleFallbackResponse).json();
  expect(fallbackRun.detail.usage.model_calls).toBe(0);
  expect(fallbackRun.detail.tool_history).toEqual([]);
  expect(fallbackRun.detail.packet.origin).toBe('system_abstention');
  expect(fallbackRun.detail.explanation.accepted).toBe(false);
  await expect(earlier.getByText('Rule-generated explanation (agent abstained)',{exact:true})).toBeVisible();
  await expect(earlier.getByText('Agent abstained. Its result has not been accepted.',{exact:true})).toBeVisible();
  await earlier.getByText('Explanation trace',{exact:true}).click();
  await expect(earlier.locator('pre').filter({hasText:'provider_unavailable: disabled'})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Explanation fallback and expanded trace fit at 390 px').toBe(true);
  await testInfo.attach('SIMULATED earlier-record handoff',{body:JSON.stringify({received:historyState,closed:closedHistory}),contentType:'application/json'});

  // Human confirmation creates a NEW normal obligation; no model decides it or closes it.
  const candidate=detectedCandidates[0];
  const windowBeforeConfirmation=await (await page.request.get('/api/v1/tsp/patients/demo-amira/window',{headers:auth})).json();
  await page.goto('/passport?candidate='+candidate.id+'&patient=demo-amira');
  await page.getByRole('button',{name:'Sign out'}).click();await signIn(page,'reviewer');
  await page.getByLabel('Candidate review rationale').fill('Synthetic clinician inspected the cited earlier record and pending policy; confirm coordination review only.');
  const candidateReviewResponse=page.waitForResponse(response=>response.request().method()==='POST'&&new URL(response.url()).pathname==='/api/v1/historical-candidates/'+candidate.id+'/review');
  await page.getByRole('button',{name:'Confirm historical candidate',exact:true}).click();
  const candidateReview=await candidateReviewResponse;expect(candidateReview.ok()).toBeTruthy();
  const confirmedCandidate=await candidateReview.json();expect(confirmedCandidate.status).toBe('confirmed');
  const newObligationId=confirmedCandidate.obligation_id;expect(newObligationId).not.toBe(historicalObligation);
  await expect(page.getByText('Confirmed by clinician',{exact:true})).toBeVisible();
  let candidateSnapshot=await (await page.request.get('/api/snapshot',{headers:auth})).json();
  expect(candidateSnapshot.clinical_obligations.find((item:{id:string})=>item.id===newObligationId)).toMatchObject({status:'open',owner:'Reviewer'});
  expect((await page.request.post('/api/obligations/'+newObligationId+'/close',{headers:auth})).status()).toBe(409);
  await page.getByRole('button',{name:'Sign out'}).click();await signIn(page,'coordinator');
  await page.goto('/audit');await page.getByLabel('Completion evidence obligation',{exact:true}).selectOption(newObligationId);
  await page.getByRole('button',{name:'Add verified evidence',exact:true}).click();
  await expect(page.getByRole('status')).toContainText('Verified fixture submitted');
  await page.goto('/passport?obligation='+newObligationId);
  const newRoutingResponse=page.waitForResponse(response=>response.request().method()==='POST'&&new URL(response.url()).pathname==='/api/obligations/'+newObligationId+'/agent');
  await page.getByRole('button',{name:'Run care-resolution agent',exact:true}).click();
  expect((await newRoutingResponse).ok()).toBeTruthy();
  await expect(page.getByRole('status')).toContainText('Coordination action routed for review');
  candidateSnapshot=await (await page.request.get('/api/snapshot',{headers:auth})).json();
  const newTask=candidateSnapshot.care_coordination_tasks.find((item:{obligation_id:string;status:string})=>item.obligation_id===newObligationId&&item.status==='pending');
  expect(newTask).toBeTruthy();
  await page.getByRole('button',{name:'Sign out'}).click();await signIn(page,'reviewer');await page.goto('/resolution?obligation='+newObligationId);
  await page.getByLabel('Review note',{exact:true}).fill('Reviewed the new obligation completion evidence; candidate confirmation alone was insufficient.');
  const newApprovalResponse=page.waitForResponse(response=>response.request().method()==='POST'&&new URL(response.url()).pathname==='/api/tasks/'+newTask.id+'/review');
  await page.getByRole('button',{name:'Approve',exact:true}).click();expect((await newApprovalResponse).ok()).toBeTruthy();
  candidateSnapshot=await (await page.request.get('/api/snapshot',{headers:auth})).json();
  expect(candidateSnapshot.clinical_obligations.find((item:{id:string})=>item.id===newObligationId).status).toBe('open');
  await page.getByRole('button',{name:'Sign out'}).click();await signIn(page,'coordinator');await page.goto('/passport?obligation='+newObligationId);
  // A pending write is not a closure confirmation; wait for the actual server acknowledgment.
  const finalClosureResponse=page.waitForResponse(response=>response.request().method()==='POST'&&new URL(response.url()).pathname==='/api/obligations/'+newObligationId+'/close');
  await page.getByRole('button',{name:'Verify closure',exact:true}).click();
  const finalClosure=await finalClosureResponse;expect(finalClosure.ok()).toBeTruthy();expect((await finalClosure.json()).status).toBe('closed');
  await expect(page.getByRole('status')).toContainText('Closure verified');
  expect(await (await page.request.get('/api/v1/tsp/patients/demo-amira/window',{headers:auth})).json()).toEqual(windowBeforeConfirmation);
  const trigger=candidate.source_refs.find((item:{trigger:boolean})=>item.trigger);
  const triggerResource=(await (await page.request.get(trigger.source_url,{headers:auth})).json()).resource;
  const invalidation=await page.request.post('/api/v1/clinical/patients/demo-amira/events',{headers:auth,data:{source:'synthetic-history-hospital-a',event_id:'browser-historical-trigger-invalidation',event_time:new Date().toISOString(),resource:triggerResource,version:trigger.version+1,action:'invalidate'}});
  expect(invalidation.ok()).toBeTruthy();
  await page.goto('/passport?candidate='+candidate.id+'&patient=demo-amira');
  await expect(page.getByText('Withdrawn: trigger evidence no longer valid',{exact:true})).toBeVisible();
  candidateSnapshot=await (await page.request.get('/api/snapshot',{headers:auth})).json();
  expect(candidateSnapshot.clinical_obligations.find((item:{id:string})=>item.id===newObligationId)).toMatchObject({status:'open',owner:'Reviewer'});
  expect(candidateSnapshot.audit_events.some((event:{action:string;detail:{candidate_id?:string;demo_date?:string}})=>event.action==='historical_candidate_withdrawn'&&event.detail.candidate_id===candidate.id&&event.detail.demo_date==='2026-11-22')).toBe(true);
  expect((await page.request.post('/api/obligations/'+newObligationId+'/close',{headers:auth})).status()).toBe(409);
  expect(await (await page.request.get('/api/v1/tsp/patients/demo-amira/window',{headers:auth})).json()).toEqual(windowBeforeConfirmation);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Withdrawn candidate passport fits at 390 px').toBe(true);
  await testInfo.attach('Historical candidate lifecycle',{body:JSON.stringify({detected:candidate,confirmed:confirmedCandidate,withdrawn:true}),contentType:'application/json'});

});
