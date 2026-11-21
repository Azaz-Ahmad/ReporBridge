import { FacilityChips, type Facility } from './Handoff';
import { displayText } from './presentation';
import { useMutation, useQuery } from '@tanstack/react-query';
import { api } from './api';
import type { WindowResult } from './Tsp';
import { Feedback, Panel } from './ui';

export type CoordinationResult = WindowResult & { coordination: {
  action: string | null; owner_role: string | null; policy_id: string; policy_version: string;
  scope: string; policy_matched: boolean;
} };

export function ActionText({ result }: { result: CoordinationResult }) {
  return <>{result.coordination.action ? <>{result.coordination.action} ({result.coordination.owner_role})</> : 'None — no coordination action specified for this state.'}</>;
}

export function CoordinationNextAction({ token, patientId }: { token: string; patientId: string }) {
  const query = useQuery({ queryKey: ['tsp', 'coordination', patientId, token],
    queryFn: () => api<CoordinationResult>(token, '/v1/tsp/patients/' + patientId + '/coordination') });
  if (query.error) return <Feedback message={query.error.message} error />;
  if (!query.data) return <span aria-live="polite">Loading coordination action…</span>;
  return <div><ActionText result={query.data} /><p className="muted">Coordination only. No automatic action or owner change. Based on {query.data.status.replaceAll('_', ' ')} as of {query.data.as_of}.</p></div>;
}


export type GuidelineTrace = { source_guideline: string; policy_id: string | null; policy_version: string | null;
  policy_active: boolean; eligibility_criteria: string[];
  historical_policy: {id: string; version: string; rules: {rule_id: string; criteria: string; triggered: boolean}[]};
  supporting_evidence: {id: string; label: string; clinical_time: string | null; version: number;
    provenance: {facility?: Facility}; source_url: string}[];
};

export function GuidelineTraceability({token, patientId}: {token: string; patientId: string}) {
  const query = useQuery({queryKey:['tsp','guideline-trace',patientId,token],
    queryFn:()=>api<GuidelineTrace>(token,'/v1/tsp/patients/'+patientId+'/guideline-trace')});
  const source = useMutation({mutationFn:(url:string)=>api<{resource:unknown}>(token,url.replace(/^\/api/,''))});
  const trace=query.data;
  return <Panel title="Guideline traceability">
    {query.error&&<Feedback message={query.error.message} error/>}
    {!trace&&!query.error&&<p aria-live="polite">Loading policy and supporting evidence…</p>}
    {trace&&<><dl className="details"><div><dt>Source guideline</dt><dd>pending clinical confirmation</dd></div>
      <div><dt>Policy ID and version</dt><dd>{trace.policy_id||'No active policy'} · version {trace.policy_version||'not established'}</dd></div></dl>
      <h3>Eligibility criteria from policy data</h3>
      {trace.policy_active?<ul>{trace.eligibility_criteria.map(item=><li key={item}>{item}</li>)}</ul>:<p>No active window policy; criteria unavailable.</p>}
      {trace.historical_policy.rules.length>0&&<div className="inset"><strong>{trace.historical_policy.id} v{trace.historical_policy.version}</strong>
      {trace.historical_policy.rules.map(rule=><div key={rule.rule_id}><p>{rule.criteria}</p><p>{rule.triggered?'Historical rule prerequisites met':'Historical rule prerequisites not met'}</p></div>)}<p>pending clinical confirmation</p></div>}
      <h3>Supporting evidence</h3><p>Versioned records supporting the server projection and its recorded context; not a clinical interpretation.</p>
      {!trace.supporting_evidence.length&&<p>No qualifying supporting records available.</p>}
      <ul className="history-sources">{trace.supporting_evidence.map(item=><li key={item.id}><strong>{item.label}</strong>
        {item.provenance.facility?<FacilityChips facility={item.provenance.facility}/>:<p>Facility not recorded</p>}
        <p>Source date: {item.clinical_time?.slice(0,10)||'not recorded'} · version {item.version}</p>
        <a className="text-link" href={item.source_url} onClick={event=>{event.preventDefault();source.mutate(item.source_url);}}>Open source record</a>
      </li>)}</ul>
      {source.isPending&&<p aria-live="polite">Loading source record…</p>}
      {source.error&&<Feedback message={source.error.message} error/>}
      {source.data&&<div className="inset" aria-label="Guideline source viewer"><h3>Source record · untrusted data</h3><pre className="history-document">{displayText(JSON.stringify(source.data.resource,null,2))}</pre></div>}
    </>}
  </Panel>;
}
