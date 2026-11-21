// @vitest-environment jsdom
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {MemoryRouter} from 'react-router-dom';
import {afterEach,expect,test,vi} from 'vitest';
import {api} from './api';
import {HistoricalCandidates,HistoricalIdentificationBadge,HistoricalDetectionTimeline,type HistoricalCandidate} from './HistoricalCandidates';
import type {Role} from './types';
vi.mock('./api',()=>({api:vi.fn()}));afterEach(()=>{cleanup();vi.resetAllMocks();});
function fixture():HistoricalCandidate{return {id:'candidate-one',patient_id:'demo-amira',title:'Early-pregnancy glycemic screening review - identified from earlier record',owner_role:'Reviewer',status:'candidate',status_label:'Candidate: needs clinician confirmation',demo_date:'2026-11-22',rule_id:'earlier-documented-finding-screening-review',rule_version:'1',clinical_confirmation:'pending clinical confirmation',eligibility_criteria:['A pregnancy transition is recorded.'],target_window:'W1',window:{id:'W1',status:'IN_WINDOW',window_start:'2026-11-08',window_end:'2026-12-01'},as_of:'2026-11-22',calculator_status:'IN_WINDOW',window_policy_id:'glycemic-assessment-pregnancy',window_policy_version:'1',obligation_id:null,decision:null,source_refs:[{id:'finding',kind:'Observation',resource_id:'demo-earlier',version:1,digest:'synthetic-digest',clinical_time:'2011-07-10',trigger:true,source_url:'/api/v1/clinical/patients/demo-amira/evidence/finding',provenance:{facility:{simulation:true,origin:'Hospital A',receiving:'Hospital B'}}}]};}
function mount(node:React.ReactNode){return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><MemoryRouter>{node}</MemoryRouter></QueryClientProvider>);}
test('candidate passport labels pending status, policy, source and calculator window',async()=>{
 vi.mocked(api).mockResolvedValue([fixture()]);mount(<HistoricalCandidates token="test" role="coordinator" patientId="demo-amira"/>);
 await screen.findByText('Candidate: needs clinician confirmation');expect(screen.getByText('Owner role:',{exact:false})).toBeTruthy();
 expect(screen.getByText(/Source date: 2011-07-10/)).toBeTruthy();expect(screen.getByText('SIMULATED · Hospital A')).toBeTruthy();
 expect(screen.getByText('Rule earlier-documented-finding-screening-review · version 1')).toBeTruthy();expect(screen.getByText('pending clinical confirmation')).toBeTruthy();
 expect(screen.queryByText('CITATION_PENDING_CLINICAL_CONFIRMATION')).toBeNull();expect(screen.queryByRole('button',{name:'Confirm historical candidate'})).toBeNull();
});
test('reviewer must supply a rationale and confirmation leaves care open',async()=>{
 const row=fixture();vi.mocked(api).mockImplementation(async(_token,path,method)=>method==='POST'?{...row,status:'confirmed',status_label:'Confirmed by clinician',obligation_id:'new-obligation'}:[row]);
 mount(<HistoricalCandidates token="test" role="reviewer" patientId="demo-amira"/>);const button=await screen.findByRole('button',{name:'Confirm historical candidate'});
 expect(button.hasAttribute('disabled')).toBe(true);fireEvent.change(screen.getByLabelText('Candidate review rationale'),{target:{value:'Cited source reviewed by synthetic clinician.'}});fireEvent.click(button);
 await screen.findByText('Candidate confirmed. A separate open obligation was created; care remains unclosed.');
 expect(api).toHaveBeenCalledWith('test','/v1/historical-candidates/candidate-one/review','POST',{decision:'confirm',rationale:'Cited source reviewed by synthetic clinician.'});
});
test('dismissal sends the required rationale through the reviewer endpoint',async()=>{
 vi.mocked(api).mockImplementation(async(_token,_path,method)=>method==='POST'?{...fixture(),status:'dismissed'}:[fixture()]);mount(<HistoricalCandidates token="test" role="reviewer" patientId="demo-amira"/>);
 fireEvent.change(await screen.findByLabelText('Candidate review rationale'),{target:{value:'Duplicate source; candidate dismissed.'}});fireEvent.click(screen.getByRole('button',{name:'Dismiss historical candidate'}));
 await screen.findByText('Candidate dismissed with an audited rationale.');expect(api).toHaveBeenCalledWith('test','/v1/historical-candidates/candidate-one/review','POST',{decision:'dismiss',rationale:'Duplicate source; candidate dismissed.'});
});
test('dashboard badge routes to a separate candidate passport',async()=>{
 vi.mocked(api).mockResolvedValue([fixture()]);mount(<HistoricalIdentificationBadge token="test"/>);expect((await screen.findByRole('link',{name:'Identified from earlier records · 1'})).getAttribute('href')).toBe('/passport?candidate=candidate-one&patient=demo-amira');
});
test('workspace timeline records detection using its stored demo date',async()=>{
 vi.mocked(api).mockResolvedValue([fixture()]);mount(<HistoricalDetectionTimeline token="test" patientId="demo-amira"/>);await screen.findByLabelText('Historical detection timeline');expect(screen.getByText(/2026-11-22 · demo-calendar detection date/)).toBeTruthy();
});
test('withdrawn candidates cannot be confirmed and show the withdrawal',async()=>{
 vi.mocked(api).mockResolvedValue([{...fixture(),status:'withdrawn',status_label:'Withdrawn: trigger evidence no longer valid'}]);mount(<HistoricalCandidates token="test" role="reviewer" patientId="demo-amira"/>);await screen.findByText('Withdrawn: trigger evidence no longer valid');expect(screen.queryByRole('button',{name:'Confirm historical candidate'})).toBeNull();
});
test('candidate source is retrieved through the authorized API',async()=>{
 vi.mocked(api).mockImplementation(async(_token,path)=>path.includes('/evidence/')?{resource:{valueString:'documented PCOS diagnosis'}}:[fixture()]);mount(<HistoricalCandidates token="test" role="reviewer" patientId="demo-amira"/>);
 fireEvent.click(await screen.findByRole('link',{name:'Open candidate source'}));await screen.findByText(/documented PCOS diagnosis/);expect(api).toHaveBeenCalledWith('test','/v1/clinical/patients/demo-amira/evidence/finding');
});
test('review rejection remains visible without inventing a successful confirmation',async()=>{
 vi.mocked(api).mockImplementation(async(_token,_path,method)=>{if(method==='POST')throw Error('Trigger evidence changed');return [fixture()];});mount(<HistoricalCandidates token="test" role="reviewer" patientId="demo-amira"/>);
 fireEvent.change(await screen.findByLabelText('Candidate review rationale'),{target:{value:'Reviewing source.'}});fireEvent.click(screen.getByRole('button',{name:'Confirm historical candidate'}));await screen.findByRole('alert');expect(screen.queryByText(/Candidate confirmed. A separate/)).toBeNull();
});


import {DemoClock} from './Tsp';
test('candidate window refreshes from the server after changing the demo clock',async()=>{
 let date='2026-11-22';
 vi.mocked(api).mockImplementation(async(_token,path,method,body)=>{
   if(path==='/v1/tsp/clock'){if(method==='POST')date=(body as {as_of:string}).as_of;return {demo_mode:true,as_of:date,timezone:'Asia/Dubai',label:'demo'};}
   return [{...fixture(),as_of:date}];
 });
 mount(<><DemoClock token="test" role="coordinator" controls/><HistoricalCandidates token="test" role="coordinator" patientId="demo-amira"/></>);
 await screen.findByText('Calculator window: W1');fireEvent.change(screen.getByLabelText('Demo as-of date'),{target:{value:'2026-11-25'}});fireEvent.click(screen.getByRole('button',{name:'Apply demo date'}));
 await screen.findByText(/as of 2026-11-25/);
});
test('changing patient clears an opened candidate source viewer',async()=>{
 vi.mocked(api).mockImplementation(async(_token,path)=>path.includes('/evidence/')?{resource:{valueString:'Prior patient source content'}}:path.includes('demo-lina')?[]:[fixture()]);
 const client=new QueryClient({defaultOptions:{queries:{retry:false}}});
 const content=(id:string)=><QueryClientProvider client={client}><MemoryRouter><HistoricalCandidates token="test" role="coordinator" patientId={id}/></MemoryRouter></QueryClientProvider>;
 const view=render(content('demo-amira'));fireEvent.click(await screen.findByRole('link',{name:'Open candidate source'}));await screen.findByText(/Prior patient source content/);
 view.rerender(content('demo-lina'));await waitFor(()=>expect(screen.queryByLabelText('Historical trigger source viewer')).toBeNull());expect(screen.queryByText(/Prior patient source content/)).toBeNull();
});


test('source investigation is explicit, attested and uses the existing grounded history endpoint',async()=>{
 vi.mocked(api).mockImplementation(async(_token,path,method)=>path.endsWith('/status')?{available:true,status:'available',configuration:{model:'configured-model'}}:method==='POST'?{id:'recorded-run',detail:{configuration:{model:'configured-model'},error:null,duration_ms:20,trace:['retrieve'],usage:{model_calls:1,input_tokens:10,output_tokens:5},tool_history:[{name:'get_patient_clinical_context',status:'ok'}],packet:{summary:'Quoted synthetic source.',grounding_status:'partially_grounded',abstained:false,findings:[]}}}:[fixture()]);
 mount(<HistoricalCandidates token="test" role="coordinator" patientId="demo-amira"/>);
 const button=await screen.findByRole('button',{name:'Investigate cited earlier evidence'});expect(button.hasAttribute('disabled')).toBe(true);
 fireEvent.click(screen.getByLabelText('This earlier-source request contains synthetic data only.'));fireEvent.click(button);await screen.findByText('Quoted synthetic source.');
 const call=vi.mocked(api).mock.calls.find(entry=>entry[2]==='POST');expect(call?.[1]).toBe('/v1/history-handoff/patients/demo-amira/investigations');
 expect(screen.getByText('Candidate: needs clinician confirmation')).toBeTruthy();
});
test('unavailable agent has no silent fallback and cannot run',async()=>{
 vi.mocked(api).mockImplementation(async(_token,path)=>path.endsWith('/status')?{available:false,status:'disabled'}:[fixture()]);mount(<HistoricalCandidates token="test" role="coordinator" patientId="demo-amira"/>);
 await screen.findByText(/Investigation provider is unavailable: disabled/);expect(screen.getByRole('button',{name:'Investigate cited earlier evidence'}).hasAttribute('disabled')).toBe(true);
});


import {AuditScreen} from './screens';
import type {Snapshot} from './types';
test('candidate audit renders the stored relevance rule version and demo date',async()=>{
 vi.mocked(api).mockResolvedValue([]);
 const data={patients:[],clinical_obligations:[],clinical_evidence:[],life_stage_events:[],rule_versions:[],obligation_dependencies:[],agent_executions:[],care_coordination_tasks:[],clinical_approvals:[],closure_evidence:[],demo_run_archive:[],audit_events:[{sequence:1,recorded:'2026-11-21T11:00:00Z',actor:'coordinator',action:'historical_candidate_identified',patient_id:'demo-amira',obligation_id:null,rule_key:'',evidence_refs:[],detail:{candidate_title:'Synthetic earlier-record review',demo_date:'2026-11-22',relevance_rule_id:'earlier-documented-finding-screening-review',relevance_rule_version:'1'}}]} as Snapshot;
 mount(<AuditScreen data={data} token="test" role="viewer" busy={false} action={vi.fn()}/>);
 expect(screen.getByText('earlier-documented-finding-screening-review version 1')).toBeTruthy();
 expect(screen.getByText(/2026-11-22 · demo calendar/)).toBeTruthy();
});
