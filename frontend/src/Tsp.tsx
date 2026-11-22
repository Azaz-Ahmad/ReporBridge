import { CalendarDays } from 'lucide-react';
import { WorkspaceDetails } from './WorkspaceDetails';
import {ExplanationOutput,type ExplanationProjection} from './ExplanationOutput';
import { useState, type ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { demoPatient } from './presentation';
import { api } from './api';
import { Button, Feedback, Panel } from './ui';
import type { Role } from './types';

type Clock = { demo_mode: boolean; as_of: string; label: string; timezone: string };
export type WindowResult = { patient_id: string; status: string; as_of: string; policy_id: string | null;
  policy_version: string | null; citation: string; clinical_confirmation: string;
  window_start: string | null; window_end: string | null; active_window?: string;
  clock: Clock; inputs_used: { source_id: string; version: string; source_date: string; due_date: string | null }[];
  missing_evidence: string[]; reviewer_questions: string[]; obligation_ids: string[];
  windows: { id: string; label: string; status: string; window_start: string; window_end: string; completion_date: string | null }[];
  completion_verified: boolean };

function WindowBadge({ value }: { value: string }) {
  const color = value === 'HOLD_DATING_UNCERTAIN' || value === 'WINDOW_PASSED' ? 'rose' : value.startsWith('COMPLETED') ? 'green' : 'amber';
  return <span className={'pill ' + color} data-testid="tsp-status">{value.replaceAll('_', ' ')}</span>;
}

export function DemoClock({ token, role, controls = false }: { token: string; role: Role; controls?: boolean }) {
  const cache = useQueryClient();
  const [date, setDate] = useState('');
  const current = useQuery({ queryKey: ['tsp', 'clock', token], queryFn: () => api<Clock>(token, '/v1/tsp/clock') });
  const change = useMutation({ mutationFn: (reset: boolean) => api<Clock>(token, '/v1/tsp/clock' + (reset ? '/reset' : ''), 'POST', reset ? undefined : { as_of: date }),
    onSuccess: () => { setDate(''); cache.invalidateQueries({ queryKey: ['tsp'] }); cache.invalidateQueries({ queryKey: ['historical-candidates'] }); cache.invalidateQueries({ queryKey: ['history'] }); } });
  if (current.error) return <Feedback message={current.error.message} error />;
  if (!current.data?.demo_mode) return null;
  if (!controls) return <aside className="tsp-clock-chip" aria-label="Demo clock banner">Demo date: {current.data.as_of} · synthetic</aside>;
  return <aside className="tsp-clock" aria-label="Demo clock controls"><div><strong>DEMO CLOCK — synthetic dates</strong>
    <p>As of {current.data.as_of} · Asia/Dubai. System time is unchanged.</p></div>
    {role === 'coordinator' && <form onSubmit={(event) => { event.preventDefault(); change.mutate(false); }}>
      <label>Demo as-of date<input type="date" required value={date || current.data.as_of} onChange={(event) => setDate(event.target.value)} /></label>
      <Button type="submit" disabled={!date || change.isPending}>Apply demo date</Button>
      <Button type="button" variant="outline" disabled={change.isPending} onClick={() => change.mutate(true)}>Reset demo date</Button>
    </form>}{change.error && <Feedback message={change.error.message} error />}</aside>;
}

export function TspQueue({ token, role }: { token: string; role?: Role }) {
  const [confirmReset, setConfirmReset] = useState(false);
  const cache = useQueryClient();
  const clock = useQuery({ queryKey: ['tsp', 'clock', token], queryFn: () => api<Clock>(token, '/v1/tsp/clock') });
  const fixture = useMutation({ mutationFn: (reset: boolean) => api(token, '/v1/tsp/demo/' + (reset ? 'reset' : 'seed'), 'POST'),
    onSuccess: () => { cache.invalidateQueries({ queryKey: ['tsp'] }); cache.invalidateQueries({ queryKey: ['historical-candidates'] }); cache.invalidateQueries({ queryKey: ['snapshot'] }); cache.invalidateQueries({ queryKey: ['prevention'] }); } });
  const query = useQuery({ queryKey: ['tsp', 'queue', token], queryFn: () => api<WindowResult[]>(token, '/v1/tsp/queue') });
  return <Panel title="Time-Sensitive Prevention Windows"><p className="muted">Illustrative policy · pending clinical confirmation</p>
    {clock.data?.demo_mode && role === 'coordinator' && <div className="actions">
      <Button disabled={fixture.isPending} onClick={() => fixture.mutate(false)}>Load TSP demo</Button>
      <Button variant="outline" disabled={fixture.isPending} onClick={() => setConfirmReset(true)}>Reset TSP demo</Button>
      {confirmReset && <div role="group" aria-label="Confirm TSP reset"><p>Restore synthetic fixtures and the default demo date. Amira’s previous demo run is archived.</p><Button variant="danger" disabled={fixture.isPending} onClick={() => fixture.mutate(true,{onSuccess:()=>setConfirmReset(false)})}>Confirm reset TSP demo</Button><Button variant="outline" disabled={fixture.isPending} onClick={()=>setConfirmReset(false)}>Cancel reset</Button></div>}
    </div>}{fixture.error && <Feedback message={fixture.error.message} error />}
    {query.error && <Feedback message={query.error.message} error />}
    {!query.data?.length && <p>No authorized synthetic windows available.</p>}
    {!!query.data?.length && <div className="table-wrap"><table><thead><tr><th>Patient</th><th>Status</th><th>Window dates</th><th>Review</th></tr></thead>
      <tbody>{query.data.map((item) => <tr key={item.patient_id}><td>{demoPatient(item.patient_id)}</td><td><WindowBadge value={item.status} /></td>
        <td>{item.window_start ? `${item.window_start} – ${item.window_end}` : 'No established window'}</td>
        <td><Link className="text-link" to={item.obligation_ids[0] ? '/passport?obligation=' + item.obligation_ids[0] : '/workspace?patient=' + item.patient_id}>Review window</Link></td></tr>)}</tbody></table></div>}
  </Panel>;
}

export function TspWindow({ token, patientId, timeline = false, role, compact = false, passport = false, owner, nextAction }: { token: string; patientId: string; timeline?: boolean; role?: Role; compact?: boolean; passport?: boolean; owner?: string; nextAction?: ReactNode }) {
  const query = useQuery({ queryKey: ['tsp', 'patient', patientId, token], queryFn: () => api<WindowResult>(token, '/v1/tsp/patients/' + patientId + '/window') });
  const cache = useQueryClient();
  const fixture = useMutation({ mutationFn: (action: string) => api(token, '/v1/tsp/demo/obligations/' + query.data?.obligation_ids[0] + '/' + action, 'POST'),
    onSuccess: () => { cache.invalidateQueries({ queryKey: ['tsp'] }); cache.invalidateQueries({ queryKey: ['historical-candidates'] }); cache.invalidateQueries({ queryKey: ['snapshot'] }); cache.invalidateQueries({ queryKey: ['prevention'] }); } });
  const explain = useMutation({ mutationFn: () => api<{ id: string; detail: { explanation?:ExplanationProjection;trace?:string[];error?: string | null; packet: { summary: string; abstained: boolean } | null } }>(token, '/v1/tsp/patients/' + patientId + '/explanations', 'POST', { request_id: crypto.randomUUID() }) });
  const item = query.data;
  if(passport)return <section className="panel passport-window-hero" aria-label="Time-Sensitive Prevention Window" id="passport-time-window">
    <div className="panel-heading"><h2><CalendarDays size={24}/>Time-Sensitive Prevention Window</h2><span>Server-calculated timing</span></div>
    {query.isPending&&<p role="status">Loading prevention window…</p>}{query.error&&<Feedback message={query.error.message} error/>}
    {item&&<><div className="passport-window-headline"><div><WindowBadge value={item.status}/><h3>{item.status==='HOLD_DATING_UNCERTAIN'?'HOLD — DATING UNCERTAIN':!item.policy_id||item.status==='NO_POLICY'?'Timing not established':item.active_window?'Current window: '+item.active_window:'No window established'}</h3>
      {item.status==='HOLD_DATING_UNCERTAIN'?<p>No prevention window can be established until the required dating evidence is confirmed.</p>:item.policy_id&&item.window_start&&item.window_end?<p className="passport-window-dates">{item.window_start} → <strong>{item.window_end}</strong> (inclusive)</p>:<p>No timing deadline is established in the current calculator result.</p>}
      <small>As of {item.as_of} · {item.clock.demo_mode?'demo calendar':'Asia/Dubai calendar'}</small></div>
      <div className="passport-window-owner"><span className="field-kicker">Responsible owner</span><strong>{owner||'Not recorded'}</strong>{nextAction&&<><span className="field-kicker">Configured next action</span>{nextAction}</>}</div></div>
      {item.policy_id&&item.clinical_confirmation==='pending clinical confirmation'&&<p className="passport-policy-notice">Illustrative policy — Pending clinical confirmation</p>}
      {item.status!=='HOLD_DATING_UNCERTAIN'&&item.policy_id&&!!item.windows.length&&<ol className="tsp-windows">{item.windows.map(window=><li key={window.id}><strong>{window.id} · {window.label}</strong><p><time>{window.window_start}</time> – <time>{window.window_end}</time> (inclusive)</p><WindowBadge value={window.status}/>
        {window.completion_date&&<p>Qualifying evidence date: {window.completion_date}. {item.completion_verified?'Closure verified through existing gates.':'Evidence presence does not close an obligation.'}</p>}</li>)}</ol>}
      {!!item.missing_evidence.length&&<div className="passport-window-blockers"><strong>Missing / conflicting timing inputs</strong>{item.missing_evidence.map(message=><p key={message}>{message}</p>)}</div>}
      {item.reviewer_questions.map(question=><p key={question}>{question}</p>)}
    </>}
    {role==='coordinator'&&!timeline&&<Button disabled={explain.isPending} onClick={()=>explain.mutate()}>Explain computed window</Button>}
    {explain.error&&<Feedback message={explain.error.message} error/>}{explain.data?.detail.error&&<Feedback message={'Explanation unavailable: '+explain.data.detail.error} error/>}
    {explain.data&&<div className="inset passport-window-explanation"><p>Explanation · mandatory human review</p><ExplanationOutput detail={explain.data.detail}/>{!explain.data.detail.explanation&&<p>{explain.data.detail.packet?.summary}</p>}</div>}
    {item?.clock.demo_mode&&role==='coordinator'&&!timeline&&patientId==='demo-amira'&&item.obligation_ids.length>0&&<details className="passport-technical"><summary>Synthetic evidence controls · demonstration only</summary><div className="actions"><Button variant="outline" disabled={fixture.isPending} onClick={()=>fixture.mutate('completion')}>Add dated synthetic result</Button><Button variant="outline" disabled={fixture.isPending} onClick={()=>fixture.mutate('invalidate')}>Invalidate TSP result</Button></div></details>}
    {fixture.error&&<Feedback message={fixture.error.message} error/>}
  </section>;
  if(compact && timeline)return <Panel title="Prevention Windows"><p className="workspace-section-note">From configured policy — illustrative.</p>
    {query.isPending&&<p role="status">Loading prevention windows…</p>}{query.error&&<Feedback message={query.error.message} error/>}
    {item&&<>{item.windows.length?<ol className="tsp-windows">{item.windows.map(window=><li key={window.id}><strong>{window.id} · {window.label}</strong><p><time>{window.window_start}</time> – <time>{window.window_end}</time> (inclusive)</p><WindowBadge value={window.status}/>
      {window.completion_date&&<p>Qualifying evidence date: {window.completion_date}. {item.completion_verified?'Closure verified through existing gates.':'Evidence presence does not close an obligation.'}</p>}</li>)}</ol>:<><WindowBadge value={item.status}/><p>No established window</p></>}
      <div className="workspace-window-footer"><small>As of {item.as_of} · {item.clock.demo_mode?'DEMO CLOCK':'Asia/Dubai calendar'}</small><strong className="tsp-citation">pending clinical confirmation</strong>
      <details><summary>Policy Details</summary><p>Policy {item.policy_id||'not established'} · version {item.policy_version||'none'}</p><p>Dates are computed by the deterministic policy service. No glucose values are interpreted. Due soon means the seven days before a window opens; window endpoints are inclusive.</p><p>Server status: {item.status.replaceAll('_',' ')}</p></details></div></>}
  </Panel>;
  return <Panel title={compact ? 'Prevention windows' : timeline ? 'Prevention window timeline' : 'Time-Sensitive Prevention Window'}>
    {!timeline && role && <DemoClock token={token} role={role} controls />}
    {compact && query.isPending && <p role="status">Loading prevention windows…</p>}
    {query.error && <Feedback message={query.error.message} error />}
    {role === 'coordinator' && !timeline && <Button disabled={explain.isPending} onClick={() => explain.mutate()}>Explain computed window</Button>}
    {explain.error && <Feedback message={explain.error.message} error />}
    {explain.data?.detail.error && <Feedback message={"Explanation unavailable: "+explain.data.detail.error} error />}
    {explain.data && <div className="inset"><p>Explanation · mandatory human review</p><ExplanationOutput detail={explain.data.detail}/>{!explain.data.detail.explanation&&<p>{explain.data.detail.packet?.summary}</p>}</div>}
    {item?.clock.demo_mode && role === 'coordinator' && !timeline && patientId === 'demo-amira' && item.obligation_ids.length > 0 && <div className="actions">
      <Button variant="outline" disabled={fixture.isPending} onClick={() => fixture.mutate('completion')}>Add dated synthetic result</Button>
      <Button variant="outline" disabled={fixture.isPending} onClick={() => fixture.mutate('invalidate')}>Invalidate TSP result</Button>
    </div>}{fixture.error && <Feedback message={fixture.error.message} error />}
    {item && <><WindowBadge value={item.status} /><p>As of {item.as_of} · {item.clock.demo_mode ? 'DEMO CLOCK' : 'Asia/Dubai calendar'}</p>
      <details><summary>Policy details</summary>Policy {item.policy_id || 'not established'} · version {item.policy_version || 'none'}</details>
      <p><strong className="tsp-citation">pending clinical confirmation</strong></p>
      <WorkspaceDetails compact={compact} title="How to read these windows"><p>Dates are computed by the deterministic policy service. No glucose values are interpreted. Due soon means the seven days before a window opens; window endpoints are inclusive.</p></WorkspaceDetails>
      {item.windows.length ? <ol className="tsp-windows">{item.windows.map((window) => <li key={window.id}>
        <strong>{window.id} · {window.label}</strong> <WindowBadge value={window.status} />
        <p><time>{window.window_start}</time> – <time>{window.window_end}</time> (inclusive)</p>
        {window.completion_date && <p>Qualifying evidence date: {window.completion_date}. {item.completion_verified ? 'Closure verified through existing gates.' : 'Evidence presence does not close an obligation.'}</p>}
      </li>)}</ol> : <p>No established window</p>}
      {!timeline && <><h3>Inputs used</h3>{item.inputs_used.map((input) => <div key={input.source_id}>Source date value {input.source_date} · version {input.version}<details><summary>Source reference</summary>{input.source_id}</details> {input.due_date ? `· EDD ${input.due_date}` : '· registration date'}</div>)}
        <h3>Missing evidence / reason for review</h3>{!item.missing_evidence.length && <p>No dating evidence gaps. Clinician review and approval remain required.</p>}
        {item.missing_evidence.map((message) => <p key={message}>{message}</p>)}
        {item.reviewer_questions.map((question) => <p key={question}>{question}</p>)}</>}
    </>}
  </Panel>;
}
