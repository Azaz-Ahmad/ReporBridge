import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { api } from './api';
import { Button, Empty, Feedback, Panel, Status } from './ui';
import { label, type Role } from './types';

type Provider = { status: string; available: boolean; configuration: { model: string } };
type Source = { evidence_id: string; version: number; citation: string; quality_state: string };
type Finding = { finding_id: string; statement: string; evidence_status: string;
  requires_clinical_interpretation: boolean;
  supporting_sources: { evidence_id: string; version: number; excerpt: string; value_key: string; value_json: string }[] };
type Packet = { summary: string; origin: string; findings: Finding[]; grounding_status: string; abstained: boolean;
  missing_information: string[]; conflicting_evidence: string[]; uncertainty: string[];
  recommended_review_actions: string[]; source_references: Source[] };
type Run = { id: string; status: string; created: string; review: { decision: string; note: string } | null;
  detail: { question: string; configuration: { model: string }; packet: Packet | null; error: string | null;
    duration_ms: number; trace: string[]; decision_context?: { decision_id: string } | null; validation?: { errors: string[]; claim_checks?: string };
    usage: { model_calls: number; input_tokens: number; output_tokens: number; retries: number };
    tool_history: { name: string; call_id: string; status: string; duration_ms: number; evidence_ids: string[] }[] } };
const base = '/v1/agents/clinical-evidence';
const defaultQuestion = "What documented evidence is available regarding Amira Haddad's unresolved preconception metabolic assessment, and what information requires clinician reconciliation?";

export function ClinicalInvestigation({ patientId, token, role, decisionId }: {
  patientId: string; token: string; role: Role; decisionId?: string;
}) {
  const [question, setQuestion] = useState(decisionId ? "Investigate this prevention decision and its evidence prerequisites for clinician review." : defaultQuestion);
  const [attested, setAttested] = useState(false);
  const [selected, setSelected] = useState('');
  const [requestId, setRequestId] = useState(() => crypto.randomUUID());
  const [note, setNote] = useState('');
  const [source, setSource] = useState<Source | null>(null);
  const provider = useQuery({ queryKey: ['evidence-provider', token],
    queryFn: () => api<Provider>(token, base + '/status') });
  const runs = useQuery({ queryKey: ['evidence-runs', token, patientId, decisionId],
    queryFn: () => api<Run[]>(token, decisionId ? '/v1/prevention/decisions/' + decisionId + '/investigations'
      : base + '/runs?patient_id=' + encodeURIComponent(patientId))
      .then((items) => (decisionId ? items : items.filter((item) => !item.detail.decision_context)).filter(item => (item.detail as { workflow?: string }).workflow !== 'multi_agent')),
    refetchInterval: (query) => query.state.data?.some((run) => run.status === 'running') ? 2000 : false });
  const run = runs.data?.find((item) => item.id === selected) ?? runs.data?.[0];
  const investigation = useMutation({
    mutationFn: () => api<Run>(token, decisionId ? '/v1/prevention/decisions/' + decisionId + '/investigations' : base + '/runs', 'POST',
      decisionId ? { request_id: requestId } : { patient_id: patientId, question, request_id: requestId, synthetic_only: true }),
    onSuccess: (result) => {
      setSelected(result.id);
      setRequestId(crypto.randomUUID());
      runs.refetch();
    },
  });
  const decision = useMutation({
    mutationFn: (value: string) => api<Run>(token, base + '/runs/' + run!.id + '/' + (value === 'submit' ? 'submit' : 'review'),
      'POST', value === 'submit' ? undefined : { decision: value, note }),
    onSuccess: () => { setNote(''); runs.refetch(); },
  });
  const evidence = useQuery({
    queryKey: ['investigation-source', token, patientId, source?.evidence_id], enabled: !!source,
    queryFn: () => api<{ citation: string; status: string; normalized: { values?: unknown }; quality: { state: string; warnings: string[] } }>(
      token, '/v1/clinical/patients/' + patientId + '/evidence/' + source!.evidence_id),
  });
  const packet = run?.detail.packet;
  return <Panel title={decisionId ? "Decision Readiness Investigation" : "Clinical Evidence Investigation"}>
    <div className="inset investigation">
      <p><strong>AI-generated evidence summary — requires clinical review.</strong></p>
      {provider.isLoading && <p role="status">Checking provider…</p>}
      {provider.data && <p>OpenAI Responses · {provider.data.configuration.model} · <Status value={provider.data.status} /></p>}
      {provider.data && !provider.data.available && <p>
        {decisionId ? 'Decision readiness investigation is unavailable.' : 'The Clinical Evidence Agent is unavailable.'} Provider status is {label(provider.data.status).toLowerCase()}.
        Configure the OpenAI API key and enable the agent in the backend environment to run an investigation.
      </p>}
      {provider.error && <Feedback message={provider.error.message} error />}
      {role === 'coordinator' && <form onSubmit={(event) => { event.preventDefault(); investigation.mutate(); }}>
        <label>Clinical evidence question
          <textarea value={question} readOnly={!!decisionId} maxLength={800} minLength={12}
            onChange={(event) => { setQuestion(event.target.value); setRequestId(crypto.randomUUID()); }} />
        </label>
        <label className="clinical-history"><input type="checkbox" checked={attested}
          onChange={(event) => setAttested(event.target.checked)} /> This question contains synthetic demonstration data only.</label>
        <Button type="submit" disabled={!provider.data?.available || !attested || patientId !== 'demo-amira' || investigation.isPending}>
          {investigation.isPending ? 'Investigating…' : decisionId ? 'Run Decision Readiness Investigation' : 'Run Investigation'}</Button>
      </form>}
      {investigation.error && <Feedback message={investigation.error.message} error />}
      {runs.error && <Feedback message={runs.error.message} error />}
      {runs.data?.length ? <label>Investigation run<select value={run?.id ?? ''}
        onChange={(event) => { setSelected(event.target.value); setSource(null); setNote(''); }}>
        {runs.data.map((item) => <option key={item.id} value={item.id}>{item.created} · {label(item.status)}</option>)}
      </select></label> : <Empty>No evidence investigations recorded for this patient.</Empty>}
      {run && <div className="investigation-result">
        <p><Status value={run.status} /> · {run.detail.configuration.model}</p>
        <p>{run.detail.question}</p>
        {run.detail.error && <Feedback message={label(run.detail.error)} error />}
        <details><summary>View Tool Execution</summary>
          <p>{run.detail.trace.map(label).join(' → ')}</p>
          <p>{run.detail.usage.model_calls} model calls · {run.detail.usage.input_tokens} input tokens · {run.detail.usage.output_tokens} output tokens
            · {run.detail.usage.retries} retries · {run.detail.duration_ms} ms</p>
          <ul>{run.detail.tool_history.map((item) => <li key={item.call_id}>
            {item.name} · {item.status} · {item.duration_ms} ms
            <small>{item.evidence_ids.join(', ')}</small>
          </li>)}</ul>
        </details>
        {packet && <>
          <p>{packet.origin === 'model' ? 'Model-generated draft' : 'System-recorded abstention'} · <Status value={packet.grounding_status} /></p>
          <p>{packet.summary}</p>
          <details open><summary>View Findings</summary>
            {packet.findings.length ? <ul>{packet.findings.map((finding) => <li key={finding.finding_id}>
              <p>{finding.statement}</p><small>{label(finding.evidence_status)} · {finding.requires_clinical_interpretation ? 'Clinical interpretation required' : 'Source statement'}</small>
              {finding.supporting_sources.map((support, index) => <div key={index}>
                <small>{support.evidence_id} · Version {support.version}</small>
                {support.excerpt && <blockquote>{support.excerpt}</blockquote>}
                {support.value_key && <p>{support.value_key} · {support.value_json}</p>}
              </div>)}
            </li>)}</ul> : <p>The investigation abstained from findings.</p>}
          </details>
          <details><summary>View Missing/Conflicting Evidence</summary>
            <h3>Missing information</h3><ul>{packet.missing_information.map((item, index) => <li key={index}>{item}</li>)}</ul>
            <h3>Conflicts</h3><ul>{packet.conflicting_evidence.map((item, index) => <li key={index}>{item}</li>)}</ul>
            <h3>Uncertainty</h3><ul>{packet.uncertainty.map((item, index) => <li key={index}>{item}</li>)}</ul>
            <h3>Recommended clinician review</h3><ul>{packet.recommended_review_actions.map((item, index) => <li key={index}>{item}</li>)}</ul>
          </details>
          <details><summary>View Evidence Sources</summary>
            <ul>{packet.source_references.map((item) => <li key={item.evidence_id}>
              <Button variant="outline" onClick={() => setSource(item)}>{item.citation}</Button>
              <small>Version {item.version} · {label(item.quality_state)}</small>
            </li>)}</ul>
            {evidence.isFetching && <p role="status">Loading source…</p>}
            {evidence.error && <Feedback message={evidence.error.message} error />}
            {source && evidence.data && <div><p>{evidence.data.citation} · Current status {evidence.data.status}</p>
              <p>{evidence.data.quality.warnings.map(label).join(', ')}</p>
              <pre>{JSON.stringify(evidence.data.normalized.values ?? {}, null, 2)}</pre></div>}
          </details>
          <p>{run.detail.validation?.claim_checks}</p>
          {run.detail.validation?.errors?.length ? <p>{run.detail.validation.errors.map(label).join(', ')}</p> : null}
          {role === 'coordinator' && ['awaiting_submission', 'abstained'].includes(run.status) &&
            <Button disabled={decision.isPending} onClick={() => decision.mutate('submit')}>Submit for Human Review</Button>}
          {role === 'reviewer' && run.status === 'pending_review' && <div className="review-controls">
            <label>Evidence summary review note<textarea value={note} maxLength={500} onChange={(event) => setNote(event.target.value)} /></label>
            <div className="actions">
              {['approve_summary', 'reject', 'request_evidence'].map((value) => <Button key={value} variant="outline"
                disabled={!note.trim() || decision.isPending || value === 'approve_summary' && packet.origin !== 'model'}
                onClick={() => decision.mutate(value)}>{label(value)}</Button>)}
            </div>
          </div>}
          {run.review && <p>Reviewer decision · {label(run.review.decision)} · {run.review.note}</p>}
          <p className="muted">Clinical closure requires its existing evidence-specific approval and verification.</p>
        </>}
        {decision.error && <Feedback message={decision.error.message} error />}
      </div>}
    </div>
  </Panel>;
}
