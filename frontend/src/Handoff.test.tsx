// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, test, vi } from 'vitest';
import { api } from './api';
import { FacilityChips, HandoffPanel, HandoffTimeline, HandoffSetup, type HandoffState } from './Handoff';
vi.mock('./api', () => ({ api: vi.fn() }));
afterEach(() => { cleanup(); vi.resetAllMocks(); });
function mount(element: React.ReactNode) { render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })}><MemoryRouter>{element}</MemoryRouter></QueryClientProvider>); }
const state: HandoffState = { simulation: true, patient_id: 'demo-handoff', stage: 'pregnancy', obligation_id: 'obligation-test', obligation_status: 'open',
  responsible_team: 'Hospital B — SIMULATED receiving care team', original_owner: 'Hospital A — SIMULATED originating care team', origin: 'Hospital A', receiving: 'Hospital B', received: true,
  received_at: '2026-11-19T22:00:00+00:00', owner_history: [{ recorded: '2026-11-19T22:00:00+00:00', previous_owner: 'Hospital A', owner: 'Hospital B', simulation: true }] };
test('chips disclose simulation and the Dubai receipt date', () => { mount(<FacilityChips facility={{ simulation: true, origin: 'Hospital A', receiving: 'Hospital B', received_at: state.received_at }} />);
  expect(screen.getByText('SIMULATED · Hospital A')).toBeTruthy(); expect(screen.getByText(/Origin: Hospital A, received 2026-11-20/)).toBeTruthy(); });
test('viewer sees owner history without exchange controls', async () => { vi.mocked(api).mockResolvedValue(state); mount(<HandoffPanel token="test" role="viewer" patientId="demo-handoff" />);
  await screen.findByText(state.responsible_team); expect(screen.getByText(state.original_owner)).toBeTruthy(); expect(screen.queryByRole('button')).toBeNull(); });
test('receiving is disabled until pregnancy registration', async () => { vi.mocked(api).mockResolvedValue({ ...state, stage: 'preconception', received: false }); mount(<HandoffPanel token="test" role="coordinator" patientId="demo-handoff" />);
  const button=await screen.findByRole('button',{name:'Receive records from Hospital A'}); expect((button as HTMLButtonElement).disabled).toBe(true); });
test('coordinator sends the explicit receive action', async () => { vi.mocked(api).mockResolvedValue(state); mount(<HandoffPanel token="test" role="coordinator" patientId="demo-handoff" />);
  fireEvent.click(await screen.findByRole('button',{name:'Receive records from Hospital A'})); await waitFor(()=>expect(api).toHaveBeenCalledWith('test','/v1/simulated-handoff/patients/demo-handoff/receive','POST')); });
test('timeline preserves both facility labels and received origin', async () => { vi.mocked(api).mockResolvedValue(state); mount(<HandoffTimeline token="test" patientId="demo-handoff" />);
  await screen.findByText('Unresolved obligation surfaced in the receiving view'); expect(screen.getAllByText('SIMULATED · Hospital A').length).toBe(2); });
test('setup labels the local simulation and invokes only the synthetic seed', async () => { vi.mocked(api).mockResolvedValue(state); mount(<HandoffSetup token="test" role="coordinator" available={false} />);
  fireEvent.click(screen.getByRole('button',{name:'Load simulated handoff demo'})); await screen.findByRole('link',{name:'Open simulated handoff workspace'}); expect(api).toHaveBeenCalledWith('test','/v1/simulated-handoff/demo/seed','POST'); });
