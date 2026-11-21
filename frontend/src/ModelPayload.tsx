import {useState} from 'react';
import {useQuery} from '@tanstack/react-query';
import {api} from './api';
import {Panel,Feedback} from './ui';
import {displayJson} from './presentation';
import type {Role} from './types';
type Call={id:string;created:string;requested_model:string;reported_model:string|null;mode:string;replayed:boolean;provider_request_id:string|null;usage:unknown;latency_ms:number|null};
type Detail={detail:Call&{error?:string;original_capture_available:boolean;capture_note?:string;redaction_label:string;redactions:string[];request_truncated:boolean;response_truncated:boolean;context_manifest:{patient_name_or_identifier_text_present?:boolean;date_of_birth_present?:boolean;records?:{record:unknown;fields:string[]}[]};request_payload:unknown;raw_response:unknown}};
export function ModelPayload({token,role,patientId}:{token:string;role:Role;patientId:string}){
 const [tab,setTab]=useState(false);const [selected,setSelected]=useState('');
 const enabled=role==='coordinator'||role==='reviewer';
 const list=useQuery({queryKey:['model-payloads',token,patientId],enabled:enabled&&tab,queryFn:()=>api<Call[]>(token,'/v1/model-payloads/patients/'+patientId)});
 const id=selected||list.data?.[0]?.id;
 const call=useQuery({queryKey:['model-payload-view',token,patientId,id],enabled:enabled&&tab&&!!id,queryFn:()=>api<Detail>(token,'/v1/model-payloads/'+id),staleTime:0});
 if(!enabled)return null;const detail=call.data?.detail;
 return <Panel title="Model transport transparency"><div role="tablist" aria-label="Evidence inspection"><button type="button" role="tab" aria-selected={!tab} onClick={()=>setTab(false)}>Audit information</button><button type="button" role="tab" aria-selected={tab} onClick={()=>setTab(true)}>Model payload</button></div>
 {tab?<><p>Patient-scoped; Coordinator and Reviewer only. Every payload view is audited. Keys and headers are never captured.</p>{list.error&&<Feedback message={list.error.message} error/>}{call.error&&<Feedback message={call.error.message} error/>}
 {list.isPending?<p>Loading captured call index…</p>:list.data?.length?<label>Model call<select aria-label="Model call" value={id} onChange={e=>setSelected(e.target.value)}>{list.data.map(c=><option key={c.id} value={c.id}>{c.created} · {c.requested_model} · {c.replayed?'replayed':'live'}</option>)}</select></label>:list.isError?null:<p>No captured model calls for this patient. Older traces cannot be reconstructed as exact payloads.</p>}
 {id&&call.isPending&&<p>Loading captured model payload…</p>}
 {detail&&<><p>Requested: {detail.requested_model} · provider reported: {detail.reported_model||'not reported'} · {detail.replayed?'replayed — original recorded call':'live'} · {detail.latency_ms??'not recorded'} ms</p><p>Request ID: {detail.provider_request_id||'not reported'}</p><p>{detail.replayed?'Recorded usage (no provider call during replay): ':'Actual provider usage: '}{detail.usage==null?'Not reported':displayJson(detail.usage)}</p>{detail.capture_note&&<p>{detail.capture_note}</p>}{detail.error&&<p role="note">Transport error: {detail.error}. No response or token usage is invented.</p>}
 <div className="document-layout"><div><h3>Records and fields sent</h3><p>Patient name/identifier text present: {String(detail.context_manifest.patient_name_or_identifier_text_present??'unknown')}. Date of birth present: {String(detail.context_manifest.date_of_birth_present??'unknown')}.</p><ul>{detail.context_manifest.records?.map((record,index)=><li key={index}>{typeof record.record==='string'?record.record:'Unrecognized legacy manifest entry; inspect the actual payload'} — {Array.isArray(record.fields)?record.fields.join(', '):''}</li>)}</ul><details><summary>Full context manifest</summary><pre>{displayJson(detail.context_manifest)}</pre></details></div><div><h3>Redactions</h3><p>{detail.redaction_label}</p><pre>{displayJson(detail.redactions)}</pre></div></div>
 {detail.original_capture_available?<div className="payload-grid"><div><h3>Request payload{detail.request_truncated?' — TRUNCATED':''}</h3><pre aria-label="Captured request payload">{JSON.stringify(detail.request_payload,null,2)}</pre></div><div><h3>Raw response{detail.response_truncated?' — TRUNCATED':''}</h3><pre aria-label="Captured raw response">{JSON.stringify(detail.raw_response,null,2)}</pre></div></div>:<p>Original wire payload is unavailable in this legacy recording. No substitute payload is shown.</p>}</>}
 </>:<p>Open Model payload to inspect actual provider transport bodies. Clinical closure and candidate decisions remain separate.</p>}</Panel>;
}
