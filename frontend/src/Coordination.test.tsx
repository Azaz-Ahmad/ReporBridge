// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
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


import {GuidelineTraceability} from './Coordination';
test('traceability shows policy criteria facility date and an authenticated source link', async()=>{
  vi.mocked(api).mockImplementation(async(_token,path)=>path.includes('/evidence/')?{resource:{resourceType:'Observation',status:'final'}}:{
    policy_id:'glycemic-assessment-pregnancy',policy_version:'1',policy_active:true,eligibility_criteria:['W1 requires a carried obligation.'],
    historical_policy:{id:'historical-finding-to-w1',version:'1',rules:[]},supporting_evidence:[{
      id:'source-one',label:'Historical source',clinical_time:'2011-07-10',version:1,
      provenance:{facility:{simulation:true,origin:'Hospital A',receiving:'Hospital B'}},source_url:'/api/v1/clinical/patients/demo-amira/evidence/source-one'}]});
  render(<QueryClientProvider client={new QueryClient()}><GuidelineTraceability token="test" patientId="demo-amira"/></QueryClientProvider>);
  await screen.findByText('W1 requires a carried obligation.');
  expect(screen.getByText('glycemic-assessment-pregnancy · version 1')).toBeTruthy();
  expect(screen.getByText('SIMULATED · Hospital A')).toBeTruthy();
  expect(screen.getByText(/Source date: 2011-07-10/)).toBeTruthy();
  expect(screen.queryByText('CITATION_PENDING_CLINICAL_CONFIRMATION')).toBeNull();
  fireEvent.click(screen.getByRole('link',{name:'Open source record'}));
  await screen.findByLabelText('Guideline source viewer');
  expect(api).toHaveBeenCalledWith('test','/v1/clinical/patients/demo-amira/evidence/source-one');
});


test('switching passport patient clears a previously opened source viewer',async()=>{
  vi.mocked(api).mockImplementation(async(_token,path)=>path.includes('/evidence/')?{resource:{valueString:'Prior patient source record'}}:{
    policy_id:'glycemic-assessment-pregnancy',policy_version:'1',policy_active:true,eligibility_criteria:[],historical_policy:{id:'history',version:'1',rules:[]},
    supporting_evidence:[{id:'source',label:path.includes('demo-lina')?'New patient source':'Earlier patient source',clinical_time:'2026-11-22',version:1,provenance:{},
      source_url:'/api/v1/clinical/patients/'+(path.includes('demo-lina')?'demo-lina':'demo-amira')+'/evidence/source'}]});
  const client=new QueryClient({defaultOptions:{queries:{retry:false}}});
  const content=(patientId:string)=><QueryClientProvider client={client}><GuidelineTraceability token="test" patientId={patientId}/></QueryClientProvider>;
  const view=render(content('demo-amira'));
  fireEvent.click(await screen.findByRole('link',{name:'Open source record'}));
  await screen.findByText(/Prior patient source record/);
  view.rerender(content('demo-lina'));
  await screen.findByText('New patient source');
  expect(screen.queryByLabelText('Guideline source viewer')).toBeNull();
  expect(screen.queryByText(/Prior patient source record/)).toBeNull();
});
