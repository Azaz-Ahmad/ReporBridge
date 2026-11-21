import { displayText } from './presentation';
import {ExplanationOutput,type ExplanationProjection} from './ExplanationOutput';
import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from './api';
import { FacilityChips, type Facility } from './Handoff';
import { Button, Panel, Feedback } from './ui';
import type { Role } from './types';
export type EarlierSource={id:string;kind:string;resource_id:string;version:number;digest:string;clinical_time:string;finding:string|null;source_url:string;provenance:{facility?:Facility}};
export type HistoryState={age_at_record:number;age_at_registration:number;findings:EarlierSource[];rule_traces:{rule_id:string;policy_id:string;policy_version:string;triggered:boolean;target_window:string;citation:string;clinical_confirmation:string;reason:string}[]};
const base='/v1/history-handoff';
export function EarlierRecords({token,role,patientId}:{token:string;role:Role;patientId:string}){
 const cache=useQueryClient();const [source,setSource]=useState<EarlierSource>();
 const query=useQuery({queryKey:['history',patientId,token],enabled:patientId==='demo-amira',queryFn:()=>api<HistoryState>(token,base+'/patients/'+patientId)});
 const action=useMutation({mutationFn:async()=>{await api(token,base+'/seed','POST');return api<HistoryState>(token,base+'/patients/'+patientId+'/receive','POST');},onMutate:async()=>{await cache.cancelQueries({queryKey:['history',patientId,token]});},onSuccess:result=>{cache.setQueryData(['history',patientId,token],result);for(const key of ['history','snapshot','prevention','clinical-explorer','tsp','historical-candidates'])cache.invalidateQueries({queryKey:[key]});}});
 const explain=useMutation({mutationFn:()=>api<{id:string;detail:{explanation?:ExplanationProjection;trace?:string[];error?:string|null;packet:{summary:string;findings:{statement:string;supporting_sources:{evidence_id:string;version:number}[]}[];abstained:boolean}|null}}>(token,base+'/patients/'+patientId+'/explanations','POST',{request_id:crypto.randomUUID()})});
 useEffect(()=>{explain.reset();},[query.data]);
 const raw=useQuery({queryKey:['history-source',source?.id,token],enabled:!!source,queryFn:()=>api<{resource:Record<string,unknown>|null}>(token,source!.source_url.replace(/^\/api/,''))});
 if(patientId!=='demo-amira')return null;
 const data=query.data;
 let content='';if(raw.data?.resource){const resource=raw.data.resource as {content?:{attachment:{data?:string}}[]};const encoded=resource.content?.[0]?.attachment.data;content=encoded?new TextDecoder().decode(Uint8Array.from(atob(encoded),c=>c.charCodeAt(0))):JSON.stringify(resource,null,2);}
 return <Panel title="Found in earlier records"><p><strong>Simulated provider exchange</strong> · Hospital A → Hospital B · no live connection</p>
 {role==='coordinator'&&<Button disabled={action.isPending} onClick={()=>action.mutate()}>Receive earlier Hospital A records</Button>}
 {role==='coordinator'&&!!data?.findings.length&&<Button variant="outline" disabled={explain.isPending} onClick={()=>explain.mutate()}>Explain cited earlier record</Button>}
 {explain.error&&<Feedback message={explain.error.message} error/>}
 {explain.data?.detail.error&&<Feedback message={"Explanation unavailable: "+explain.data.detail.error} error/>}
 {explain.data&&<div className="inset"><p>Explanation · mandatory human review</p><ExplanationOutput detail={explain.data.detail}/>{!explain.data.detail.explanation&&<p>{explain.data.detail.packet?.summary}</p>}{explain.data.detail.packet?.findings.map((finding,index)=><div key={index}><p>{displayText(finding.statement)}</p><details className="history-model-citation"><summary>Supporting source references</summary>Sources: {finding.supporting_sources.map(source=>`${source.evidence_id} · version ${source.version}`).join('; ')}</details></div>)}</div>}
 {action.error&&<Feedback message={action.error.message} error/>}{query.error&&<Feedback message={query.error.message} error/>}
 {!data?.findings.length&&<p>No earlier matching records received. This rule adds no trigger without the documented finding.</p>}
 {!!data?.findings.length&&<><p>Age {data.age_at_record} at the 2011 record; age {data.age_at_registration} at the 2026 pregnancy registration. Earlier documentation does not establish a current diagnosis or risk level.</p>
 <ul className="history-sources">{data.findings.map(item=><li key={item.id}><FacilityChips facility={item.provenance.facility}/><strong>{item.finding||'Historical source document'}</strong>
 <p>Recorded {item.clinical_time.slice(0,10)} · version {item.version}</p><Button variant="outline" onClick={()=>setSource(item)}>Open {item.kind==='DocumentReference'?'source document':'source finding'}</Button></li>)}</ul></>}
 {data?.rule_traces.map(rule=><div className="inset" key={rule.rule_id}><strong>{rule.triggered?'Documented finding linked to existing '+rule.target_window:'No trigger from this historical rule'}</strong><details><summary>Historical rule details</summary>Rule {rule.rule_id} · policy {rule.policy_id} version {rule.policy_version}</details><p>{displayText(rule.reason)}</p><p><strong className="tsp-citation">pending clinical confirmation</strong></p><p>Window dates, eligibility and closure remain server-controlled. Existing review and closure gates still apply.</p></div>)}
 {source&&<div className="inset" aria-label="Earlier source viewer"><h3>Source record · untrusted data</h3><details><summary>Source identifier</summary>{source.resource_id} · version {source.version}</details>{raw.error&&<Feedback message={raw.error.message} error/>}<pre className="history-document">{displayText(content||'Source content unavailable or loading.')}</pre><Button variant="outline" onClick={()=>setSource(undefined)}>Close source</Button></div>}
 </Panel>;
}
