import {useState} from 'react';
import {useMutation,useQuery} from '@tanstack/react-query';
import {api} from './api';import {Panel,Button,Feedback} from './ui';import type {Role} from './types';
type Version={id:string;number:number;text:string;editor:string;role:string;created:string;digest:string};
type ReviewDraft={original:{text:string;model:string;digest:string;created:string};versions:Version[];approval:{version_id:string}|null;date_notice:string|null;submitted:boolean;reviewed:boolean;calculator:{as_of:string;status:string;windows:{id:string;window_start:string;window_end:string;status:string}[]}};
export function DraftEditor({token,role,runId,onReviewed}:{token:string;role:Role;runId:string;onReviewed:()=>void}){
 const [text,setText]=useState<string>();const [note,setNote]=useState('');
 const query=useQuery({queryKey:['review-draft',token,runId],enabled:role!=='viewer',queryFn:()=>api<ReviewDraft>(token,'/v1/review-drafts/'+runId)});
 const data=query.data;const latest=data?.versions.at(-1);
 const edit=useMutation({mutationFn:()=>api<ReviewDraft>(token,'/v1/review-drafts/'+runId+'/versions','POST',{text:text??latest?.text??data?.original.text,expected_version:latest?.number||0}),onSuccess:()=>{setText(undefined);query.refetch();}});
 const approve=useMutation({mutationFn:()=>api<ReviewDraft>(token,'/v1/review-drafts/'+runId+'/approve','POST',{version_id:latest!.id,note}),onSuccess:()=>{query.refetch();onReviewed();}});
 if(role==='viewer')return null;
 return <Panel title="Original and clinician-authored draft"><p>Review happens in 04 Care resolution. Verified closure remains a separate action in 03 Obligation passport.</p>{query.error&&<Feedback message={query.error.message} error/>}
 {data&&<><div className="draft-columns"><div><h3>Original validated draft — immutable</h3><pre aria-label="Original immutable draft">{data.original.text}</pre><details><summary>Original draft details</summary>{data.original.model}<br/>{data.original.digest}<br/>{data.original.created} · system time</details></div>
 <div><h3>Clinician-authored version</h3>{role==='reviewer'&&!data.reviewed?<><label>Clinician-authored draft<textarea aria-label="Clinician-authored draft" maxLength={8000} value={text??latest?.text??data.original.text} onChange={e=>setText(e.target.value)}/></label><Button disabled={edit.isPending||!(text??latest?.text??data.original.text).trim()} onClick={()=>edit.mutate()}>Save clinician-authored version</Button></>:<pre>{latest?.text||'No clinician-authored version saved.'}</pre>}</div></div>
 <div className="inset" aria-label="Calculator-owned windows"><strong>Calculator-owned windows — separate from edited text</strong><p>As of {data.calculator.as_of}</p>{data.calculator.windows.map(w=><p key={w.id}>{w.window_start} to {w.window_end} · {w.status.replaceAll('_',' ')}</p>)}</div>
 {data.date_notice&&<p className="date-notice" role="note">{data.date_notice}</p>}
 <details><summary>Edited version history</summary><ol>{data.versions.map(v=><li key={v.id}>Clinician-authored · version {v.number} · {v.editor} · {v.role} · {v.created} (system time)<pre>{v.text}</pre><small>{v.digest}</small></li>)}</ol></details>
 {role==='reviewer'&&latest&&!data.reviewed&&<><label>Edited draft review note<textarea aria-label="Edited draft review note" maxLength={500} value={note} onChange={e=>setNote(e.target.value)}/></label><Button disabled={!data.submitted||!note.trim()||approve.isPending} onClick={()=>approve.mutate()}>Approve clinician-authored draft</Button>{!data.submitted&&<p>A coordinator must submit the original investigation for review first.</p>}</>}
 {data.approval&&<p role="status">Clinician-authored version approved. Clinical completion and closure still require their existing gates.</p>}
 </>}{edit.error&&<Feedback message={edit.error.message} error/>}{approve.error&&<Feedback message={approve.error.message} error/>}</Panel>;
}
