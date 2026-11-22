// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, test, vi } from 'vitest';
import { api } from './api';
import { PreventionQueue, PreventionPassport, DecisionTimeline, type PreventionDecision } from './Prevention';

vi.mock('./api', () => ({ api: vi.fn() }));
afterEach(() => { cleanup(); vi.resetAllMocks(); });

function fixture(): PreventionDecision {
  return { id: 'decision-test', patient_id: 'demo-amira', obligation_id: 'obligation-test',
    rationale: 'Review the synthetic metabolic assessment.', owner: 'Synthetic care team', rule_key: 'illustrative@1',
    status: 'ready_for_review', revision: 1, archived: false, snapshot_hash: 'a'.repeat(64),
    created: '2026-11-19T10:00:00Z', source_refs: ['source-1'], last_investigation_id: null, record_snapshot_current: true,
    timing: { state: 'not_established', label: 'Timing not established.', due_at: null, reason: 'no_policy' }, timing_policy: null,
    prerequisites: [{ id: 'prerequisite-1', category: 'Assessment summary document', status: 'available_for_review',
      source_refs: ['source-1'], issues: [], evaluated: '2026-11-19T10:00:00Z', rule_key: 'illustrative@1' }],
    snapshot: { evidence: [{ id: 'source-1', quality: { state: 'valid' } }],
      life_stage_events: [['stage-1', 'preconception', '2026-11-19T09:00:00Z']] }, record: null };
}

function mount(element: React.ReactNode, entry = '/') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[entry]}>{element}</MemoryRouter></QueryClientProvider>);
}

test('queue displays backend counts and a patient decision link', async () => {
  vi.mocked(api).mockResolvedValue({ decisions: [fixture()], history: [],
    counts: { awaiting_evidence: 7, ready_for_review: 2, due_soon: 3, overdue: 1 } });
  mount(<PreventionQueue token="test" role="viewer" />);
  await screen.findByText('7');
  expect(screen.getByRole('link').getAttribute('href')).toContain('obligation-test');
  expect(screen.queryByRole('button', { name: 'Load illustrative timing scenario' })).toBeNull();
});

test('reviewer explicitly reviews and records the current snapshot', async () => {
  let decision = fixture();
  vi.mocked(api).mockImplementation(async (_token, path, method) => {
    if (method === 'POST') {
      decision = { ...decision, status: path.endsWith('/transition') ? 'under_review' : 'decided', revision: decision.revision + 1 };
      return decision;
    }
    return { decisions: [decision], history: [], counts: {} };
  });
  mount(<PreventionPassport token="test" role="reviewer" obligationId="obligation-test" />);
  await screen.findByText('Synthetic care team');
  fireEvent.change(screen.getByLabelText('Clinical decision rationale'), { target: { value: 'Source documents need clinical reconciliation.' } });
  fireEvent.click(screen.getByRole('button', { name: 'Begin clinician review' }));
  await screen.findByRole('button', { name: 'Record clinical decision' });
  fireEvent.change(screen.getByLabelText('Outstanding follow-up actions, one per line'), { target: { value: 'Obtain reconciliation.' } });
  fireEvent.click(screen.getByRole('checkbox', { name: 'I reviewed the current evidence snapshot and take responsibility for this decision.' }));
  fireEvent.click(screen.getByRole('button', { name: 'Record clinical decision' }));
  await waitFor(() => expect(vi.mocked(api).mock.calls.some((call) => call[1].endsWith('/record') &&
    (call[3] as { reviewed_snapshot: string }).reviewed_snapshot === 'a'.repeat(64))).toBe(true));
});

test('timeline shows persisted life-stage context and no invented due date', async () => {
  vi.mocked(api).mockResolvedValue({ decisions: [fixture()], history: [], counts: {} });
  mount(<DecisionTimeline token="test" patientId="demo-amira" />);
  await screen.findByText('Preconception life-stage event');
  expect(screen.getByText(/Timing not established/)).toBeTruthy();
  expect(screen.getByText('Decision created')).toBeTruthy();
});


test('passport honors the selected decision in a queue link', async () => {
  const second = { ...fixture(), id: 'decision-second', owner: 'Selected care team' };
  vi.mocked(api).mockResolvedValue({ decisions: [fixture(), second], history: [], counts: {} });
  mount(<PreventionPassport token="test" role="viewer" obligationId="obligation-test" />,
    '/passport?obligation=obligation-test&decision=decision-second');
  await screen.findByText('Selected care team');
  expect(screen.queryByText('Synthetic care team')).toBeNull();
});


test('Passport empty decision is a compact line without a large empty panel',async()=>{
 vi.mocked(api).mockResolvedValue({decisions:[],history:[],counts:{}});
 mount(<PreventionPassport token="test" role="viewer" obligationId="obligation-test" passport/>);
 const empty=await screen.findByText('No prevention decision is linked to this obligation.');
 expect(empty.tagName).toBe('P');expect(empty.className).toBe('passport-decision-empty');
});

test('Passport decision keeps status owner readiness link and coordinator reasons directly accessible',async()=>{
 vi.mocked(api).mockResolvedValue({decisions:[fixture()],history:[],counts:{}});
 mount(<PreventionPassport token="test" role="coordinator" obligationId="obligation-test" passport/>);
 await screen.findByText('Synthetic care team',{selector:'.passport-decision-summary strong'});
 expect(screen.getByRole('link',{name:'Open decision readiness investigation'}).getAttribute('href')).toBe('/resolution?obligation=obligation-test&decision=decision-test');
 expect(screen.getAllByRole('link',{name:'Open decision readiness investigation'})).toHaveLength(1);
 expect(screen.getByLabelText('Escalation or cancellation reason').closest('details')).toBeNull();
 expect(screen.getByRole('button',{name:'Escalate decision'})).toBeTruthy();
 expect(screen.getByRole('button',{name:'Cancel decision'})).toBeTruthy();
});
