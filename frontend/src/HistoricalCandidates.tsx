import { WorkspaceDetails } from './WorkspaceDetails';
import { useState, type ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api } from './api';
import { FacilityChips, type Facility } from './Handoff';
import { displayJson, displayText } from './presentation';
import { Button, Feedback, Panel } from './ui';
import type { Role } from './types';

export type HistoricalCandidate={id:string;patient_id:string;title:string;owner_role:string;status:string;status_label:string;
  demo_date:string;rule_id:string;rule_version:string;clinical_confirmation:string;eligibility_criteria:string[];
  target_window:string;window:{id:string;status:string;window_start:string;window_end:string}|null;
  as_of:string;calculator_status:string;window_policy_id:string|null;window_policy_version:string|null;
  obligation_id:string|null;decision:{rationale:string;actor:string;demo_date:string}|null;
  source_refs:{id:string;kind:string;resource_id:string;version:number;digest:string;clinical_time:string|null;trigger:boolean;source_url:string;provenance:{facility?:Facility}}[]};
function CandidateDetails({compact,children}:{compact:boolean;children:ReactNode}){return compact?<details className="passport-candidate-details"><summary>Eligibility, source evidence and provenance</summary>{children}</details>:<>{children}</>;}
const base='/v1/historical-candidates';
function useCandidates(token:string,patientId:string){return useQuery({queryKey:['historical-candidates',patientId,token],queryFn:()=>api<HistoricalCandidate[]>(token,base+'/patients/'+patientId)});}
export function HistoricalIdentificationBadge({token}:{token:string}){
 const query=useQuery({queryKey:['historical-candidates','queue',token],queryFn:()=>api<HistoricalCandidate[]>(token,base)});
 const found=(query.data||[]).filter(row=>['candidate','confirmed'].includes(row.status));
 if(query.error)return <Feedback message={query.error.message} error/>;
 if(!found.length)return null;
 const first=found[0];return <Link className="pill history-identification" to={'/passport?candidate='+first.id+'&patient='+first.patient_id}>Identified from earlier records · {found.length}</Link>;
}
export function HistoricalDetectionTimeline({token,patientId}:{token:string;patientId:string}){
 const query=useCandidates(token,patientId);if(!query.data?.length)return null;
 return <div className="historical-detection-timeline"><h3>Historical finding detection</h3><ul className="timeline" aria-label="Historical detection timeline">{query.data.map(row=><li key={row.id}><strong>Identified from earlier records</strong><small>{row.demo_date} · demo-calendar detection date · {row.status_label}</small><Link className="text-link" to={'/passport?candidate='+row.id+'&patient='+patientId}>Open candidate passport</Link></li>)}</ul></div>;
}
export function HistoricalCandidates(props:{token:string;role:Role;patientId:string;candidateId?:string;compact?:boolean;passportSummary?:boolean}){
 return <HistoricalCandidateScope key={props.patientId} {...props}/>;
}
function HistoricalCandidateScope({token,role,patientId,candidateId,compact=false,passportSummary=false}:{token:string;role:Role;patientId:string;candidateId?:string;compact?:boolean;passportSummary?:boolean}){
 const query=useCandidates(token,patientId);const cache=useQueryClient();const [notes,setNotes]=useState<Record<string,string>>({});
 const [source,setSource]=useState<HistoricalCandidate['source_refs'][number]>();
 const raw=useQuery({queryKey:['historical-candidate-source',patientId,token,source?.id],enabled:!!source,queryFn:()=>api<{resource:unknown}>(token,source!.source_url.replace(/^\/api/,''))});
 const decision=useMutation({mutationFn:({row,choice}:{row:HistoricalCandidate;choice:'confirm'|'dismiss'})=>api<HistoricalCandidate>(token,base+'/'+row.id+'/review','POST',{decision:choice,rationale:notes[row.id]||''}),
   onSuccess:()=>{setNotes({});for(const key of ['historical-candidates','snapshot','tsp','history','prevention'])cache.invalidateQueries({queryKey:[key]});}});
 const rows=(query.data||[]).filter(row=>!candidateId||row.id===candidateId);
 if(!rows.length&&!query.error&&!candidateId)return null;
 return <Panel title="Identified from earlier records">
  <p hidden={passportSummary}>Deterministic policy-data identification. A candidate is not an active care obligation until a clinician confirms it. No agent decides relevance, risk, timing or closure.</p>
  {query.error&&<Feedback message={query.error.message} error/>}
  {candidateId&&!rows.length&&!query.error&&<p>No candidate is available in this patient scope, or the record is loading.</p>}
  {rows.map(row=><article className="historical-candidate-card" key={row.id} data-candidate-status={row.status}>
    <h3>{row.title}</h3><span className="pill history-identification">{row.status_label}</span>
    {passportSummary&&<div className="passport-candidate-summary"><span>{row.status==='candidate'?'Reviewer confirmation required before activation.':`Reviewer requirement: ${row.owner_role} · ${row.status_label}`}</span>{row.source_refs.filter(source=>source.trigger).map(source=><span key={source.id}>{source.provenance.facility?`${source.provenance.facility.simulation?'SIMULATED · ':''}${source.provenance.facility.origin}`:'Facility not recorded'}</span>)}</div>}
    <CandidateDetails compact={passportSummary}>
    <p>Owner role: <strong>{row.owner_role}</strong> · identified {row.demo_date} · demo calendar</p>
    <p>Rule {row.rule_id} · version {row.rule_version}</p><p><strong>pending clinical confirmation</strong></p>
    <WorkspaceDetails compact={compact} title="Eligibility criteria from policy data"><h4>Eligibility criteria from policy data</h4><ul>{row.eligibility_criteria.map(text=><li key={text}>{text}</li>)}</ul></WorkspaceDetails>
    <p><strong>Calculator window: {row.target_window}</strong> · as of {row.as_of}</p>
    {row.window?<p>{row.window.window_start} – {row.window.window_end} (inclusive) · {row.window.status.replaceAll('_',' ')}</p>:<p>No established {row.target_window} window. Server status: {row.calculator_status.replaceAll('_',' ')}. A candidate does not create or change a timing window.</p>}
    <WorkspaceDetails compact={compact} title="Window policy details"><p>Window policy: {row.window_policy_id||'not established'} · version {row.window_policy_version||'not established'}</p></WorkspaceDetails>
    <h4>Trigger evidence and source context</h4><ul className="history-sources">{row.source_refs.map(item=><li key={item.id}>
      <strong>{item.trigger?'Trigger finding':'Supporting source document'}</strong>
      {item.provenance.facility?<FacilityChips facility={item.provenance.facility}/>:<p>Facility not recorded</p>}
      <p>Source date: {item.clinical_time?.slice(0,10)||'not recorded'} · version {item.version}</p>
      <a className="text-link" href={item.source_url} onClick={event=>{event.preventDefault();setSource(item);}}>Open candidate source</a>
      <details><summary>Source integrity details</summary>{item.digest}</details>
    </li>)}</ul>
    </CandidateDetails>
    {role==='reviewer'&&row.status==='candidate'&&<form className="candidate-review" onSubmit={event=>{event.preventDefault();decision.mutate({row,choice:'confirm'});}}>
      <label>Candidate review rationale<textarea required minLength={3} maxLength={1000} value={notes[row.id]||''} onChange={event=>setNotes({...notes,[row.id]:event.target.value})}/></label>
      <p>Confirmation creates a separate open obligation. Qualifying evidence, a further clinical review and the unchanged closure gates still apply.</p>
      <div className="actions"><Button type="submit" disabled={decision.isPending||(notes[row.id]||'').trim().length<3}>Confirm historical candidate</Button>
      <Button type="button" variant="outline" disabled={decision.isPending||(notes[row.id]||'').trim().length<3} onClick={()=>decision.mutate({row,choice:'dismiss'})}>Dismiss historical candidate</Button></div>
    </form>}
    {row.decision&&<p>Clinician decision: {row.status} · {row.decision.demo_date}. Rationale: {row.decision.rationale}</p>}
    {compact&&<Link className="text-link" to={'/passport?candidate='+row.id+'&patient='+patientId}>Open candidate passport</Link>}
    {row.obligation_id&&<Link className="text-link" to={'/passport?obligation='+row.obligation_id}>Open confirmed obligation</Link>}
    {row.status==='withdrawn'&&<p>Trigger evidence is no longer valid. The original source versions and audit remain available; any active care requires reconciliation through existing gates.</p>}
  </article>)}
  {!!rows.length&&(passportSummary?<details className="passport-candidate-investigation"><summary>Earlier-source evidence investigation</summary><HistoricalSourceInvestigation token={token} role={role} patientId={patientId}/></details>:<HistoricalSourceInvestigation token={token} role={role} patientId={patientId}/>)}
  {decision.error&&<Feedback message={decision.error.message} error/>}
  {decision.data&&<Feedback message={decision.data.status==='confirmed'?'Candidate confirmed. A separate open obligation was created; care remains unclosed.':'Candidate dismissed with an audited rationale.'}/>}
  {source&&<div className="inset" aria-label="Historical trigger source viewer"><h3>Source record · untrusted data</h3>{raw.error&&<Feedback message={raw.error.message} error/>}<pre className="history-document">{raw.data?displayJson(raw.data.resource):'Loading source…'}</pre><Button variant="outline" onClick={()=>setSource(undefined)}>Close candidate source</Button></div>}
 </Panel>;
}


type SourceRun={id:string;detail:{configuration:{model:string};error:string|null;duration_ms:number;trace:string[];
 usage:{model_calls:number;input_tokens:number;output_tokens:number};tool_history:{name:string;status:string}[];
 packet:{summary:string;grounding_status:string;abstained:boolean;findings:{statement:string}[]}|null}};
function HistoricalSourceInvestigation({token,role,patientId}:{token:string;role:Role;patientId:string}){
 const [attested,setAttested]=useState(false);
 const provider=useQuery({queryKey:['evidence-provider',token],queryFn:()=>api<{available:boolean;status:string;configuration?:{model:string}}>(token,'/v1/agents/clinical-evidence/status')});
 const investigation=useMutation({mutationFn:()=>api<SourceRun>(token,'/v1/history-handoff/patients/'+patientId+'/investigations','POST',{request_id:crypto.randomUUID()})});
 const run=investigation.data;const packet=run?.detail.packet;
 return <section className="inset" aria-label="Grounded earlier-source investigation"><h3>Earlier-source evidence investigation</h3>
   <p>Source summary only. The existing grounded agent may retrieve and quote records; it cannot determine relevance, risk, candidate decisions, windows or closure.</p>
   {provider.data&&!provider.data.available&&<p>Investigation provider is unavailable: {provider.data.status||'not configured'}. No substitute model or mock will be used.</p>}
   {provider.error&&<Feedback message={provider.error.message} error/>}
   {role==='coordinator'&&<><label className="clinical-history"><input type="checkbox" checked={attested} onChange={event=>setAttested(event.target.checked)}/> This earlier-source request contains synthetic data only.</label>
   <Button disabled={!attested||!provider.data?.available||patientId!=='demo-amira'||investigation.isPending} onClick={()=>investigation.mutate()}>Investigate cited earlier evidence</Button></>}
   {investigation.error&&<Feedback message={investigation.error.message} error/>}
   {run&&<div className="investigation-result"><p>Model: {run.detail.configuration.model} · {run.detail.usage.model_calls} requests · {run.detail.tool_history.length} tools · {run.detail.duration_ms} ms</p>
     {run.detail.error&&<Feedback message={run.detail.error} error/>}
     {packet&&<><p>Grounding: {packet.grounding_status}. {packet.abstained?'Agent abstained.':'Human interpretation required.'}</p><p>{displayText(packet.summary)}</p>{packet.findings.map((finding,index)=><p key={index}>{displayText(finding.statement)}</p>)}</>}
     <details><summary>Earlier-source investigation trace</summary><pre className="history-document">{displayJson(run.detail)}</pre></details>
     <p>The recorded investigation is also available in the care-resolution centre. It does not change the candidate.</p>
   </div>}
 </section>;
}
