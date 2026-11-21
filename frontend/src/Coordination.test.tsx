// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, expect, test, vi } from 'vitest';
import { api } from './api';
import { CoordinationNextAction } from './Coordination';
vi.mock('./api', () => ({ api: vi.fn() }));
afterEach(() => { cleanup(); vi.resetAllMocks(); });
function mount() { render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><CoordinationNextAction token="test" patientId="demo-amira"/></QueryClientProvider>); }
test('next action renders server mapping and responsible coordination role', async () => {
  vi.mocked(api).mockResolvedValue({ status:'DUE_SOON', as_of:'2026-11-22', coordination:{action:'Schedule assessment',owner_role:'Coordinator'} });
  mount(); await screen.findByText('Schedule assessment (Coordinator)');
  expect(screen.getByText(/No automatic action or owner change/)).toBeTruthy();
  expect(api).toHaveBeenCalledWith('test','/v1/tsp/patients/demo-amira/coordination');
});
test('completed state has no action', async () => {
  vi.mocked(api).mockResolvedValue({status:'COMPLETED_LATE',as_of:'2026-11-22',coordination:{action:null,owner_role:null}});
  mount(); await screen.findByText('None — no coordination action specified for this state.');
});
