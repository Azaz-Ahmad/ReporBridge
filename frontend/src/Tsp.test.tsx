// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, test, vi } from 'vitest';
import { api } from './api';
import { DemoClock, TspQueue, TspWindow, type WindowResult } from './Tsp';
vi.mock('./api', () => ({ api: vi.fn() }));
afterEach(() => { cleanup(); vi.resetAllMocks(); });
function mount(element: React.ReactNode) { render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter>{element}</MemoryRouter></QueryClientProvider>); }
const clock = { demo_mode: true, as_of: '2026-11-22', label: 'demo', timezone: 'Asia/Dubai' };
function fixture(): WindowResult { return { patient_id: 'demo-amira', status: 'HOLD_DATING_UNCERTAIN', as_of: clock.as_of,
  policy_id: 'glycemic-assessment-pregnancy', policy_version: '1', citation: 'CITATION_PENDING_CLINICAL_CONFIRMATION', clinical_confirmation: 'pending clinical confirmation',
  window_start: null, window_end: null, windows: [], clock, inputs_used: [], missing_evidence: ['Pregnancy dating evidence'],
  reviewer_questions: ['Review dating'], obligation_ids: ['obligation-1'], completion_verified: false }; }
test('passport holds dates and discloses policy and missing evidence', async () => { vi.mocked(api).mockResolvedValue(fixture()); mount(<TspWindow token="test" patientId="demo-amira" />);
  await screen.findByText('No established window'); expect(screen.getByText('CITATION_PENDING_CLINICAL_CONFIRMATION')).toBeTruthy(); expect(screen.getByText('Pregnancy dating evidence')).toBeTruthy(); expect(screen.getByText('pending clinical confirmation')).toBeTruthy(); });
test('queue links the scoped obligation and renders status', async () => { vi.mocked(api).mockResolvedValue([fixture()]); mount(<TspQueue token="test" />);
  await screen.findByText('HOLD DATING UNCERTAIN'); expect(screen.getByRole('link').getAttribute('href')).toBe('/passport?obligation=obligation-1'); });
test('clock updates only by explicit coordinator submission', async () => { vi.mocked(api).mockResolvedValue(clock); mount(<DemoClock token="test" role="coordinator" />);
  await screen.findByText('DEMO CLOCK — synthetic dates'); fireEvent.change(screen.getByLabelText('Demo as-of date'), { target: { value: '2027-01-01' } }); fireEvent.click(screen.getByRole('button', { name: 'Apply demo date' }));
  await waitFor(() => expect(api).toHaveBeenCalledWith('test', '/v1/tsp/clock', 'POST', { as_of: '2027-01-01' })); });
test('viewer sees a clock banner without mutation controls', async () => { vi.mocked(api).mockResolvedValue(clock); mount(<DemoClock token="test" role="viewer" />);
  await screen.findByText('DEMO CLOCK — synthetic dates'); expect(screen.queryByRole('button')).toBeNull(); });
test('disabled demo mode hides the clock controls', async () => { vi.mocked(api).mockResolvedValue({ ...clock, demo_mode: false }); mount(<DemoClock token="test" role="coordinator" />);
  await waitFor(() => expect(api).toHaveBeenCalled()); expect(screen.queryByLabelText('Demo clock banner')).toBeNull(); });


test('TSP reset requires separate confirmation and cancellation does not reset', async()=>{
 vi.mocked(api).mockImplementation(async(_token,path)=>path.endsWith('/clock')?clock:[]);
 mount(<TspQueue token="test" role="coordinator"/>);
 fireEvent.click(await screen.findByRole('button',{name:'Reset TSP demo'}));
 expect(vi.mocked(api).mock.calls.some(c=>c[1].endsWith('/demo/reset'))).toBe(false);
 fireEvent.click(screen.getByRole('button',{name:'Cancel reset'}));
 expect(screen.queryByRole('button',{name:'Confirm reset TSP demo'})).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'Reset TSP demo'}));
 fireEvent.click(screen.getByRole('button',{name:'Confirm reset TSP demo'}));
 await waitFor(()=>expect(api).toHaveBeenCalledWith('test','/v1/tsp/demo/reset','POST'));
});

import {qualityWarning} from './ClinicalExplorer';
test('synthetic date warning is explanatory while the raw non-demo warning is retained',()=>{
 expect(qualityWarning('timestamp_after_receipt',true)).toBe('Synthetic source date follows import time; inspect the source date.');
 expect(qualityWarning('timestamp_after_receipt',false)).toBe('Timestamp after receipt');
 expect(qualityWarning('unknown_terminology',true)).toBe('Unknown terminology');
});


test('window explanation displays actual provider or replay failure',async()=>{
 vi.mocked(api).mockImplementation(async(_token,path)=>path.endsWith('/investigations')?{id:'failed',detail:{packet:null,error:'configured_model_rejected: check OPENAI_MODEL'}}:fixture());
 mount(<TspWindow token="test" patientId="demo-amira" role="coordinator"/>);
 fireEvent.click(screen.getByRole('button',{name:'Explain computed window'}));
 expect((await screen.findByRole('alert')).textContent).toContain('configured_model_rejected: check OPENAI_MODEL');
});
