// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, expect, test, vi } from 'vitest';
import { ClinicalInvestigation } from './ClinicalInvestigation';
import { api } from './api';

vi.mock('./api', () => ({ api: vi.fn() }));
afterEach(() => { cleanup(); vi.resetAllMocks(); });

function mount(role: 'coordinator' | 'reviewer' = 'coordinator') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(<QueryClientProvider client={client}><ClinicalInvestigation token="test-token" patientId="demo-amira" role={role} /></QueryClientProvider>);
}

test('unconfigured provider disables execution and shows its real status', async () => {
  vi.mocked(api).mockImplementation(async (_token, path) => path.endsWith('/status')
    ? { status: 'missing_api_key', available: false, configuration: { model: 'gpt-4.1-mini' } } : []);
  mount();
  await screen.findByText(/Provider status is missing api key/);
  expect((screen.getByRole('button', { name: 'Run Investigation' }) as HTMLButtonElement).disabled).toBe(true);
  expect(api).toHaveBeenCalledTimes(2);
});

test('runs a real endpoint request and displays persisted model findings', async () => {
  const run = { id: 'run-1', status: 'awaiting_submission', created: '2026-11-18', review: null,
    detail: { question: 'Synthetic clinical question', configuration: { model: 'test-model' }, duration_ms: 35,
      trace: ['investigate', 'authorized_tools'], tool_history: [], error: null,
      usage: { model_calls: 2, input_tokens: 20, output_tokens: 30, retries: 0 },
      packet: { origin: 'model', summary: 'Persisted source summary', grounding_status: 'partially_grounded',
        abstained: false, findings: [], missing_information: [], conflicting_evidence: [], uncertainty: [],
        recommended_review_actions: [], source_references: [] } } };
  let created = false;
  vi.mocked(api).mockImplementation(async (_token, path, method) => {
    if (path.endsWith('/status')) return { status: 'available', available: true, configuration: { model: 'test-model' } };
    if (method === 'POST') { created = true; return run; }
    return created ? [run] : [];
  });
  mount();
  await screen.findByText('Available');
  fireEvent.click(screen.getByRole('checkbox'));
  fireEvent.click(screen.getByRole('button', { name: 'Run Investigation' }));
  await screen.findByText('Persisted source summary');
  await waitFor(() => expect(vi.mocked(api).mock.calls.some((call) =>
    call[1] === '/v1/agents/clinical-evidence/runs' && call[2] === 'POST')).toBe(true));
  expect(screen.getByRole('button', { name: 'Submit for Human Review' })).toBeTruthy();
});

test('provider error remains visible without a fabricated run', async () => {
  vi.mocked(api).mockRejectedValue(new Error('Backend unavailable'));
  mount('reviewer');
  await screen.findAllByText('Backend unavailable');
  expect(screen.queryByRole('button', { name: 'Run Investigation' })).toBeNull();
  expect(screen.queryByText('Model-generated draft')).toBeNull();
});
