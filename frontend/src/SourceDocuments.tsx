import {useState} from 'react';
import {FileText, Search, ShieldCheck} from 'lucide-react';
import {useQuery} from '@tanstack/react-query';
import {Link,useSearchParams} from 'react-router-dom';
import {api} from './api';
import {Panel,Feedback} from './ui';
import type {ScreenProps} from './screens';
type Document={id:string;title:string;facility:string;date:string;version:number;digest:string;status:string;source_state?:string;simulated:boolean;text:string;text_available?:boolean;unavailable_reason?:string|null;citations:{candidate_id:string;excerpt:string|null;url:string}[]};
export function SourceDocuments({data,token}:ScreenProps){
 const [params,setParams]=useSearchParams();const patientId=params.get('patient')||data.patients[0]?.id||'';
 const [chosen,setChosen]=useState('');
 const [search,setSearch]=useState('');
 const query=useQuery({queryKey:['source-documents',patientId,token],enabled:!!patientId,queryFn:()=>api<Document[]>(token,'/v1/source-documents/patients/'+patientId)});
 const documents=query.data||[];const document=documents.find(d=>d.id===(params.get('document')||chosen))||documents[0];
 const filter=search.trim().toLocaleLowerCase();
 const visibleDocuments=documents.filter(d=>!filter||d.title.toLocaleLowerCase().includes(filter)||d.facility.toLocaleLowerCase().includes(filter));
 const excerpts=[...new Set(document?.citations.map(c=>c.excerpt).filter((x):x is string=>!!x)||[])];
 let text:React.ReactNode[]=document?[document.text]:[];
 for(const excerpt of excerpts)text=text.flatMap<React.ReactNode>((part,i)=>typeof part==='string'?part.split(excerpt).flatMap((chunk,j)=>j?[<mark key={i+'-'+j}>{excerpt}</mark>,chunk]:[chunk]):[part]);
 return <div className="source-documents-page">
  <div className="page-heading source-documents-heading"><div><h1><FileText size={28} aria-hidden="true"/>Source Documents</h1><p>Original clinical records, exactly as stored.</p></div>
   <label>Patient<select aria-label="Document patient" value={patientId} onChange={e=>{setChosen('');setSearch('');setParams({patient:e.target.value});}}>{data.patients.map(p=><option key={p.id} value={p.id}>{p.resource.name?.[0]?.given?.join(' ')} {p.resource.name?.[0]?.family}</option>)}</select></label>
  </div>
  <div className="source-documents-note"><ShieldCheck size={18} aria-hidden="true"/><span>No model is called on this page. Documents are shown exactly as stored.</span></div>
  {query.error&&<Feedback message={query.error.message} error/>}
  <div className="source-documents-layout">
   <Panel title="Document Library">
    <label className="source-library-search"><span>Search loaded documents</span><div><Search size={17} aria-hidden="true"/><input type="search" value={search} placeholder="Title or facility" onChange={e=>setSearch(e.target.value)}/></div></label>
    <p className="source-library-count" role="status">{visibleDocuments.length} of {documents.length} documents · patient-scoped</p>
    <div className="document-list source-library-list" role="region" aria-label="Document library" tabIndex={0}>
     {visibleDocuments.map(d=><button type="button" className={d.id===document?.id?'selected':''} aria-pressed={d.id===document?.id} key={d.id} onClick={()=>{setChosen(d.id);setParams({patient:patientId,document:d.id});}}>
      <div className="source-library-title"><FileText size={19} aria-hidden="true"/><strong>{d.title}</strong></div>
      <span>{d.facility} · {d.date?.slice(0,10)} · version {d.version}</span>
      <div className="source-library-badges">{d.simulated&&<span className="pill source-simulated">SIMULATED</span>}<span className="source-state">{d.source_state||d.status}</span>{d.text_available===false&&<span className="source-state">Stored text unavailable</span>}</div>
     </button>)}
    </div>
    {!documents.length&&<p>{query.isPending?'Loading documents…':'No source documents in this patient scope. Earlier Hospital A records appear only after the simulated exchange.'}</p>}
    {!!documents.length&&!visibleDocuments.length&&<p role="status">No loaded documents match this title or facility.</p>}
    {!!document&&filter&&!visibleDocuments.some(d=>d.id===document.id)&&<p className="source-filter-note">The selected document remains open in the viewer; it is outside this filter.</p>}
   </Panel>
   <Panel title={document?.title||'Original Document Viewer'}>
    {document?<>
     <dl className="source-document-meta"><div><dt>Source facility</dt><dd>{document.facility}</dd></div><div><dt>Recorded date</dt><dd>{document.date?.slice(0,10)||'Not supplied'}</dd></div><div><dt>Version</dt><dd>{document.version}</dd></div><div><dt>Status</dt><dd>{document.status}</dd></div><div><dt>Source state</dt><dd>{document.source_state||'not supplied'}</dd></div></dl>
     {document.simulated&&<p className="pill source-simulated">SIMULATED provider exchange</p>}
     {document.status!=='valid'&&<p className="source-document-warning">Historical or unavailable source: inspect its version and state. Displaying stored text does not make it qualifying clinical evidence.</p>}
     {document.text_available===false?<p className="source-document-unavailable" role="note" aria-label="Stored text availability">{document.unavailable_reason||"No stored inline text is available."}</p>:<pre className="stored-document" aria-label="Full stored document text">{text}</pre>}
     {!!document.citations.length&&<div className="source-document-citations">{document.citations.map(c=><p key={c.candidate_id}>Highlighted text is quoted in the candidate source context. <Link className="text-link" to={c.url}>View where it is cited</Link></p>)}</div>}
     <details className="source-document-integrity"><summary><ShieldCheck size={17} aria-hidden="true"/>Source integrity and provenance</summary><dl className="source-document-meta"><div><dt>Source identifier</dt><dd>{document.id}</dd></div><div><dt>Document version</dt><dd>{document.version}</dd></div><div><dt>Source facility</dt><dd>{document.facility}</dd></div><div><dt>Recorded date</dt><dd>{document.date||'Not supplied'}</dd></div><div><dt>Source state</dt><dd>{document.source_state||'not supplied'}</dd></div></dl><strong>Integrity hash</strong><code>{document.digest}</code></details>
    </>:<p>{query.isPending&&patientId?'Loading stored document…':'No stored document selected.'}</p>}
   </Panel>
  </div>
  <p className="source-documents-formats">Accepted formats today: plain text and Markdown. PDF and scanned documents are on the roadmap.</p>
 </div>;
}
export function SourceDocumentsLink({patientId}:{patientId:string}){return <Link className="text-link" to={'/documents?patient='+patientId}>Read source documents</Link>;}

export function LatestSourceDocuments({token,patientId}:{token:string;patientId:string}){
 const query=useQuery({queryKey:['source-documents',patientId,token],queryFn:()=>api<Document[]>(token,'/v1/source-documents/patients/'+patientId)});
 const rows=Array.isArray(query.data)?query.data:[];
 return <Panel title="Latest source documents — read-only"><p>Inspect the stored source before reviewing a draft. No model is called by this panel.</p>
 {query.error&&<Feedback message={query.error.message} error/>}
 <ul className="latest-source-list">{rows.slice(0,8).map(d=><li key={d.id}><Link className="text-link" to={'/documents?patient='+patientId+'&document='+d.id}>{d.title}</Link><span>{d.facility} · {d.date?.slice(0,10)} · version {d.version}{d.simulated?' · SIMULATED':''}</span><small>{d.source_state||d.status}</small></li>)}</ul>
 {!rows.length&&<p>{query.isPending?'Loading stored documents…':'No stored documents in this patient scope.'}</p>}
 <p>Accepted formats today: plain text and Markdown. PDF and scanned documents are on the roadmap.</p></Panel>;
}
