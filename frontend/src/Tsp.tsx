import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api } from './api';
import { Button, Feedback, Panel } from './ui';
import type { Role } from './types';

type Clock = { demo_mode: boolean; as_of: string; label: string; timezone: string };
export type WindowResult = { patient_id: string; status: string; as_of: string; policy_id: string | null;
  policy_version: string | null; citation: string; clinical_confirmation: string;
  window_start: string | null; window_end: string | null; active_window?: string;
  clock: Clock; inputs_used: { source_id: string; version: string; source_date: string; due_date: string }[];
  missing_evidence: string[]; reviewer_questions: string[]; obligation_ids: string[];
  windows: { id: string; label: string; status: string; window_start: string; window_end: string; completion_date: string | null }[];
  completion_verified: boolean };

function WindowBadge({ value }: { value: string }) {
  const color = value === 'HOLD_DATING_UNCERTAIN' || value === 'WINDOW_PASSED' ? 'rose' : value.startsWith('COMPLETED') ? 'green' : 'amber';
  return <span className={'pill ' + color} data-testid="tsp-status">{value.replaceAll('_', ' ')}</span>;
}

export function DemoClock({ token, role }: { token: string; role: Role }) {
  const cache = useQueryClient();
  const [date, setDate] = useState('');
  const current = useQuery({ queryKey: ['tsp', 'clock', token], queryFn: () => api<Clock>(token, '/v1/tsp/clock') });
  const change = useMutation({ mutationFn: (reset: boolean) => api<Clock>(token, '/v1/tsp/clock' + (reset ? '/reset' : ''), 'POST', reset ? undefined : { as_of: date }),
    onSuccess: () => { setDate(''); cache.invalidateQueries({ queryKey: ['tsp'] }); } });
  if (current.error) return <Feedback message={current.error.message} error />;
  if (!current.data?.demo_mode) return null;
  return <aside className="tsp-clock" aria-label="Demo clock banner"><div><strong>DEMO CLOCK — synthetic dates</strong>
    <p>As of {current.data.as_of} · Asia/Dubai. System time is unchanged.</p></div>
    {role === 'coordinator' && <form onSubmit={(event) => { event.preventDefault(); change.mutate(false); }}>
      <label>Demo as-of date<input type="date" required value={date || current.data.as_of} onChange={(event) => setDate(event.target.value)} /></label>
      <Button type="submit" disabled={!date || change.isPending}>Apply demo date</Button>
      <Button type="button" variant="outline" disabled={change.isPending} onClick={() => change.mutate(true)}>Reset demo date</Button>
    </form>}{change.error && <Feedback message={change.error.message} error />}</aside>;
}

export function TspQueue({ token, role }: { token: string; role?: Role }) {
  const cache = useQueryClient();
  const clock = useQuery({ queryKey: ['tsp', 'clock', token], queryFn: () => api<Clock>(token, '/v1/tsp/clock') });
  const fixture = useMutation({ mutationFn: (reset: boolean) => api(token, '/v1/tsp/demo/' + (reset ? 'reset' : 'seed'), 'POST'),
    onSuccess: () => { cache.invalidateQueries({ queryKey: ['tsp'] }); cache.invalidateQueries({ queryKey: ['snapshot'] }); cache.invalidateQueries({ queryKey: ['prevention'] }); } });
  const query = useQuery({ queryKey: ['tsp', 'queue', token], queryFn: () => api<WindowResult[]>(token, '/v1/tsp/queue') });
  return <Panel title="Time-Sensitive Prevention Windows"><p className="muted">Illustrative policy · pending clinical confirmation</p>
    {clock.data?.demo_mode && role === 'coordinator' && <div className="actions">
      <Button disabled={fixture.isPending} onClick={() => fixture.mutate(false)}>Load TSP demo</Button>
      <Button variant="outline" disabled={fixture.isPending} onClick={() => fixture.mutate(true)}>Reset TSP demo</Button>
    </div>}{fixture.error && <Feedback message={fixture.error.message} error />}
    {query.error && <Feedback message={query.error.message} error />}
    {!query.data?.length && <p>No authorized synthetic windows available.</p>}
    {!!query.data?.length && <div className="table-wrap"><table><thead><tr><th>Patient</th><th>Status</th><th>Window dates</th><th>Review</th></tr></thead>
      <tbody>{query.data.map((item) => <tr key={item.patient_id}><td>{item.patient_id}</td><td><WindowBadge value={item.status} /></td>
        <td>{item.window_start ? `${item.window_start} – ${item.window_end}` : 'No established window'}</td>
        <td><Link className="text-link" to={item.obligation_ids[0] ? '/passport?obligation=' + item.obligation_ids[0] : '/workspace?patient=' + item.patient_id}>Review window</Link></td></tr>)}</tbody></table></div>}
  </Panel>;
}

export function TspWindow({ token, patientId, timeline = false, role }: { token: string; patientId: string; timeline?: boolean; role?: Role }) {
  const query = useQuery({ queryKey: ['tsp', 'patient', patientId, token], queryFn: () => api<WindowResult>(token, '/v1/tsp/patients/' + patientId + '/window') });
  const cache = useQueryClient();
  const fixture = useMutation({ mutationFn: (action: string) => api(token, '/v1/tsp/demo/obligations/' + query.data?.obligation_ids[0] + '/' + action, 'POST'),
    onSuccess: () => { cache.invalidateQueries({ queryKey: ['tsp'] }); cache.invalidateQueries({ queryKey: ['snapshot'] }); cache.invalidateQueries({ queryKey: ['prevention'] }); } });
  const explain = useMutation({ mutationFn: () => api<{ id: string; detail: { packet: { summary: string; abstained: boolean } | null } }>(token, '/v1/tsp/patients/' + patientId + '/investigations', 'POST', { request_id: crypto.randomUUID() }) });
  const item = query.data;
  return <Panel title={timeline ? 'Prevention window timeline' : 'Time-Sensitive Prevention Window'}>
    {query.error && <Feedback message={query.error.message} error />}
    {role === 'coordinator' && !timeline && <Button disabled={explain.isPending} onClick={() => explain.mutate()}>Explain computed window</Button>}
    {explain.error && <Feedback message={explain.error.message} error />}
    {explain.data && <div className="inset"><p>Investigation {explain.data.id} · mandatory human review</p><p>{explain.data.detail.packet?.summary}</p></div>}
    {item?.clock.demo_mode && role === 'coordinator' && !timeline && patientId === 'demo-amira' && item.obligation_ids.length > 0 && <div className="actions">
      <Button variant="outline" disabled={fixture.isPending} onClick={() => fixture.mutate('completion')}>Add dated synthetic result</Button>
      <Button variant="outline" disabled={fixture.isPending} onClick={() => fixture.mutate('invalidate')}>Invalidate TSP result</Button>
    </div>}{fixture.error && <Feedback message={fixture.error.message} error />}
    {item && <><WindowBadge value={item.status} /><p>As of {item.as_of} · {item.clock.demo_mode ? 'DEMO CLOCK' : 'Asia/Dubai calendar'}</p>
      <p>Policy {item.policy_id || 'not established'} · version {item.policy_version || 'none'}</p>
      <p><strong>pending clinical confirmation</strong><br /><code className="tsp-citation">{item.citation}</code></p>
      <p>Dates are computed by the deterministic policy service. No glucose values are interpreted. Due soon means the seven days before a window opens; window endpoints are inclusive.</p>
      {item.windows.length ? <ol className="tsp-windows">{item.windows.map((window) => <li key={window.id}>
        <strong>{window.id} · {window.label}</strong> <WindowBadge value={window.status} />
        <p><time>{window.window_start}</time> – <time>{window.window_end}</time> (inclusive)</p>
        {window.completion_date && <p>Qualifying evidence date: {window.completion_date}. {item.completion_verified ? 'Closure verified through existing gates.' : 'Evidence presence does not close an obligation.'}</p>}
      </li>)}</ol> : <p>No established window</p>}
      {!timeline && <><h3>Inputs used</h3>{item.inputs_used.map((input) => <p key={input.source_id}>{input.source_id} · version {input.version} · source {input.source_date} · EDD {input.due_date}</p>)}
        <h3>Missing evidence / reason for review</h3>{!item.missing_evidence.length && <p>No dating evidence gaps. Clinician review and approval remain required.</p>}
        {item.missing_evidence.map((message) => <p key={message}>{message}</p>)}
        {item.reviewer_questions.map((question) => <p key={question}>{question}</p>)}</>}
    </>}
  </Panel>;
}
