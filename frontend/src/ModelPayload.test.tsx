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

test('legacy malformed manifest cannot blank the app or alter the exact payload',async()=>{
 vi.mocked(api).mockImplementation(async(_token,path)=>path.includes('/patients/')?[{id:'legacy'}]:{detail:{original_capture_available:true,context_manifest:{records:[{record:{type:'string'},fields:['reference','excerpt']}]},request_payload:{actual:'unchanged'},raw_response:{id:'original'},redactions:[],redaction_label:'None applied'}});
 mount();fireEvent.click(screen.getByRole('tab',{name:'Model payload'}));await screen.findByLabelText('Captured request payload');
 expect(screen.getByText(/Unrecognized legacy manifest entry/)).toBeTruthy();expect(screen.getByLabelText('Captured request payload').textContent).toContain('unchanged');
});

test('copy request uses only the exact persisted body and legacy captures offer no copy', async()=>{
 const writeText=vi.fn().mockResolvedValue(undefined);
 Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText}});
 vi.mocked(api).mockImplementation(async(_token,path)=>path.includes('/patients/')?[{id:'capture'}]:{detail:{original_capture_available:true,context_manifest:{},request_payload:{actual:'[REDACTED]'},raw_response:{id:'original'},redactions:[],redaction_label:'Existing mandatory secret scrub applied'}});
 mount();fireEvent.click(screen.getByRole('tab',{name:'Model payload'}));
 fireEvent.click(await screen.findByRole('button',{name:'Copy request'}));
 await screen.findByText('Request copied.');
 expect(writeText).toHaveBeenCalledWith(JSON.stringify({actual:'[REDACTED]'},null,2));
 cleanup();vi.mocked(api).mockImplementation(async(_token,path)=>path.includes('/patients/')?[{id:'legacy'}]:{detail:{original_capture_available:false,context_manifest:{},redactions:[],redaction_label:'Unknown: original payload not recorded'}});
 mount();fireEvent.click(screen.getByRole('tab',{name:'Model payload'}));
 await screen.findByText(/Original payload unavailable for this recorded run/);
 expect(screen.queryByRole('button',{name:'Copy request'})).toBeNull();
 expect(screen.queryByLabelText('Captured request payload')).toBeNull();
});
