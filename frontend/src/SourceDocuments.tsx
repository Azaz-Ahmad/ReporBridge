import {useState} from 'react';
import {useQuery} from '@tanstack/react-query';
import {Link,useSearchParams} from 'react-router-dom';
import {api} from './api';
import {Panel,Feedback} from './ui';
import type {ScreenProps} from './screens';
type Document={id:string;title:string;facility:string;date:string;version:number;digest:string;status:string;source_state?:string;simulated:boolean;text:string;citations:{candidate_id:string;excerpt:string|null;url:string}[]};
export function SourceDocuments({data,token}:ScreenProps){
 const [params,setParams]=useSearchParams();const patientId=params.get('patient')||data.patients[0]?.id||'';
 const [chosen,setChosen]=useState('');
 const query=useQuery({queryKey:['source-documents',patientId,token],enabled:!!patientId,queryFn:()=>api<Document[]>(token,'/v1/source-documents/patients/'+patientId)});
 const documents=query.data||[];const document=documents.find(d=>d.id===(params.get('document')||chosen))||documents[0];
 const excerpts=[...new Set(document?.citations.map(c=>c.excerpt).filter((x):x is string=>!!x)||[])];
 let text:React.ReactNode[]=document?[document.text]:[];
 for(const excerpt of excerpts)text=text.flatMap<React.ReactNode>((part,i)=>typeof part==='string'?part.split(excerpt).flatMap((chunk,j)=>j?[<mark key={i+'-'+j}>{excerpt}</mark>,chunk]:[chunk]):[part]);
 return <><div className="page-heading"><div><h1>Source documents</h1><p>The underlying synthetic records, with no model in between.</p></div><label>Patient<select aria-label="Document patient" value={patientId} onChange={e=>{setChosen('');setParams({patient:e.target.value});}}>{data.patients.map(p=><option key={p.id} value={p.id}>{p.resource.name?.[0]?.given?.join(' ')} {p.resource.name?.[0]?.family}</option>)}</select></label></div>
 <p>No model is called on this page. Documents are shown exactly as stored.</p><p>Accepted formats today: plain text and Markdown. PDF and scanned documents are on the roadmap.</p>
 {query.error&&<Feedback message={query.error.message} error/>}
 <div className="document-layout"><Panel title="Patient source documents"><div className="document-list">{documents.map(d=><button type="button" className={d.id===document?.id?'selected':''} key={d.id} onClick={()=>{setChosen(d.id);setParams({patient:patientId,document:d.id});}}><strong>{d.title}</strong><span>{d.facility} · {d.date?.slice(0,10)} · version {d.version}</span>{d.simulated&&<span className="pill">SIMULATED</span>}</button>)}</div>{!documents.length&&<p>{query.isPending?'Loading documents…':'No source documents in this patient scope. Earlier Hospital A records appear only after the simulated exchange.'}</p>}</Panel>
 <Panel title={document?.title||'Stored source text'}>{document&&<><p>{document.facility} · {document.date?.slice(0,10)} · version {document.version} · {document.status} · source state: {document.source_state||'not supplied'}</p>{document.status!=='valid'&&<p>Historical or unavailable source: inspect its version and state. Displaying stored text does not make it qualifying clinical evidence.</p>}{document.simulated&&<p className="pill">SIMULATED provider exchange</p>}<details><summary>Integrity hash</summary><code>{document.digest}</code></details><pre className="stored-document" aria-label="Full stored document text">{text}</pre>{document.citations.map(c=><p key={c.candidate_id}>Highlighted text is quoted in the candidate source context. <Link className="text-link" to={c.url}>View where it is cited</Link></p>)}</>}</Panel></div></>;
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
