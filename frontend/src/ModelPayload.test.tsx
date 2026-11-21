// @vitest-environment jsdom
import {cleanup,render,screen,fireEvent} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {afterEach,expect,test,vi} from 'vitest';
import {ModelPayload} from './ModelPayload';import {api} from './api';
vi.mock('./api',()=>({api:vi.fn()}));afterEach(()=>{cleanup();vi.resetAllMocks();});
function mount(role:'coordinator'|'reviewer'|'viewer'='coordinator'){return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><ModelPayload token="synthetic" role={role} patientId="demo-amira"/></QueryClientProvider>);}
test('payload shows actual technical JSON, original replay and real disclosure',async()=>{
 const call={id:'capture',created:'2026-11-21',requested_model:'requested',reported_model:'reported',mode:'replay',replayed:true,usage:{input_tokens:7},latency_ms:5,original_capture_available:true};
 vi.mocked(api).mockImplementation(async(_token,path)=>path.includes('/patients/')?[call]:{detail:{...call,context_manifest:{date_of_birth_present:true},redaction_label:'None applied',redactions:[],request_payload:{citation:'CITATION_PENDING_CLINICAL_CONFIRMATION'},raw_response:{id:'actual-response'},request_truncated:false,response_truncated:false}});
 mount();fireEvent.click(screen.getByRole('tab',{name:'Model payload'}));await screen.findByLabelText('Captured request payload');
 expect(screen.getByLabelText('Captured request payload').textContent).toContain('CITATION_PENDING_CLINICAL_CONFIRMATION');expect(screen.getByText(/replayed — original recorded call/)).toBeTruthy();expect(screen.getByText('None applied')).toBeTruthy();expect(screen.getByLabelText('Captured raw response').textContent).toContain('actual-response');
});
test('Viewer never receives a payload tab or payload API query',()=>{mount('viewer');expect(screen.queryByRole('tab',{name:'Model payload'})).toBeNull();expect(api).not.toHaveBeenCalled();});
