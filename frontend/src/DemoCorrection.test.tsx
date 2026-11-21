// @vitest-environment jsdom
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {afterEach,expect,test,vi} from 'vitest';
import {MemoryRouter} from 'react-router-dom';
import {api} from './api';
import {DemoCorrection} from './DemoCorrection';
import {Lifecycle} from './showcase';
import type {Obligation,Role,Snapshot} from './types';
vi.mock('./api',()=>({api:vi.fn()}));
afterEach(()=>{cleanup();vi.resetAllMocks();});
const obligation:Obligation={id:'obligation-one',patient_id:'demo-amira',rule_key:'pre',source_id:'demo-source',owner:'Hospital B coordination',status:'closed',created:'2026-11-22'};
function mount(role:Role='coordinator',status:'closed'|'open'='closed'){
  render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><DemoCorrection token="test" role={role} obligation={{...obligation,status}} evidenceId="demo-closing" evidenceLabel="Verified synthetic assessment"/></QueryClientProvider>);
}
test('simulated correction requires explicit confirmation; cancellation sends no event',async()=>{
  vi.mocked(api).mockResolvedValue({demo_mode:true});mount();
  fireEvent.click(await screen.findByRole('button',{name:'Simulate evidence correction (demo)'}));
  expect(vi.mocked(api).mock.calls.filter(c=>c[2]==='POST')).toHaveLength(0);
  fireEvent.click(screen.getByRole('button',{name:'Cancel simulated correction'}));
  expect(screen.queryByRole('group')).toBeNull();
  expect(vi.mocked(api).mock.calls.filter(c=>c[2]==='POST')).toHaveLength(0);
});
test('confirmed correction waits for server result and reports actual owner',async()=>{
  vi.mocked(api).mockImplementation(async(_token,path)=>path==='/session'?{demo_mode:true}:{obligation_status:'open',owner:obligation.owner});mount();
  fireEvent.click(await screen.findByRole('button',{name:'Simulate evidence correction (demo)'}));
  fireEvent.click(screen.getByRole('button',{name:'Confirm simulated correction'}));
  await screen.findByText(/Simulated correction recorded. Obligation open; returned to assigned owner: Hospital B coordination/);
  expect(api).toHaveBeenCalledWith('test','/v1/tsp/demo/obligations/obligation-one/correct-closing-evidence','POST',{evidence_id:'demo-closing',confirmation:'invalidate closing synthetic evidence'});
});
test.each(['reviewer','viewer'] as const)('correction control hidden for %s',async role=>{
  vi.mocked(api).mockResolvedValue({demo_mode:true});mount(role);await waitFor(()=>expect(api).toHaveBeenCalled());expect(screen.queryByRole('button')).toBeNull();
});
test('correction control hidden outside DEMO_MODE',async()=>{
  vi.mocked(api).mockResolvedValue({demo_mode:false});mount();await waitFor(()=>expect(api).toHaveBeenCalled());expect(screen.queryByRole('button')).toBeNull();
});
test('open obligation cannot be corrected by this closure control',async()=>{
  vi.mocked(api).mockResolvedValue({demo_mode:true});mount('coordinator','open');
  expect((await screen.findByRole('button',{name:'Simulate evidence correction (demo)'})).hasAttribute('disabled')).toBe(true);
});
test('server rejection stays visible and never reports a successful reopening',async()=>{
  vi.mocked(api).mockImplementation(async(_token,path)=>{if(path==='/session')return {demo_mode:true};throw Error('Closing evidence changed');});mount();
  fireEvent.click(await screen.findByRole('button',{name:'Simulate evidence correction (demo)'}));fireEvent.click(screen.getByRole('button',{name:'Confirm simulated correction'}));
  await screen.findByRole('alert');expect(screen.queryByText(/Simulated correction recorded/)).toBeNull();
});
test('lifecycle reopened state is from audit, with original owner',()=>{
  const data={care_coordination_tasks:[],clinical_approvals:[],clinical_evidence:[],rule_versions:[],audit_events:[{action:'closure_reopened',obligation_id:obligation.id}]} as unknown as Snapshot;
  render(<MemoryRouter><Lifecycle data={data} item={{...obligation,status:'open'}}/></MemoryRouter>);
  expect(screen.getByText('Reopened').closest('li')?.className).toBe('done');expect(screen.getByText(/returned to Hospital B coordination/)).toBeTruthy();
});
