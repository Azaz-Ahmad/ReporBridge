// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, expect, test, vi } from 'vitest';
import { api } from './api';
import { MultiAgent } from './MultiAgent';
vi.mock('./api', () => ({ api: vi.fn() }));
afterEach(() => { cleanup(); vi.resetAllMocks(); });
const agent = { agent_id: 'A03', state: 'completed', task_objective: 'Clinical Context', findings: [],
  uncertainty: [], error: null, validation_status: 'partially_grounded', model_identifier: 'configured-model',
  execution_metadata: { duration_ms: 12, response_id: 'actual-response', reported_model: 'reported-model' },
  validated_output: { timeline_events: [] } };
const run = { id: 'multi-1', created: '2026-11-19', status: 'pending_review', review: null, detail: {
  workflow: 'multi_agent', decision_context: { decision_id: 'decision-1' }, question: 'Authorized synthetic objective',
  error: null, duration_ms: 45, configuration: { model: 'configured-model' }, trace: ['supervisor_planning', 'A03.completed'],
  usage: { model_calls: 3, input_tokens: 200, output_tokens: 100, usage_complete: true }, tool_history: [],
  multi_agent: { agents: { A01: { ...agent, agent_id: 'A01' }, A02: { ...agent, state: 'not_selected' }, A03: agent,
    A04: { ...agent, agent_id: 'A04', state: 'failed', error: 'provider_timeout', validated_output: null } }, routing: [] },
  packet: { summary: 'Persisted unified packet', packet_complete: false, abstained: true, grounding_status: 'insufficient_evidence',
    requires_human_review: true, findings: [], missing_information: ['Assessment summary missing'], conflicting_evidence: [],
    uncertainty: [], administrative_follow_up_proposals: ['Request documentation'],
    timing: { label: 'Timing not established.', due_at: null }, timing_policy: null, prerequisites: [], source_references: [] } } };
function mount(role: 'coordinator' | 'reviewer' = 'coordinator') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(<QueryClientProvider client={client}><MultiAgent token="test" patientId="demo-amira" role={role} decisionId="decision-1" /></QueryClientProvider>);
}
function mockRuns(items: unknown[]) {
  vi.mocked(api).mockImplementation(async (_token, path) => path.endsWith('/status')
    ? { available: true, status: 'available', configuration: { model: 'configured-model' } } : items);
}
test('starts only an attested backend-scoped investigation with a linked decision', async () => {
  mockRuns([]); mount();
  await screen.findByText(/configured-model/);
  const button = screen.getByRole('button', { name: 'Run Multi-Agent Investigation' }) as HTMLButtonElement;
  expect(button.disabled).toBe(true);
  fireEvent.click(screen.getByRole('checkbox'));
  vi.mocked(api).mockImplementation(async (_token, path, method) => method === 'POST' ? run
    : path.endsWith('/status') ? { available: true, status: 'available', configuration: { model: 'configured-model' } } : [run]);
  fireEvent.click(button);
  await screen.findByText('Persisted unified packet');
  await waitFor(() => expect(vi.mocked(api).mock.calls.some(c => c[1].endsWith('/runs/multi-agent') && (c[3] as { decision_id?: string }).decision_id === 'decision-1')).toBe(true));
});
test('shows actual failed and skipped specialists and marks the unified packet partial', async () => {
  mockRuns([run]); mount();
  await screen.findByText('Partial packet — required output unavailable', { exact: false });
  expect(screen.getByText('Not selected')).toBeTruthy();
  expect(screen.getByText('Failed')).toBeTruthy();
  expect(screen.getByText('Timing not established.')).toBeTruthy();
  expect(screen.getByText('Assessment summary missing')).toBeTruthy();
});
test('prevents approval of partial packets and permits a reviewer evidence request', async () => {
  mockRuns([run]); mount('reviewer');
  await screen.findByText('Persisted unified packet');
  fireEvent.change(screen.getByLabelText('Multi-agent summary review note'), { target: { value: 'Obtain source documentation.' } });
  expect((screen.getByRole('button', { name: 'Approve summary' }) as HTMLButtonElement).disabled).toBe(true);
  vi.mocked(api).mockResolvedValue(run);
  fireEvent.click(screen.getByRole('button', { name: 'Request evidence' }));
  await waitFor(() => expect(vi.mocked(api).mock.calls.some(c => c[1] === '/v1/agents/clinical-evidence/runs/multi-1/review' && (c[3] as { decision?: string }).decision === 'request_evidence')).toBe(true));
});
test('provider failure stays visible without fabricated specialist results', async () => {
  vi.mocked(api).mockRejectedValue(new Error('Backend unavailable'));
  mount();
  await screen.findAllByText('Backend unavailable');
  expect(screen.queryByTestId('multi-run')).toBeNull();
});
