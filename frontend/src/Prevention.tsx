import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { demoPatient, displayJson } from './presentation';
import { api } from './api';
import { ClinicalInvestigation } from './ClinicalInvestigation';
import { MultiAgent } from './MultiAgent';
import { Button, Empty, Feedback, Panel, Status } from './ui';
import { label, moment, type Role } from './types';

type Prerequisite = { id: string; category: string; status: string; source_refs: string[]; issues: string[]; evaluated: string; rule_key: string };
export type PreventionDecision = {
  id: string; patient_id: string; obligation_id: string; rationale: string; owner: string; rule_key: string;
  status: string; revision: number; archived: boolean; snapshot_hash: string; created: string;
  source_refs: string[]; last_investigation_id: string | null; record_snapshot_current: boolean;
  timing: { state: string; label: string; due_at: string | null; reason: string };
  timing_policy: { id: string; version: string; source: string; status: string } | null;
  prerequisites: Prerequisite[];
  snapshot: { evidence: { id: string; quality: { state: string } }[]; life_stage_events: [string, string, string][] };
  record: { actor: string; outcome: string; rationale: string; recorded: string; source_refs: string[]; follow_up: string[] } | null;
};
type DecisionEvent = { sequence: number; decision_id: string; patient_id: string; actor: string; action: string; recorded: string; detail: Record<string, unknown> };
type Data = { decisions: PreventionDecision[]; counts: Record<string, number>; history: DecisionEvent[] };
type Props = { token: string; role: Role };
const base = '/v1/prevention';

export function usePrevention(token: string, patientId?: string) {
  return useQuery({ queryKey: ['prevention', token, patientId ?? 'all'],
    queryFn: () => api<Data>(token, base + '/snapshot' + (patientId ? '?patient_id=' + encodeURIComponent(patientId) : '')),
    refetchInterval: 30000 });
}

function useDecisionAction(token: string) {
  const cache = useQueryClient();
  return useMutation({
    mutationFn: ({ path, body }: { path: string; body?: unknown }) => api<unknown>(token, base + path, 'POST', body),
    onSuccess: () => {
      cache.invalidateQueries({ queryKey: ['prevention'] });
      cache.invalidateQueries({ queryKey: ['snapshot', token] });
    },
  });
}

export function PreventionQueue({ token, role }: Props) {
  const data = usePrevention(token);
  const action = useDecisionAction(token);
  const [filter, setFilter] = useState('');
  const active = data.data?.decisions.filter((item) => !item.archived && !['decided', 'cancelled'].includes(item.status)) ?? [];
  const visible = active.filter((item) => !filter || item.status === filter || item.timing.state === filter);
  return <Panel title="Prevention Decision Queue">
    <div className="inset prevention">
      <p className="muted">Synthetic decision tracking. Timing is established only by a registered policy.</p>
      {data.isLoading && <p>Loading decision queue…</p>}
      {data.error && <Feedback message={data.error.message} error />}
      <div className="decision-counts">
        {['awaiting_evidence', 'ready_for_review', 'due_soon', 'overdue'].map((name) =>
          <button key={name} type="button" aria-pressed={filter === name}
            onClick={() => setFilter(filter === name ? '' : name)}>
            <strong>{data.data?.counts[name] ?? '—'}</strong><span>{label(name)}</span>
          </button>)}
      </div>
      {visible.map((item) => <Link className="record-link decision-queue-row" key={item.id}
        to={'/passport?obligation=' + item.obligation_id + '&decision=' + item.id}>
        <div><strong>{demoPatient(item.patient_id)} · Prevention review</strong><small>{item.owner}</small>
          <small>{item.timing_policy ? 'Illustrative timing policy · ' : ''}{item.timing.label}</small></div>
        <Status value={item.status} />
      </Link>)}
      {!data.isLoading && !visible.length && <Empty>No decisions match this queue filter.</Empty>}
      {role === 'coordinator' && <Button variant="outline" disabled={action.isPending}
        onClick={() => action.mutate({ path: '/demo/timing' })}>Load illustrative timing scenario</Button>}
      {action.error && <Feedback message={action.error.message} error />}
    </div>
  </Panel>;
}

function DecisionFacts({ decision }: { decision: PreventionDecision }) {
  return <>
    <p>{decision.rationale}</p>
    <dl className="details">
      <div><dt>Responsible team</dt><dd>{decision.owner}</dd></div>
      <div><dt>Decision lifecycle</dt><dd><Status value={decision.status} /></dd></div>
      <div><dt>Timing</dt><dd>{decision.timing.label}
        {decision.timing.due_at && <small>{moment(decision.timing.due_at)}</small>}</dd></div>
      <div><dt>Timing policy</dt><dd>{decision.timing_policy
        ? <>Illustrative policy · Version {decision.timing_policy.version}
          <small>{decision.timing_policy.source} · {label(decision.timing_policy.status)}</small></>
        : 'No approved timing policy is configured.'}</dd></div>
      <div><dt>Rule provenance</dt><dd><details><summary>Rule details</summary>{decision.rule_key}</details><small>Illustrative readiness registry · clinical review required</small></dd></div>
      <div><dt>Linked obligation</dt><dd><Link to={'/passport?obligation=' + decision.obligation_id}>Open obligation passport</Link></dd></div>
    </dl>
    <h3>Required evidence</h3>
    <p className="muted">Available evidence supports review. The clinician determines clinical sufficiency.</p>
    <ul className="decision-prerequisites">{decision.prerequisites.map((item) => <li key={item.id}>
      <strong>{item.category}</strong> <Status value={item.status} />
      <small>{item.source_refs.length} accessible source records</small>
      {item.issues.length > 0 && <small>{item.issues.map(label).join(', ')}</small>}
      <small>Evaluated {moment(item.evaluated)}</small>
    </li>)}</ul>
    <details><summary>Decision evidence snapshot</summary><p>Snapshot <code>{decision.snapshot_hash}</code></p>
      <p>Source evidence {decision.source_refs.join(', ')}</p>
      <Link className="text-link" to={'/workspace?patient=' + decision.patient_id}>Inspect patient source evidence</Link>
    </details>
    {decision.record && <div className="decision-outcome">
      <h3>Clinical decision recorded</h3><p><strong>{label(decision.record.outcome)}</strong> · {label(decision.record.actor)} · {moment(decision.record.recorded)}</p>
      <p>{decision.record.rationale}</p>
      {!decision.record_snapshot_current && <Feedback message="Decision context changed after recording. A clinician must assess whether further review is needed." error />}
      <details><summary>Supporting evidence references</summary>{decision.record.source_refs.join(', ') || 'Deferral recorded with unresolved evidence'}</details>
      <p className="muted">Clinical obligation closure requires its evidence-specific approval and verification.</p>
    </div>}
  </>;
}

function ReviewControls({ decision, token, role }: Props & { decision: PreventionDecision }) {
  const action = useDecisionAction(token);
  const [note, setNote] = useState('');
  const [outcome, setOutcome] = useState('follow_up_required');
  const [followUp, setFollowUp] = useState('');
  const [refs, setRefs] = useState<string[]>([]);
  const [confirmed, setConfirmed] = useState(false);
  useEffect(() => { setRefs([]); setConfirmed(false); }, [decision.snapshot_hash]);
  const path = '/decisions/' + decision.id;
  const candidates = [...new Set(decision.prerequisites.flatMap((item) => item.source_refs))];
  const unavailable = new Set(decision.snapshot.evidence.filter((item) => item.quality.state === 'unavailable').map((item) => item.id));
  const transition = (value: string) => action.mutate({ path: path + '/transition',
    body: { action: value, revision: decision.revision, rationale: note } });
  return <div className="decision-controls">
    {role === 'reviewer' && !['decided', 'cancelled'].includes(decision.status) && <>
      <label>Clinical decision rationale<textarea value={note} maxLength={decision.status === 'under_review' ? 1000 : 500} onChange={(event) => setNote(event.target.value)} /></label>
      {decision.status !== 'under_review' ? <Button disabled={note.trim().length < 5 || action.isPending}
        onClick={() => transition('begin_review')}>Begin clinician review</Button> : <>
        <label>Clinical decision outcome<select value={outcome} onChange={(event) => setOutcome(event.target.value)}>
          <option value="follow_up_required">Follow-up required</option><option value="deferred">Deferred</option>
          <option value="reconciled">Reconciled by clinician</option><option value="not_applicable">Not applicable</option>
        </select></label>
        <fieldset><legend>Supporting evidence reviewed</legend>
          {candidates.map((id,index) => <div key={id}><label className="decision-checkbox"><input type="checkbox" checked={refs.includes(id)}
            disabled={unavailable.has(id)} onChange={(event) => setRefs(event.target.checked ? [...refs, id] : refs.filter((value) => value !== id))} />
            <span>{decision.prerequisites.find(item=>item.source_refs.includes(id))?.category || 'Supporting evidence'} · source {index+1}{unavailable.has(id) ? ' · Unavailable content' : ''}</span></label><details><summary>Source reference {index+1}</summary>{id}</details></div>)}
          {!candidates.length && <p>No prerequisite evidence is currently accessible.</p>}
        </fieldset>
        <label>Outstanding follow-up actions, one per line<textarea value={followUp} maxLength={5000} onChange={(event) => setFollowUp(event.target.value)} /></label>
        <label className="decision-checkbox"><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />
          I reviewed the current evidence snapshot and take responsibility for this decision.</label>
        <Button disabled={!confirmed || note.trim().length < 5 || action.isPending}
          onClick={() => action.mutate({ path: path + '/record', body: {
            revision: decision.revision, reviewed_snapshot: decision.snapshot_hash,
            outcome, rationale: note, evidence_refs: refs, follow_up: followUp.split('\n').map((line) => line.trim()).filter(Boolean),
          } })}>Record clinical decision</Button>
      </>}
    </>}
    {role === 'coordinator' && !['decided', 'cancelled'].includes(decision.status) && <>
      <label>Escalation or cancellation reason<input value={note} maxLength={500} onChange={(event) => setNote(event.target.value)} /></label>
      <div className="actions">
        <Button variant="outline" disabled={note.trim().length < 5 || action.isPending} onClick={() => transition('escalate')}>Escalate decision</Button>
        <Button variant="outline" disabled={note.trim().length < 5 || action.isPending} onClick={() => transition('cancel')}>Cancel decision</Button>
        {decision.status === 'escalated' && <Button variant="outline" disabled={note.trim().length < 5 || action.isPending}
          onClick={() => transition('resume')}>Resume evidence review</Button>}
      </div>
    </>}
    {role === 'coordinator' && decision.record?.follow_up.map((item, index) => <div className="record-link" key={index}>
      <span>{item}</span><Button variant="outline" disabled={action.isPending}
        onClick={() => action.mutate({ path: path + '/follow-up/' + index })}>Initiate follow-up {index + 1}</Button>
    </div>)}
    {action.error && <Feedback message={action.error.message} error />}
  </div>;
}

export function PreventionPassport({ token, role, obligationId, passport = false }: Props & { obligationId: string; passport?: boolean }) {
  const data = usePrevention(token);
  const [params] = useSearchParams();
  const requested = params.get("decision");
  const visible = data.data?.decisions.filter((item) => !item.archived && item.obligation_id === obligationId
    && (!requested || item.id === requested)) ?? [];
  return <Panel title={passport ? "Current prevention decision" : "Prevention Decision"}>
    <div className="inset prevention">
      {data.error && <Feedback message={data.error.message} error />}
      {visible.map((decision) => <article key={decision.id} className="prevention-decision" id={'decision-' + decision.id}>
        {passport?<><div className="passport-decision-summary"><Status value={decision.status}/><strong>{decision.owner}</strong><span>Next step: <Link className="text-link" to={'/resolution?obligation=' + obligationId + '&decision=' + decision.id}>Open decision readiness investigation</Link></span><p>{decision.timing.label}{decision.timing.due_at&&<> · {moment(decision.timing.due_at)}</>}</p></div><details className="passport-technical"><summary>Required evidence, timing policy and decision snapshot</summary><DecisionFacts decision={decision}/></details></>:<DecisionFacts decision={decision} />}
        {!passport&&<Link className="text-link" to={'/resolution?obligation=' + obligationId + '&decision=' + decision.id}>Open decision readiness investigation</Link>}
        <ReviewControls key={decision.id} decision={decision} token={token} role={role} />
      </article>)}
      {data.isLoading && <p>Loading prevention decisions…</p>}
      {!data.isLoading && !visible.length && <>{passport?<p className="passport-decision-empty">No prevention decision is linked to this obligation.</p>:<Empty>No prevention decision is linked to this obligation.</Empty>}</>}
    </div>
  </Panel>;
}

export function DecisionReadiness({ token, role, patientId }: Props & { patientId: string }) {
  const data = usePrevention(token, patientId);
  const [params, setParams] = useSearchParams();
  const selected = params.get("decision");
  const visible = data.data?.decisions.filter((item) => !item.archived) ?? [];
  const decision = selected ? visible.find((item) => item.id === selected)
    : visible.find((item) => !['decided', 'cancelled'].includes(item.status)) ?? visible[0];
  return <>
    <Panel title="Prevention review case">
      <div className="inset prevention">
        <label>Selected prevention decision<select value={decision?.id ?? ''} onChange={(event) => {
          const value = event.target.value;
          setParams((current) => {
            const next = new URLSearchParams(current);
            next.set("decision", value);
            return next;
          });
        }}>
          {!decision && <option value="" disabled>Choose a decision</option>}
          {visible.map((item) => <option key={item.id} value={item.id}>{label(item.status)} · {moment(item.created)}</option>)}
        </select></label>
        {decision ? <><p>{decision.rationale}</p>
          <ul>{decision.prerequisites.map((item) => <li key={item.id}>{item.category} · {label(item.status)}</li>)}</ul>
          <p>{decision.timing.label}</p>
          <Link className="text-link" to={'/passport?obligation=' + decision.obligation_id + '&decision=' + decision.id}>Open prevention decision and clinician controls</Link>
        </> : <Empty>No prevention decision available.</Empty>}
        {data.error && <Feedback message={data.error.message} error />}
      </div>
    </Panel>
    {decision && !['decided', 'cancelled'].includes(decision.status) && <MultiAgent key={decision.id + '-multi'} decisionId={decision.id} patientId={patientId} token={token} role={role} />}
    {decision && !['decided', 'cancelled'].includes(decision.status) &&
      <ClinicalInvestigation key={decision.id} decisionId={decision.id} patientId={patientId} token={token} role={role} />}
  </>;
}

function TimelineEvents({ decision }: { decision: PreventionDecision }) {
  const entries = [
    ...decision.snapshot.life_stage_events.map(([id, stage, at]) => ({ id, at, title: label(stage) + " life-stage event", text: id })),
    { id: "created", at: decision.created, title: "Decision created", text: decision.owner },
    ...decision.prerequisites.map((item) => ({ id: item.id, at: item.evaluated, title: item.category, text: label(item.status) })),
    ...(decision.record ? [{ id: "recorded", at: decision.record.recorded, title: label(decision.record.outcome), text: decision.record.rationale }] : []),
  ].sort((first, second) => Date.parse(first.at) - Date.parse(second.at));
  return <ul className="timeline">{entries.map((item) => <li key={item.id}>
    <strong>{item.title}</strong><small>{moment(item.at)} · {item.text}</small>
  </li>)}</ul>;
}

export function DecisionTimeline({ token, patientId }: { token: string; patientId: string }) {
  const data = usePrevention(token, patientId);
  const active = data.data?.decisions.filter((item) => !item.archived) ?? [];
  return <Panel title="Decision Timeline"><div className="inset prevention">
    {active.map((item) => <div key={item.id}>
      <Link to={'/passport?obligation=' + item.obligation_id}><strong>Prevention review · {label(item.status)}</strong></Link>
      <p>Assigned to {item.owner} · {item.timing.label}</p>
      <TimelineEvents decision={item} />
    </div>)}
    {data.isLoading && <p>Loading decision timeline…</p>}
    {!data.isLoading && !active.length && <Empty>No active prevention decisions.</Empty>}
    {data.error && <Feedback message={data.error.message} error />}
  </div></Panel>;
}

export function DecisionHistory({ token }: { token: string }) {
  const data = usePrevention(token);
  return <Panel title="Decision History"><div className="inset prevention">
    <p className="muted">Evidence retrieval, clinician review, decision recording, follow-up and verified obligation closure are recorded as separate events.</p>
    <ul className="timeline">{data.data?.history.slice().reverse().slice(0, 100).map((item) => <li key={item.sequence}>
      <strong>{label(item.action)}</strong><small>{moment(item.recorded)} · {label(item.actor)} · {demoPatient(item.patient_id)}</small>
      <details><summary>Decision identifier</summary>{item.decision_id}</details>
      <details><summary>Inspect decision audit event</summary><pre>{displayJson(item.detail)}</pre></details>
    </li>)}</ul>
    {!data.data?.history.length && <Empty>No decision history recorded.</Empty>}
    {data.error && <Feedback message={data.error.message} error />}
  </div></Panel>;
}
