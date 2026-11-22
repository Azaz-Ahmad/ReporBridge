// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, test, vi } from 'vitest';
import { Workspace } from './Workspace';
import type { Role, Snapshot } from './types';

// Isolate the presentation shell; existing component suites cover their real queries and mutations.
vi.mock('./Jury', () => ({ JourneyStrip: ({ actions }: { actions?: import('react').ReactNode }) => <><span>Existing calculator summary</span>{actions}</> }));
vi.mock('./Tsp', () => ({ TspWindow: () => <section aria-label="Existing prevention windows" /> }));
vi.mock('./History', () => ({ EarlierRecords: ({ patientId, currentCare }: { patientId: string; currentCare?: import('react').ReactNode }) => patientId === 'demo-amira' ? <section aria-label="Existing earlier sources">{currentCare}</section> : null }));
vi.mock('./HistoricalCandidates', () => ({ HistoricalCandidates: () => <section aria-label="Existing reviewer controls" />, HistoricalDetectionTimeline: () => null }));
vi.mock('./Handoff', () => ({ HandoffPanel: () => null, HandoffTimeline: () => null }));
vi.mock('./Prevention', () => ({ DecisionTimeline: () => null }));
vi.mock('./ClinicalExplorer', () => ({ ClinicalExplorer: () => <details><summary>Clinical evidence explorer</summary></details> }));
afterEach(cleanup);

const data: Snapshot = {
  patients: [{ id: 'demo-amira', stage: 'preconception', resource: { resourceType: 'Patient', id: 'demo-amira', name: [{ given: ['Amira'], family: 'Haddad' }], birthDate: '1995-04-12' } },
    { id: 'demo-other', stage: 'pregnancy', resource: { resourceType: 'Patient', id: 'demo-other', name: [{ given: ['Noor'], family: 'Demo' }] } }],
  clinical_obligations: [{ id: 'prior', patient_id: 'demo-amira', rule_key: 'pre', source_id: 'demo-source', owner: 'Demo coordinator', status: 'open', created: '2026-11-22' },
    { id: 'later', patient_id: 'demo-amira', rule_key: 'preg', source_id: 'demo-pregnancy', owner: 'Demo coordinator', status: 'open', created: '2026-11-22' }],
  rule_versions: [{ id: 'pre', rule_id: 'pre', version: '1', pathway_id: 'preconception', definition: { title: 'Preconception review', description: 'Recorded assessment', trigger: 'flag', closure: 'reconciled', source: 'pending clinical confirmation' } },
    { id: 'preg', rule_id: 'preg', version: '1', pathway_id: 'pregnancy', definition: { title: 'Pregnancy handoff review', description: 'Recorded handoff', trigger: 'registration', closure: 'handoff', source: 'pending clinical confirmation' } }],
  clinical_evidence: [{ id: 'demo-source', patient_id: 'demo-amira', resource: { resourceType: 'Observation', id: 'demo-source', code: { text: 'Recorded finding' }, valueString: 'outstanding', status: 'final' } }],
  obligation_dependencies: [], life_stage_events: [], agent_executions: [], care_coordination_tasks: [], clinical_approvals: [], closure_evidence: [], audit_events: [], demo_run_archive: [],
};
function mount(role: Role = 'coordinator', snapshot = data, entry = '/workspace?patient=demo-amira') {
  const action = vi.fn();
  const view = render(<MemoryRouter initialEntries={[entry]}><Workspace data={snapshot} role={role} token="test" busy={false} action={action} /></MemoryRouter>);
  return { action, ...view };
}

test('coordinator actions keep their existing endpoints and patient selection uses the URL', () => {
  const { action } = mount();
  fireEvent.click(screen.getByRole('button', { name: 'Evaluate rules' }));
  expect(action).toHaveBeenCalledWith('/patients/demo-amira/evaluate', 'Applicable rules evaluated.');
  fireEvent.click(screen.getByRole('button', { name: 'Register pregnancy' }));
  expect(action).toHaveBeenCalledWith('/patients/demo-amira/pregnancy', 'Pregnancy registered. Existing obligations were retained.');
  fireEvent.change(screen.getByRole('combobox', { name: 'Patient' }), { target: { value: 'demo-other' } });
  expect(screen.getByRole('heading', { name: 'Noor Demo' })).toBeTruthy();
  expect(screen.queryByRole('button', { name: 'Register pregnancy' })).toBeNull();
  expect(screen.queryByText('Recorded finding')).toBeNull();
});

test('dependency arrows require actual backend relationships; Passport destinations are retained', () => {
  const view = mount();
  expect(view.container.querySelector('.workspace-dependency-arrow')).toBeNull();
  expect(screen.getByRole('link', { name: 'Preconception review' }).getAttribute('href')).toBe('/passport?obligation=prior');
  cleanup();
  const connected = mount('viewer', { ...data, obligation_dependencies: [{ id: 'edge', obligation_id: 'later', depends_on: 'prior', rule_key: 'preg', kind: 'requires_verified_closure' }] });
  expect(connected.container.querySelectorAll('.workspace-dependency-arrow')).toHaveLength(1);
  expect(screen.getByText('Depends on completion')).toBeTruthy();
  expect(screen.queryByRole('button', { name: 'Evaluate rules' })).toBeNull();
  expect(screen.queryByRole('button', { name: 'Register pregnancy' })).toBeNull();
});

test('technical details retain the full evidence table and dependency anchors open their disclosures', () => {
  const { container } = mount('viewer', data, '/workspace?patient=demo-amira#dependencies');
  expect((container.querySelector('.workspace-more') as HTMLDetailsElement).open).toBe(true);
  expect((container.querySelector('#dependencies')?.parentElement as HTMLDetailsElement).open).toBe(true);
  expect(screen.getByRole('table')).toBeTruthy();
  expect(screen.getByRole('cell', { name: 'Recorded finding' })).toBeTruthy();
  expect(screen.getByText('Planned')).toBeTruthy();
  expect(screen.getByLabelText('Existing reviewer controls')).toBeTruthy();
});

test('an unavailable patient keeps the existing empty state and exposes no clinical actions', () => {
  mount('coordinator', data, '/workspace?patient=demo-unavailable');
  expect(screen.getByText(/This patient is unavailable/)).toBeTruthy();
  expect(screen.getByRole('link', { name: 'Open population dashboard' }).getAttribute('href')).toBe('/');
  expect(screen.queryByRole('button', { name: 'Evaluate rules' })).toBeNull();
});

test('Sara sees only her stored evidence and no invented exchange or dependency', () => {
  const sara = { id: 'demo-sara', stage: 'pregnancy', resource: { resourceType: 'Patient', id: 'demo-sara', name: [{ given: ['Sara'], family: 'Ali' }], birthDate: '1995-04-12' } };
  const { container } = mount('viewer', { ...data, patients: [...data.patients, sara], clinical_evidence: [...data.clinical_evidence,
    { id: 'sara-record', patient_id: sara.id, resource: { resourceType: 'Observation', id: 'sara-record', code: { text: 'Selected patient source' }, valueString: 'Documented', status: 'final' } }] }, '/workspace?patient=demo-sara');
  expect(screen.getByRole('heading', { name: 'Sara Ali' })).toBeTruthy();
  expect(within(screen.getByLabelText('Evidence explorer')).getByText('Selected patient source')).toBeTruthy();
  expect(screen.queryByText('Recorded finding')).toBeNull();
  expect(container.querySelector('.workspace-dependency-arrow')).toBeNull();
  expect(container.querySelector('.workspace-exchange-arrow')).toBeNull();
  expect(screen.queryByText(/SIMULATED EXCHANGE/)).toBeNull();
  expect(screen.getByRole('link', { name: 'Read source documents' }).getAttribute('href')).toContain('patient=demo-sara');
});
