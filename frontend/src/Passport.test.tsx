// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, test, vi } from 'vitest';
import { Passport } from './Passport';
import type { Role, Snapshot } from './types';

vi.mock('./Jury', () => ({ JourneyStrip: () => <span>Existing pregnancy context</span> }));
vi.mock('./Tsp', () => ({ TspWindow: ({ nextAction }: { nextAction?: import('react').ReactNode }) => <section aria-label="Time-Sensitive Prevention Window">Existing calculator result{nextAction}</section> }));
vi.mock('./Coordination', () => ({ CoordinationNextAction: () => <span>Existing configured action</span>, GuidelineTraceability: () => <div>Existing guideline trace</div> }));
vi.mock('./History', () => ({ EarlierRecords: () => <div>Existing earlier evidence</div> }));
vi.mock('./Handoff', () => ({ HandoffPanel: () => null }));
vi.mock('./HistoricalCandidates', () => ({ HistoricalCandidates: () => <div>Existing candidate review controls</div> }));
vi.mock('./Prevention', () => ({ usePrevention: () => ({ data: { decisions: [], history: [] }, error: null, isPending: false }),
  PreventionPassport: () => <label>Existing decision reason<input defaultValue="" /></label> }));
afterEach(cleanup);

const data: Snapshot = {
  patients: [{ id: 'demo-amira', stage: 'pregnancy', resource: { resourceType: 'Patient', id: 'demo-amira', name: [{ given: ['Amira'], family: 'Haddad' }] } }],
  clinical_obligations: [{ id: 'prior', patient_id: 'demo-amira', rule_key: 'pre', source_id: 'demo-source', owner: 'Hospital B coordination', status: 'open', created: '2026-11-22' }],
  rule_versions: [{ id: 'pre', rule_id: 'pre', version: '1', pathway_id: 'preconception', definition: { title: 'Preconception review', description: 'Recorded assessment', trigger: 'flag', closure: 'reconciled', source: 'pending clinical confirmation' } }],
  clinical_evidence: [{ id: 'demo-source', patient_id: 'demo-amira', resource: { resourceType: 'Observation', id: 'demo-source', code: { text: 'Recorded finding' }, valueString: 'outstanding', status: 'final' } }],
  obligation_dependencies: [], life_stage_events: [], agent_executions: [], care_coordination_tasks: [], clinical_approvals: [], closure_evidence: [], audit_events: [], demo_run_archive: [],
  closure_readiness: { prior: 'Required completion evidence is missing.' },
};
function mount(role: Role = 'coordinator', snapshot = data, entry = '/passport?obligation=prior') {
  const action = vi.fn();
  const result = render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={[entry]}>
    <Passport data={snapshot} role={role} token="test" busy={false} action={action} />
  </MemoryRouter></QueryClientProvider>);
  return { action, ...result };
}

test('all five tabs retain the hero and keep one decision form mounted across switches', () => {
  mount();
  expect(screen.getAllByRole('tab').map(tab => tab.textContent)).toEqual(['Overview', 'Evidence', 'Decision History', 'Audit Trail', 'Guideline Trace']);
  fireEvent.change(screen.getByLabelText('Existing decision reason'), { target: { value: 'Keep this unsaved reason' } });
  for (const name of ['Evidence', 'Decision History', 'Audit Trail', 'Guideline Trace', 'Overview']) {
    fireEvent.click(screen.getByRole('tab', { name }));
    expect(screen.getAllByRole('tabpanel')).toHaveLength(1);
    expect(screen.getByRole('region', { name: 'Time-Sensitive Prevention Window' })).toBeTruthy();
  }
  expect((screen.getByLabelText('Existing decision reason') as HTMLInputElement).value).toBe('Keep this unsaved reason');
  expect(screen.getAllByLabelText('Existing decision reason')).toHaveLength(1);
});

test('existing coordinator actions and navigation destinations are unchanged', () => {
  const { action } = mount();
  fireEvent.click(screen.getByRole('button', { name: 'Run care-resolution agent' }));
  expect(action).toHaveBeenCalledWith('/obligations/prior/agent', 'Coordination action routed for review.');
  fireEvent.click(screen.getByRole('button', { name: 'Verify closure' }));
  expect(action).toHaveBeenCalledWith('/obligations/prior/close', 'Closure verified.');
  expect(screen.getByRole('link', { name: 'Open review queue' }).getAttribute('href')).toBe('/resolution?obligation=prior');
  expect(screen.getByRole('tabpanel').textContent).toContain('Required completion evidence is missing.');
  expect(screen.getByRole('link', { name: 'Read source documents' }).getAttribute('href')).toBe('/documents?patient=demo-amira');
});

test('Viewer receives no coordinator closure action and a provenance deep link opens Evidence', () => {
  mount('viewer', data, '/passport?obligation=prior#provenance');
  expect(screen.getByRole('tab', { name: 'Evidence' }).getAttribute('aria-selected')).toBe('true');
  expect(screen.getByText('Recorded finding · outstanding')).toBeTruthy();
  fireEvent.click(screen.getByRole('tab', { name: 'Overview' }));
  expect(screen.queryByRole('button', { name: 'Verify closure' })).toBeNull();
  expect(screen.queryByRole('button', { name: 'Run care-resolution agent' })).toBeNull();
});

test('candidate-only Passport preserves confirmation controls without presenting an active obligation workflow', () => {
  mount('reviewer', data, '/passport?candidate=candidate-one&patient=demo-amira');
  expect(screen.getByText('Existing candidate review controls')).toBeTruthy();
  expect(screen.getByText(/A candidate requires clinician confirmation/)).toBeTruthy();
  expect(screen.queryByRole('region', { name: 'Time-Sensitive Prevention Window' })).toBeNull();
  expect(screen.queryByRole('button', { name: 'Verify closure' })).toBeNull();
});

test('audit pagination retains every recorded event', () => {
  mount('viewer', { ...data, audit_events: Array.from({ length: 10 }, (_, index) => ({ sequence: index, recorded: '2026-11-22T10:00:00Z', actor: 'coordinator', action: 'closure_blocked', patient_id: 'demo-amira', obligation_id: 'prior', rule_key: 'pre', evidence_refs: [], detail: { reason: 'Recorded event ' + index } })) });
  fireEvent.click(screen.getByRole('tab', { name: 'Audit Trail' }));
  expect(within(screen.getByRole('tabpanel')).getByText('Recorded event 0')).toBeTruthy();
  expect(within(screen.getByRole('tabpanel')).queryByText('Recorded event 9')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Next audit events' }));
  expect(within(screen.getByRole('tabpanel')).getByText('Recorded event 9')).toBeTruthy();
});


test('Overview has compact closure requirements and omits unrecorded cross-pathway dependencies', () => {
 mount();
 const panel=screen.getByRole('tabpanel');
 expect(within(panel).getByText('Qualifying completion evidence')).toBeTruthy();
 expect(within(panel).getByText('Evidence-specific reviewer approval')).toBeTruthy();
 expect(within(panel).getByText('No dependencies recorded.')).toBeTruthy();
 expect(within(panel).queryByText(/Cross-pathway dependencies/)).toBeNull();
 expect(within(panel).queryByText('Recorded assessment')).toBeNull();
 expect(within(panel).queryByText('Existing earlier evidence')).toBeNull();
 fireEvent.click(screen.getByRole('tab',{name:'Evidence'}));
 expect(screen.getByText('Existing earlier evidence')).toBeTruthy();
});
