import { displayJson, displayText } from './presentation';
import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { api } from './api';
import { Button, Empty, Feedback, Panel, Status } from './ui';
import { label, type Role } from './types';

type Support = { evidence_id: string; version: number; excerpt: string; value_key: string; value_json: string };
type Finding = { finding_id: string; statement: string; supporting_sources: Support[] };
type Agent = { agent_id: string; state: string; task_objective: string; findings: Finding[]; uncertainty: string[];
  error: string | null; validation_status: string; model_identifier: string;
  execution_metadata: { model_calls?: number; duration_ms?: number; reported_model?: string; response_id?: string; validation_errors?: string[] };
  validated_output: Record<string, unknown> | null };
type Packet = { summary: string; packet_complete: boolean; abstained: boolean; grounding_status: string;
  requires_human_review: boolean; findings: Finding[]; missing_information: string[]; conflicting_evidence: string[];
  uncertainty: string[]; administrative_follow_up_proposals: string[];
  timing: { label: string; due_at: string | null }; timing_policy: { id: string; version: string } | null;
  prerequisites: { id: string; category: string; status: string }[];
  source_references: { evidence_id: string; version: number; citation: string; quality_state: string }[] };
type Accounting = { model_calls: number; tool_calls: number; tool_requests: number; cache_hits: number;
  input_tokens: number; output_tokens: number; total_latency_ms: number; cumulative_model_latency_ms: number;
  tool_latency_ms: number; context_peak_characters: number; retries: number;
  agents: Record<string, { model_calls: number; input_tokens: number; output_tokens: number; model_latency_ms: number; tool_calls: number }> };
type Run = { id: string; created: string; status: string; review: { decision: string; note: string } | null;
  detail: { workflow?: string; question: string; decision_context?: { decision_id: string } | null; error: string | null;
    packet: Packet | null; trace: string[]; duration_ms: number; configuration: { model: string };
    usage: { model_calls: number; input_tokens: number; output_tokens: number; usage_complete: boolean };
    tool_history: { name: string; call_id: string; status: string; duration_ms: number; cached?: boolean; evidence_ids: string[] }[];
    multi_agent?: { summary?: Accounting; execution_profile?: string; parallel_enabled?: boolean; sealed_context?: { id: string; sealed_at: string };
      agents: Record<string, Agent>; routing: { agent_id: string; selected: boolean; reason: string; at: string }[] } } };
const base = '/v1/agents/clinical-evidence';
const names: Record<string, string> = { A01: 'Clinical Evidence Investigation', A02: 'Evidence Reconciliation Agent',
  A03: 'Clinical Context Agent', A04: 'Evidence Gap Agent' };
function Findings({ items }: { items: Finding[] }) {
  return <ul>{items.map((f, i) => <li key={i}><p>{f.statement}</p>
    <small>Source-linked interpretation · clinician review required</small>
    {f.supporting_sources.map((s, index) => <div key={index}>
      <small>{s.evidence_id} · Version {s.version}</small>
      {s.excerpt && <blockquote>{s.excerpt}</blockquote>}
      {s.value_key && <p>{s.value_key} · {s.value_json}</p>}
    </div>)}</li>)}</ul>;
}
function SpecialistDetails({ agent }: { agent: Agent }) {
  const output = agent.validated_output;
  if (!output) return null;
  if (agent.agent_id === 'A02') return <div>
    <h4>Source reconciliation</h4>
    <p>Conflicting records: {(output.conflicting_records as string[] ?? []).join(', ') || 'None in retrieved inventory'}</p>
    <p>Corrected records: {(output.corrected_records as string[] ?? []).join(', ') || 'None in retrieved inventory'}</p>
    <ul>{(output.supersession_relationships as { previous_id: string; current_id: string }[] ?? []).map((x, i) => <li key={i}>{x.previous_id} → {x.current_id}</li>)}</ul>
    <p>Source lineage does not establish clinical authority.</p>
  </div>;
  if (agent.agent_id === 'A03') return <div><h4>Documented chronology</h4>
    <ol>{(output.timeline_events as { evidence_id: string; clinical_time: string }[] ?? []).map((x, i) => <li key={i}>{x.clinical_time}<small>Source {x.evidence_id}</small></li>)}</ol>
    <p>Linked obligations: {(output.linked_obligations as string[] ?? []).join(', ') || 'None selected'}</p>
    <p>Life-stage event references: {(output.life_stage_transition_refs as string[] ?? []).join(', ') || 'None selected'}</p>
  </div>;
  if (agent.agent_id === 'A04') return <div><h4>Proposed clinician questions</h4>
    <ul>{(output.unresolved_questions as string[] ?? []).map((x, i) => <li key={i}>{x}</li>)}</ul>
    <p>Questions are review proposals. Configured prerequisite states appear in the unified packet.</p>
  </div>;
  return null;
}
function ExecutionSummary({ run }: { run: Run }) {
  const detail = run.detail;
  const summary = detail.multi_agent?.summary;
  const routing = detail.multi_agent?.routing ?? [];
  const selected = routing.filter(x => x.selected).map(x => x.agent_id);
  const skipped = routing.filter(x => !x.selected);
  const metrics = [
    ['Model calls', detail.usage.model_calls.toLocaleString()],
    ['M08 executions', (summary?.tool_calls ?? detail.tool_history.filter(x => !x.cached).length).toLocaleString()],
    ['Input tokens', detail.usage.input_tokens.toLocaleString()],
    ['Output tokens', detail.usage.output_tokens.toLocaleString()],
    ['Total duration', (detail.duration_ms / 1000).toFixed(1) + ' s'],
    ['Grounding', detail.packet ? label(detail.packet.grounding_status) : 'Pending validation'],
  ];
  return <section className="execution-summary" aria-label="Persisted execution summary">
    <h3>Execution summary</h3>
    <p>Selected agents · {selected.length ? selected.join(', ') : 'Routing pending'}</p>
    <dl className="execution-metrics">{metrics.map(([name, value]) => <div key={name}><dt>{name}</dt><dd>{value}</dd></div>)}</dl>
    <p>{detail.packet ? (detail.packet.abstained ? 'Abstained · ' : 'Summary proposed · ') : ''}
      Human review required</p>
    {summary ? <p className="muted">Cumulative model time {(summary.cumulative_model_latency_ms / 1000).toFixed(1)} s ·
      tool time {(summary.tool_latency_ms / 1000).toFixed(1)} s · {summary.cache_hits} cache hits · {summary.retries} retries
      · peak input context {summary.context_peak_characters.toLocaleString()} characters</p>
      : <p className="muted">{run.status === 'running' ? 'Invocation metrics will appear as persisted calls complete.'
        : 'Per-call model timing and context size were not recorded in this legacy trace.'}</p>}
    {skipped.length > 0 && <details><summary>Skipped agents and reasons</summary>
      <ul>{skipped.map(x => <li key={x.agent_id}><strong>{x.agent_id} · {names[x.agent_id]}</strong><p>{x.reason}</p></li>)}</ul>
    </details>}
    {detail.multi_agent?.sealed_context && <details><summary>Pinned evidence context</summary>
      <p>Sealed at {detail.multi_agent.sealed_context.sealed_at}</p><small>{detail.multi_agent.sealed_context.id}</small>
      <p>Versions and hashes are rechecked before publication and human review.</p></details>}
  </section>;
}
export function MultiAgent({ token, role, patientId, decisionId }: { token: string; role: Role; patientId: string; decisionId?: string }) {
  const [question, setQuestion] = useState('Review the documented clinical evidence, reconcile source discrepancies and identify unresolved decision prerequisites.');
  const [attested, setAttested] = useState(false);
  const [selected, setSelected] = useState('');
  const [requestId, setRequestId] = useState(() => crypto.randomUUID());
  const [note, setNote] = useState('');
  const [sourceId, setSourceId] = useState('');
  const provider = useQuery({ queryKey: ['evidence-provider', token], queryFn: () => api<{ available: boolean; status: string; configuration: { model: string } }>(token, base + '/status') });
  const runs = useQuery({ queryKey: ['multi-agent-runs', token, patientId, decisionId],
    queryFn: () => api<Run[]>(token, base + '/runs?patient_id=' + encodeURIComponent(patientId))
      .then(items => items.filter(r => r.detail.workflow === 'multi_agent' && (!decisionId || r.detail.decision_context?.decision_id === decisionId))),
    refetchInterval: 1500 });
  const run = runs.data?.find(r => r.id === selected) ?? runs.data?.[0];
  const investigate = useMutation({
    mutationFn: () => api<Run>(token, base + '/runs/multi-agent', 'POST', {
      patient_id: patientId, question, synthetic_only: true, request_id: requestId, ...(decisionId ? { decision_id: decisionId } : {}) }),
    onSuccess: result => { setSelected(result.id); setRequestId(crypto.randomUUID()); runs.refetch(); } });
  const review = useMutation({ mutationFn: (value: string) => api<Run>(token, base + '/runs/' + run!.id + '/' + (value === 'submit' ? 'submit' : 'review'),
    'POST', value === 'submit' ? undefined : { decision: value, note }),
    onSuccess: () => { setNote(''); runs.refetch(); } });
  const source = useQuery({ queryKey: ['multi-source', token, patientId, sourceId], enabled: !!sourceId,
    queryFn: () => api<{ citation: string; normalized: unknown; quality: unknown }>(token, '/v1/clinical/patients/' + patientId + '/evidence/' + sourceId) });
  const packet = run?.detail.packet;
  return <Panel title="Multi-Agent Clinical Intelligence"><div className="inset investigation multi-agent">
    <p><strong>Source-grounded review support · human review is mandatory.</strong></p>
    <p>Specialists compare retrieved evidence, preserve chronology and explain configured prerequisites.</p>
    {decisionId && <details className="multi-linked"><summary>Linked prevention decision</summary>{decisionId}</details>}
    {provider.data && <p>{provider.data.configuration.model} · <Status value={provider.data.status} /></p>}
    {role === 'coordinator' && <form onSubmit={event => { event.preventDefault(); investigate.mutate(); }}>
      <label>Multi-agent investigation objective<textarea minLength={12} maxLength={800} value={question}
        onChange={event => { setQuestion(event.target.value); setRequestId(crypto.randomUUID()); }} /></label>
      <label className="clinical-history"><input type="checkbox" checked={attested} onChange={event => setAttested(event.target.checked)} />
        This investigation contains synthetic demonstration data only.</label>
      <Button type="submit" disabled={!provider.data?.available || !attested || patientId !== 'demo-amira' || investigate.isPending}>
        {investigate.isPending ? 'Supervisor investigating…' : 'Run Multi-Agent Investigation'}</Button>
    </form>}
    {[provider.error, runs.error, investigate.error, review.error].filter(Boolean).map((e, i) => <Feedback key={i} message={e!.message} error />)}
    {runs.data?.length ? <label>Multi-agent run<select value={run?.id ?? ''} onChange={event => { setSelected(event.target.value); setSourceId(''); }}>
      {runs.data.map(r => <option key={r.id} value={r.id}>{r.created} · {label(r.status)}</option>)}
    </select></label> : <Empty>No multi-agent investigations recorded for this selection.</Empty>}
    {run && <div data-testid="multi-run">
      <h3>Supervisor execution</h3><p><Status value={run.status} /> · {run.detail.question}</p>
      <ExecutionSummary run={run} />
      {run.detail.error && <Feedback message={label(run.detail.error)} error />}
      <div className="agent-grid">{Object.keys(names).map(id => {
        const agent = run.detail.multi_agent?.agents[id];
        const stats = run.detail.multi_agent?.summary?.agents[id];
        return <article key={id} className={'agent-card ' + (agent?.state ?? 'pending')}>
          <h3>{names[id]}</h3>
          <Status value={agent?.state ?? 'pending'} />
          {agent && <details><summary>Inspect {names[id]}</summary>
            <p>{label(agent.validation_status)} · {agent.execution_metadata.duration_ms ?? 0} ms</p>
            {stats && <p>{stats.model_calls} model calls · {stats.input_tokens.toLocaleString()} input / {stats.output_tokens.toLocaleString()} output tokens
              · {(stats.model_latency_ms / 1000).toFixed(1)} s model time</p>}
            {agent.execution_metadata.reported_model && <small>{agent.execution_metadata.reported_model} · {agent.execution_metadata.response_id}</small>}
            {agent.error && <Feedback message={label(agent.error)} error />}
            <Findings items={agent.findings} />
            <SpecialistDetails agent={agent} />
            <ul>{agent.uncertainty.map((x, i) => <li key={i}>{x}</li>)}</ul>
            {agent.validated_output && <details><summary>Validated structured specialist output</summary>
              <pre>{displayJson(agent.validated_output)}</pre></details>}
          </details>}
        </article>;
      })}</div>
      <details><summary>Agent execution timeline and actual tool calls</summary>
        <ol>{run.detail.multi_agent?.routing.map((r, i) => <li key={i}>{r.at} · {r.agent_id} · {r.selected ? 'Selected' : 'Not selected'} · {r.reason}</li>)}</ol>
        <p>{run.detail.trace.map(label).join(' → ')}</p>
        <ul>{run.detail.tool_history.map(t => <li key={t.call_id}>{t.name} · {t.status} · {t.cached ? 'Cached result reused' : 'Executed'} · {t.duration_ms} ms
          <small>{t.evidence_ids.join(', ')}</small></li>)}</ul>
        <p>{run.detail.usage.model_calls} model calls · {run.detail.usage.input_tokens} input / {run.detail.usage.output_tokens} output tokens · {run.detail.duration_ms} ms</p>
        {!run.detail.usage.usage_complete && <p>Usage is incomplete because a provider call failed or was interrupted.</p>}
      </details>
      {packet && <section className="unified-packet">
        <h3>Unified clinical review packet</h3>
        <p>{displayText(packet.summary)}</p><p><Status value={packet.grounding_status} /> · {packet.packet_complete ? 'All selected agent outputs validated' : 'Partial packet — required output unavailable'}
          · {packet.abstained ? 'Abstained from a readiness conclusion' : 'Evidence summary proposed for review'}</p>
        <h3>Decision timing information</h3><p>{packet.timing.label}</p>
        {packet.timing_policy && <p>Illustrative policy {packet.timing_policy.id} · Version {packet.timing_policy.version} · {packet.timing.due_at}</p>}
        <h3>Decision prerequisites</h3><ul>{packet.prerequisites.map(p => <li key={p.id}>{p.category} · {label(p.status)}</li>)}</ul>
        <details><summary>Consolidated source-linked findings</summary><Findings items={packet.findings} /></details>
        <h3>Unresolved evidence and clinician questions</h3>
        <ul>{[...packet.missing_information, ...packet.conflicting_evidence, ...packet.uncertainty].map((x, i) => <li key={i}>{x}</li>)}</ul>
        <h3>Administrative follow-up proposals</h3><ul>{packet.administrative_follow_up_proposals.map((x, i) => <li key={i}>{x}</li>)}</ul>
        <details><summary>Authorized evidence inventory</summary><ul>{packet.source_references.map(s => <li key={s.evidence_id}>
          <Button variant="outline" onClick={() => setSourceId(s.evidence_id)}>{s.citation}</Button><small>Version {s.version} · {label(s.quality_state)}</small>
        </li>)}</ul>{source.isFetching && <p>Loading source…</p>}
          {source.error && <Feedback message={source.error.message} error />}
          {source.data && <><p>{source.data.citation}</p><pre>{displayJson({ normalized: source.data.normalized, quality: source.data.quality })}</pre></>}
        </details>
        <h3>Human review</h3><p>{run.review ? label(run.review.decision) + ' · ' + run.review.note : label(run.status)}</p>
        {role === 'coordinator' && ['awaiting_submission', 'abstained'].includes(run.status) &&
          <Button disabled={review.isPending} onClick={() => review.mutate('submit')}>Submit Multi-Agent Packet for Human Review</Button>}
        {role === 'reviewer' && run.status === 'pending_review' && <>
          <label>Multi-agent summary review note<textarea value={note} maxLength={500} onChange={event => setNote(event.target.value)} /></label>
          <div className="actions">{['approve_summary', 'request_evidence', 'reject'].map(value =>
            <Button key={value} variant="outline" disabled={!note.trim() || review.isPending || value === 'approve_summary' && (!packet.packet_complete || packet.grounding_status === 'validation_failed')}
              onClick={() => review.mutate(value)}>{label(value)}</Button>)}</div>
        </>}
        <p className="muted">Summary review does not record a clinical decision or verify obligation closure. Use the existing authorized clinical workflows.</p>
      </section>}
    </div>}
  </div></Panel>;
}
