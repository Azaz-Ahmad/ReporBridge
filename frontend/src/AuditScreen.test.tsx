// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, test, vi } from 'vitest';
import { AuditScreen } from './AuditScreen';
import { api } from './api';
import type { Role, Snapshot } from './types';

vi.mock('./api', () => ({ api: vi.fn() }));
afterEach(() => { cleanup(); vi.resetAllMocks(); });
const snapshot: Snapshot = {
  patients: [{ id: 'demo-amira', stage: 'pregnancy', resource: { resourceType: 'Patient', id: 'demo-amira', name: [{ given: ['Amira'], family: 'Haddad' }] } }],
  clinical_obligations: [{ id: 'obligation-one', patient_id: 'demo-amira', rule_key: 'pre', source_id: 'demo-source', owner: 'Hospital B coordination', status: 'open', created: '2026-11-22' }],
  rule_versions: [{ id: 'pre', rule_id: 'pre', version: '1', pathway_id: 'preconception', definition: { title: 'Synthetic assessment review', description: 'Review', closure: 'follow-up-reconciled', trigger: 'follow-up-flag', source: 'pending clinical confirmation' } }],
  clinical_evidence: [], life_stage_events: [], obligation_dependencies: [], agent_executions: [], care_coordination_tasks: [], clinical_approvals: [], closure_evidence: [], demo_run_archive: [], audit_events: [],
  closure_readiness: { 'obligation-one': 'Required completion evidence is missing.' },
};
function mount(role: Role = 'coordinator', data = snapshot) {
  vi.mocked(api).mockImplementation(async (_token, path) => path === '/session' ? { demo_mode: true }
    : path.includes('source-documents') ? [] : path.includes('prevention') ? { decisions: [], history: [], counts: {} } : []);
  const action = vi.fn();
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter>
    <AuditScreen data={data} token="test" role={role} busy={false} action={action} />
  </MemoryRouter></QueryClientProvider>);
  return action;
}

test('five tabs default to closure, preserve backend blocker and defer model inspection', async () => {
  mount();
  expect(screen.getAllByRole('tab').map(tab => tab.textContent)).toEqual(['Closure & Evidence', 'Decision History', 'Audit Trail', 'Model Payload', 'FHIR Export']);
  expect(screen.getAllByRole('tabpanel')).toHaveLength(1);
  expect(screen.getByRole('tab', { name: 'Closure & Evidence' }).getAttribute('aria-selected')).toBe('true');
  expect(screen.getByRole('tabpanel').textContent).toContain('Required completion evidence is missing.');
  expect(screen.queryByText('Satisfied by the server closure check.')).toBeNull();
  await waitFor(() => expect(api).toHaveBeenCalled());
  expect(vi.mocked(api).mock.calls.some(call => call[1].includes('model-payloads'))).toBe(false);
  fireEvent.click(screen.getByRole('button', { name: 'Export FHIR bundle' }));
  expect(screen.getByRole('tabpanel').textContent).toContain('FHIR R4 export');
  expect(screen.getByRole('button', { name: 'Download FHIR bundle' })).toBeTruthy();
  expect(vi.mocked(api).mock.calls.some(call => call[1].includes('/fhir/patients'))).toBe(false);
});

test('existing synthetic evidence actions retain their endpoints and explicit scenarios', () => {
  const action = mount();
  fireEvent.click(screen.getByRole('button', { name: 'Add verified evidence' }));
  expect(action).toHaveBeenCalledWith('/obligations/obligation-one/demo-completion', 'Verified fixture submitted. Reviewer approval is still required.', { scenario: 'verified' });
  fireEvent.click(screen.getByRole('button', { name: 'Add conflicting evidence' }));
  expect(action).toHaveBeenCalledWith('/obligations/obligation-one/demo-completion', 'Conflicting fixture submitted.', { scenario: 'conflicting' });
  expect(screen.getByRole('link', { name: 'Verify closure in Passport' }).getAttribute('href')).toBe('/passport?obligation=obligation-one');
});

test.each(['viewer', 'reviewer'] as const)('%s cannot submit coordinator evidence', async role => {
  mount(role);
  await waitFor(() => expect(api).toHaveBeenCalled());
  expect(screen.queryByRole('button', { name: 'Add verified evidence' })).toBeNull();
  expect(screen.queryByRole('button', { name: 'Add conflicting evidence' })).toBeNull();
  if (role === 'viewer') {
    expect((screen.getByRole('tab', { name: 'Model Payload' }) as HTMLButtonElement).disabled).toBe(true);
    expect(vi.mocked(api).mock.calls.some(call => call[1].includes('model-payloads'))).toBe(false);
  }
});

test('audit pagination keeps every event reachable and preserves the displayed page across tabs', () => {
  mount('viewer', { ...snapshot, audit_events: Array.from({ length: 10 }, (_, i) => ({ sequence: i + 1, recorded: '2026-11-22T10:00:00Z', actor: 'coordinator', action: 'closure_blocked', patient_id: 'demo-amira', obligation_id: 'obligation-one', rule_key: 'pre', evidence_refs: [], detail: { reason: 'Recorded event ' + (i + 1) } })) });
  fireEvent.click(screen.getByRole('tab', { name: 'Audit Trail' }));
  expect(within(screen.getByRole('tabpanel')).getByText('Recorded event 1')).toBeTruthy();
  expect(within(screen.getByRole('tabpanel')).queryByText('Recorded event 10')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Next audit events' }));
  expect(within(screen.getByRole('tabpanel')).getByText('Recorded event 10')).toBeTruthy();
  fireEvent.click(screen.getByRole('tab', { name: 'Decision History' }));
  fireEvent.click(screen.getByRole('tab', { name: 'Audit Trail' }));
  expect(within(screen.getByRole('tabpanel')).getByText('Recorded event 10')).toBeTruthy();
});
