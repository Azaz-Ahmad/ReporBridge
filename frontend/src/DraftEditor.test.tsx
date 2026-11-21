// @vitest-environment jsdom
import {cleanup,render,screen,fireEvent,waitFor} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {afterEach,expect,test,vi} from 'vitest';
import {DraftEditor} from './DraftEditor';import {api} from './api';
vi.mock('./api',()=>({api:vi.fn()}));afterEach(()=>{cleanup();vi.resetAllMocks();});
test('immutable original and clinician version stay separate; approval binds saved id',async()=>{
 let state:any={original:{text:'Original model-backed window text',model:'recorded-model',digest:'original',created:'2026-11-21'},versions:[],approval:null,date_notice:null,submitted:true,reviewed:false,calculator:{as_of:'2026-11-22',status:'IN_WINDOW',windows:[{id:'W1',window_start:'2026-11-14',window_end:'2026-12-01',status:'IN_WINDOW'}]}};
 vi.mocked(api).mockImplementation(async(_token,path,method,body:any)=>{if(method==='POST'&&path.endsWith('/versions'))state={...state,versions:[{id:'saved-version',number:1,text:body.text,editor:'reviewer',role:'reviewer',created:'2026-11-21',digest:'edited'}],date_notice:'Edited text has a date outside the calculator; review is not blocked.'};if(method==='POST'&&path.endsWith('/approve'))state={...state,approval:{version_id:body.version_id},reviewed:true};return state;});
 render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><DraftEditor token="synthetic" role="reviewer" runId="run" onReviewed={()=>{}}/></QueryClientProvider>);
 await screen.findByLabelText('Clinician-authored draft');fireEvent.change(screen.getByLabelText('Clinician-authored draft'),{target:{value:'Clinician authored a different date: 2030-01-01'}});fireEvent.click(screen.getByRole('button',{name:'Save clinician-authored version'}));await screen.findByText(/date outside the calculator/);
 expect(screen.getByLabelText('Original immutable draft').textContent).toBe('Original model-backed window text');expect(screen.getByLabelText('Calculator-owned windows').textContent).toContain('2026-12-01');
 fireEvent.change(screen.getByLabelText('Edited draft review note'),{target:{value:'Clinician reviewed this exact version.'}});fireEvent.click(screen.getByRole('button',{name:'Approve clinician-authored draft'}));await screen.findByText(/Clinician-authored version approved/);
 expect(api).toHaveBeenCalledWith('synthetic','/v1/review-drafts/run/approve','POST',{version_id:'saved-version',note:'Clinician reviewed this exact version.'});
});
