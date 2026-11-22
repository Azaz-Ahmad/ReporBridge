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


test('Documents without stored inline text show an explicit availability note rather than a blank or fabricated text panel',async()=>{
 vi.mocked(api).mockResolvedValue([{id:'missing',title:'Unavailable source note',facility:'Hospital B',date:'2026-03-12',version:1,digest:'b'.repeat(64),status:'unavailable',simulated:false,text:'',text_available:false,unavailable_reason:'No supported stored inline text is available for this document. No external URL was fetched.',citations:[]}]);
 render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><MemoryRouter><SourceDocuments data={{patients:[{id:'demo-amira',resource:{name:[{given:['Amira'],family:'Haddad'}]}}]} as any} token="synthetic" role="coordinator" busy={false} action={()=>{}}/></MemoryRouter></QueryClientProvider>);
 expect((await screen.findByLabelText('Stored text availability')).textContent).toContain('No external URL was fetched');expect(screen.queryByLabelText('Full stored document text')).toBeNull();
});


function source(id:string,title:string,facility:string){return {id,title,facility,date:'2026-11-22',version:2,digest:id+'-stored-hash',status:'valid',source_state:'current',simulated:facility==='Hospital A',text:'Original line one.\n\n  Indented line two. <script>untrusted</script>',citations:[]};}
function mountDocuments(entry='/documents?patient=demo-amira'){
 const client=new QueryClient({defaultOptions:{queries:{retry:false}}});
 render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[entry]}><SourceDocuments data={{patients:[{id:'demo-amira',resource:{name:[{given:['Amira'],family:'Haddad'}]}},{id:'demo-lina',resource:{name:[{given:['Lina'],family:'Karim'}]}}]} as any} token="synthetic" role="viewer" busy={false} action={()=>{}}/></MemoryRouter></QueryClientProvider>);
}

test('local search filters title and facility without fetching, reordering or changing the selected document',async()=>{
 vi.mocked(api).mockResolvedValue([source('one','First note','Hospital A'),source('two','Second report','Hospital B'),source('three','Third note','Hospital A')]);
 mountDocuments();await screen.findByRole('button',{name:/First note/});
 const library=screen.getByRole('region',{name:'Document library'});
 const buttons=()=>Array.from(library.querySelectorAll('button')).map(button=>button.querySelector('strong')?.textContent);
 expect(buttons()).toEqual(['First note','Second report','Third note']);
 const calls=vi.mocked(api).mock.calls.length;
 fireEvent.change(screen.getByRole('searchbox',{name:'Search loaded documents'}),{target:{value:'  HOSPITAL B  '}});
 expect(buttons()).toEqual(['Second report']);expect(screen.getByRole('heading',{name:'First note'})).toBeTruthy();
 expect(screen.getByText(/selected document remains open/)).toBeTruthy();
 fireEvent.change(screen.getByRole('searchbox'),{target:{value:'third'}});expect(buttons()).toEqual(['Third note']);
 fireEvent.change(screen.getByRole('searchbox'),{target:{value:'not found'}});expect(screen.getByText('No loaded documents match this title or facility.')).toBeTruthy();
 fireEvent.change(screen.getByRole('searchbox'),{target:{value:''}});expect(buttons()).toEqual(['First note','Second report','Third note']);
 expect(vi.mocked(api).mock.calls).toHaveLength(calls);
});

test('document deep links and selection preserve exact multiline text and stored integrity metadata',async()=>{
 vi.mocked(api).mockResolvedValue([source('one','First note','Hospital A'),source('two','Second report','Hospital B')]);
 mountDocuments('/documents?patient=demo-amira&document=two');
 const selected=await screen.findByRole('button',{name:/Second report/});expect(selected.getAttribute('aria-pressed')).toBe('true');
 expect(screen.getByLabelText('Full stored document text').textContent).toBe(source('two','','').text);
 expect(document.querySelector('script')).toBeNull();
 const integrity=screen.getByText('Source integrity and provenance').closest('details')!;expect(integrity.open).toBe(false);
 fireEvent.click(screen.getByText('Source integrity and provenance'));expect(integrity.open).toBe(true);
 expect(screen.getByText('two-stored-hash')).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:/First note/}));expect(screen.getByRole('heading',{name:'First note'})).toBeTruthy();
 expect(screen.getByText('one-stored-hash')).toBeTruthy();
 expect(vi.mocked(api).mock.calls.every(call=>call[1]==='/v1/source-documents/patients/demo-amira'&&!call[2])).toBe(true);
});

test('patient change clears local search and uses the existing patient-scoped query',async()=>{
 vi.mocked(api).mockImplementation(async(_token,path)=>path.endsWith('demo-lina')?[source('lina','Lina original note','Hospital B')]:[source('amira','Amira original note','Hospital A')]);
 mountDocuments();await screen.findByRole('button',{name:/Amira original note/});
 fireEvent.change(screen.getByRole('searchbox'),{target:{value:'Hospital A'}});
 fireEvent.change(screen.getByRole('combobox',{name:'Document patient'}),{target:{value:'demo-lina'}});
 await screen.findByRole('button',{name:/Lina original note/});expect((screen.getByRole('searchbox') as HTMLInputElement).value).toBe('');
 expect(screen.queryByRole('button',{name:/Amira original note/})).toBeNull();
 expect(api).toHaveBeenCalledWith('synthetic','/v1/source-documents/patients/demo-lina');
});

test('loading and empty states remain explicit in both panels',async()=>{
 let finish!:(value:unknown[])=>void;vi.mocked(api).mockImplementation(()=>new Promise(resolve=>{finish=resolve;}));
 mountDocuments();expect(screen.getByText('Loading documents…')).toBeTruthy();expect(screen.getByText('Loading stored document…')).toBeTruthy();
 finish([]);await screen.findByText(/No source documents in this patient scope/);expect(screen.getByText('No stored document selected.')).toBeTruthy();
});

test('authorization errors remain visible without displaying fabricated document content',async()=>{
 vi.mocked(api).mockRejectedValue(new Error('Patient access denied'));
 mountDocuments();expect((await screen.findByRole('alert')).textContent).toContain('Patient access denied');
 expect(screen.queryByLabelText('Full stored document text')).toBeNull();
});
