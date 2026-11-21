// @vitest-environment jsdom
import {cleanup,render,screen,fireEvent} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {MemoryRouter} from 'react-router-dom';
import {afterEach,expect,test,vi} from 'vitest';
import {SourceDocuments} from './SourceDocuments';
import {api} from './api';
vi.mock('./api',()=>({api:vi.fn()}));afterEach(()=>{cleanup();vi.resetAllMocks();});
test('shows exact text with cited highlight and back link; no model invocation',async()=>{
 vi.mocked(api).mockResolvedValue([{id:'doc',title:'Adolescent clinic note',facility:'Hospital A',date:'2011-07-10',version:1,digest:'a'.repeat(64),status:'valid',simulated:true,text:'Hospital A recorded: documented PCOS diagnosis.',citations:[{candidate_id:'candidate',excerpt:'documented PCOS diagnosis',url:'/passport?candidate=candidate&patient=demo-amira'}]}]);
 render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><MemoryRouter><SourceDocuments data={{patients:[{id:'demo-amira',resource:{name:[{given:['Amira'],family:'Haddad'}]}}]} as any} token="synthetic" role="coordinator" busy={false} action={()=>{}}/></MemoryRouter></QueryClientProvider>);
 await screen.findByLabelText('Full stored document text');expect(screen.getByLabelText('Full stored document text').textContent).toBe('Hospital A recorded: documented PCOS diagnosis.');
 expect(document.querySelector('mark')?.textContent).toBe('documented PCOS diagnosis');expect(screen.getByRole('link',{name:'View where it is cited'}).getAttribute('href')).toContain('candidate=candidate');
 expect(screen.getByText('SIMULATED')).toBeTruthy();expect(screen.getByText(/PDF and scanned documents are on the roadmap/)).toBeTruthy();
 expect(vi.mocked(api).mock.calls.every(call=>String(call[1]).includes('/source-documents/'))).toBe(true);
});
