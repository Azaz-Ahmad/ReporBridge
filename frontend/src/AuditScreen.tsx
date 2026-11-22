import { useState, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { ArrowDownToLine, ClipboardList, FileCheck2, History, ListChecks, ShieldCheck } from 'lucide-react';
import { api } from './api';
import { DemoCorrection } from './DemoCorrection';
import { ModelPayload } from './ModelPayload';
import { usePrevention } from './Prevention';
import { displayJson, displayText, demoPatient } from './presentation';
import { closureMessage, completionEvidence, Interoperability, Lifecycle, obligationTitle } from './showcase';
import type { ScreenProps } from './screens';
import { label, moment, patientName, type Audit, type Resource } from './types';
import { Button, Empty, Feedback, Panel, Status } from './ui';

const tabs = ['Closure & Evidence', 'Decision History', 'Audit Trail', 'Model Payload', 'FHIR Export'] as const;
type Tab = typeof tabs[number];
const pageSize = 8;

function PageControls({ page, total, onChange, name }: { page: number; total: number; onChange: (page: number) => void; name: string }) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  return <div className="audit-pagination" aria-label={name + ' pagination'}>
    <span>{total ? page * pageSize + 1 : 0}–{Math.min((page + 1) * pageSize, total)} of {total}</span>
    <Button variant="outline" disabled={page === 0} onClick={() => onChange(page - 1)}>Previous {name}</Button>
    <Button variant="outline" disabled={page + 1 >= pages} onClick={() => onChange(page + 1)}>Next {name}</Button>
  </div>;
}

function AuditEvents({ events }: { events: Audit[] }) {
  const [selectedPage, setPage] = useState(0);
  const page = Math.min(selectedPage, Math.max(0, Math.ceil(events.length / pageSize) - 1));
  if (!events.length) return <Empty>No events recorded yet.</Empty>;
  return <><div className="table-wrap audit-table" role="region" aria-label="Scrollable audit table" tabIndex={0}>
    <table><thead><tr><th>Action</th><th>Actor</th><th>Timestamp · system time</th><th>Evidence references</th><th>Rule version</th></tr></thead>
      <tbody>{events.slice(page * pageSize, (page + 1) * pageSize).map(event => <tr key={event.sequence}>
        <td><strong>{label(event.action)}</strong><small>{displayText(event.detail.reason || event.detail.candidate_title || demoPatient(event.patient_id))}
          {event.detail.demo_date && <span> · {event.detail.demo_date} · demo calendar</span>}</small></td>
        <td>{label(event.actor)}</td><td>{moment(event.recorded)}</td>
        <td>{event.evidence_refs.length ? <details><summary>Source references ({event.evidence_refs.length})</summary>{event.evidence_refs.join(', ')}</details> : '—'}</td>
        <td><details><summary>Rule details</summary>{event.rule_key || event.detail.evaluated_rule || (event.detail.relevance_rule_id ? event.detail.relevance_rule_id + ' version ' + event.detail.relevance_rule_version : '—')}
          <pre>{displayJson(event.detail)}</pre></details></td>
      </tr>)}</tbody></table>
  </div><PageControls page={page} total={events.length} onChange={setPage} name="audit events" /></>;
}

function recordDetails(resource: Resource) {
  const raw = resource as Resource & { effectiveDateTime?: string; issued?: string; date?: string; serviceProvider?: { display?: string }; performer?: { display?: string }[]; author?: { display?: string }[] };
  return { date: raw.effectiveDateTime || raw.date || raw.issued, facility: raw.serviceProvider?.display || raw.performer?.[0]?.display || raw.author?.[0]?.display };
}

function AuditPanel({ tab, selected, children }: { tab: Tab; selected: Tab; children: ReactNode }) {
  const id = tabs.indexOf(tab);
  return <div className="audit-tab-panel" id={'audit-panel-' + id} role="tabpanel" aria-labelledby={'audit-tab-' + id} hidden={selected !== tab}>{children}</div>;
}

export function AuditScreen({ data, role, token, busy, action }: ScreenProps) {
  const [tab, setTab] = useState<Tab>('Closure & Evidence');
  const [payloadPatient, setPayloadPatient] = useState('');
  const [selected, setSelected] = useState('');
  const [inspectedId, setInspectedId] = useState('');
  const [error, setError] = useState('');
  const [recentPage, setRecentPage] = useState(0);
  const [decisionPage, setDecisionPage] = useState(0);
  const prevention = usePrevention(token);
  const open = data.clinical_obligations.filter(item => item.status === 'open');
  const current = open.find(item => item.id === selected) || open[0];
  const inspected = data.clinical_obligations.find(item => item.id === inspectedId) || data.clinical_obligations.find(item => item.status === 'closed') || current;
  const patient = data.patients.find(item => item.id === inspected?.patient_id) || data.patients[0];
  const documents = useQuery({ queryKey: ['source-documents', patient?.id, token], enabled: !!patient,
    queryFn: () => api<{ id: string; title: string; facility: string; date: string; version: number; status: string; simulated: boolean; digest: string }[]>(token, '/v1/source-documents/patients/' + patient!.id) });
  const verification = data.audit_events.filter(event => ['closure_verified', 'closure_blocked', 'closure_reopened'].includes(event.action));
  const lastResult = verification.find(event => event.obligation_id === inspected?.id);
  const reviews = inspected ? data.clinical_approvals.filter(review => data.care_coordination_tasks.some(task => task.id === review.task_id && task.obligation_id === inspected.id)) : [];
  const review = reviews.slice().sort((a, b) => b.recorded.localeCompare(a.recorded))[0];
  const tasks = data.care_coordination_tasks.filter(task => task.obligation_id === inspected?.id);
  const scenario = inspected && data.case_context?.[inspected.id];
  const evidence = inspected ? completionEvidence(data, inspected) : [];
  const readiness = inspected && data.closure_readiness?.[inspected.id];
  const serverVerified = inspected?.status === 'closed' || readiness === '';
  const dependencies = data.obligation_dependencies.filter(edge => edge.obligation_id === inspected?.id);
  const history = (prevention.data?.history || []).slice().reverse();
  const visibleDecisionPage = Math.min(decisionPage, Math.max(0, Math.ceil(history.length / pageSize) - 1));
  const patientEvidence = data.clinical_evidence.filter(item => item.patient_id === patient?.id);
  const recent = [
    ...patientEvidence.map(item => ({ key: 'e-' + item.id, ...recordDetails(item.resource), title: item.resource.code?.text || item.resource.resourceType,
      type: item.resource.resourceType, status: item.resource.status || 'Not recorded', detail: item.resource, sourceLink: undefined })),
    ...(Array.isArray(documents.data) ? documents.data : []).map(item => ({ key: 's-' + item.id, date: item.date,
      facility: item.facility + (item.simulated ? ' · SIMULATED' : ''), title: item.title, type: 'Source document', status: item.status,
      detail: { version: item.version, digest: item.digest }, sourceLink: '/documents?patient=' + patient!.id + '&document=' + item.id })),
    ...history.filter(event => event.patient_id === patient?.id).map(event => ({ key: 'd-' + event.sequence, date: event.recorded, facility: undefined,
      title: label(event.action), type: 'Decision event · system time', status: typeof event.detail.outcome === 'string' ? label(event.detail.outcome) : 'Recorded', detail: event.detail, sourceLink: undefined })),
  ].sort((a, b) => (Date.parse(b.date || '') || 0) - (Date.parse(a.date || '') || 0));
  const visibleRecentPage = Math.min(recentPage, Math.max(0, Math.ceil(recent.length / pageSize) - 1));

  async function download(patientId: string) {
    setError('');
    try {
      const bundle = await api(token, '/fhir/patients/' + patientId);
      const url = URL.createObjectURL(new Blob([JSON.stringify(bundle, null, 2)], { type: 'application/fhir+json' }));
      const link = document.createElement('a'); link.href = url; link.download = patientId + '-r4.json'; link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) { setError(err instanceof Error ? err.message : 'FHIR download failed.'); }
  }

  return <div className="audit-workspace">
    <div className="page-heading audit-heading"><div className="audit-heading-title"><span className="audit-heading-icon"><ShieldCheck size={27} /></span>
      <div><h1>Evidence &amp; Audit</h1><p>What evidence was reviewed, and was care actually completed?</p></div></div>
      <Button variant="outline" onClick={() => setTab('FHIR Export')}><ArrowDownToLine size={17} />Export FHIR bundle</Button>
    </div>
    {error && <Feedback message={error} error />}
    <section className="panel audit-summary" aria-label="Patient and obligation summary">
      <div><span className="field-kicker">Selected patient</span><strong>{patient ? patientName(patient) : 'No patient selected'}</strong>
        {patient && <small>{label(patient.stage)}{patient.resource.birthDate ? ' · DOB ' + patient.resource.birthDate : ''}</small>}</div>
      <div>{inspected ? <label>Inspect obligation<select value={inspected.id} onChange={event => { setInspectedId(event.target.value); setRecentPage(0); }}>
        {data.clinical_obligations.map(item => <option key={item.id} value={item.id}>{obligationTitle(data, item)} · {demoPatient(item.patient_id)}</option>)}
      </select></label> : <span>No obligation available.</span>}{inspected && <small>Assigned owner: {inspected.owner}</small>}</div>
      <div>{inspected && <><Status value={inspected.status} /><small>{closureMessage(data, inspected)}</small></>}</div>
    </section>

    <div className="audit-tabs" role="tablist" aria-label="Evidence and audit sections">{tabs.map((name, index) => <button key={name} type="button" role="tab"
      id={'audit-tab-' + index} aria-controls={'audit-panel-' + index} aria-selected={tab === name} disabled={name === 'Model Payload' && role === 'viewer'}
      title={name === 'Model Payload' && role === 'viewer' ? 'Coordinator and Reviewer only' : undefined} onClick={() => setTab(name)}>{name}</button>)}</div>

    <AuditPanel tab="Closure & Evidence" selected={tab}>
      {inspected ? <>
        <section className="panel audit-checkpoints" aria-label="Recorded obligation checkpoints"><Lifecycle data={data} item={inspected} /></section>
        <div className="audit-card-grid">
          <Panel title="Review status"><div className="audit-review-note"><ClipboardList size={20} /><div><strong>Action initiated</strong>
            <p>{review ? 'Proposal decision · ' + label(review.decision) + ' by ' + label(review.actor) : tasks.length ? 'A coordination proposal is recorded for human review.' : 'No coordination proposal recorded.'}</p>
            {review?.note && <p>{review.note}</p>}<small>Approving a proposal to obtain evidence leaves closure pending.</small></div></div>
            <p><strong>Required next action</strong><br />{scenario?.next_action || tasks[0]?.action || 'No next action recorded.'}</p>
            <p><strong>Current server closure check</strong><br />{closureMessage(data, inspected)}</p>
            {lastResult?.action === 'closure_blocked' && <p>Last closure attempt blocked. {lastResult.detail.reason}</p>}
            <div className="audit-safety-note">Approval alone does not close care. Qualifying evidence and required prerequisites must be satisfied.</div>
            <Link className="text-link" to="/resolution">Open care resolution and clinician drafts</Link>
          </Panel>
          <Panel title="Closure requirements"><ul className="audit-requirements">
            <li><FileCheck2 size={19} /><div><strong>Qualifying completion evidence</strong><small>{scenario?.completion || 'A qualifying final completion record.'}</small>
              <span>{serverVerified ? 'Satisfied by the server closure check.' : evidence.length ? `${evidence.length} record(s) submitted; qualification is checked by the server.` : 'No completion evidence submitted'}</span></div></li>
            <li><ShieldCheck size={19} /><div><strong>Evidence-specific reviewer approval</strong><span>{serverVerified ? 'Satisfied by the server closure check.' : review ? 'Review decision recorded; current evidence coverage remains subject to the server check.' : 'No approval recorded.'}</span>
              <details><summary>Reviewed source references</summary>{review?.evidence_refs.join(', ') || 'None recorded'}</details></div></li>
            <li><ListChecks size={19} /><div><strong>Dependency checks</strong>{dependencies.length ? dependencies.map(edge => {
              const prior = data.clinical_obligations.find(item => item.id === edge.depends_on);
              return <small key={edge.id}>{prior ? <Link to={'/passport?obligation=' + prior.id}>{obligationTitle(data, prior)}</Link> : 'Linked obligation unavailable'} · {prior ? label(prior.status) : 'Not available'}</small>;
            }) : <span>No prerequisites recorded.</span>}</div></li>
          </ul><details><summary>Supporting records</summary>{evidence.map(({ resource }) => (resource.code?.text || resource.resourceType) + ' · ' + resource.status).join(', ') || 'No completion evidence submitted'}</details>
          <div className="audit-verified-result"><strong>Care obligation verified as resolved</strong><Status value={inspected.status} /><p>{closureMessage(data, inspected)}</p></div>
          </Panel>
        </div>
        <Panel title="Correction and reopening"><p>Assigned owner: {inspected.owner}</p><DemoCorrection key={inspected.id} token={token} role={role} obligation={inspected}
          evidenceId={data.closure_evidence.find(row => row.obligation_id === inspected.id)?.evidence_id} evidenceLabel={evidence[0]?.resource.code?.text} /></Panel>
      </> : <Empty>No clinical obligation is available in this patient scope.</Empty>}

      {role === 'coordinator' && current && <Panel title="Submit synthetic completion evidence"><p className="muted">Demonstration actions · synthetic data only</p>
        <label className="field-inline">Completion evidence obligation<select aria-label="Completion evidence obligation" value={current.id} onChange={event => setSelected(event.target.value)}>
          {open.map(item => <option key={item.id} value={item.id}>{obligationTitle(data, item)} · {demoPatient(item.patient_id)}</option>)}
        </select></label><div className="actions">
          <Button disabled={busy} onClick={() => action('/obligations/' + current.id + '/demo-completion', 'Verified fixture submitted. Reviewer approval is still required.', { scenario: 'verified' })}>Add verified evidence</Button>
          <Button disabled={busy} variant="danger" onClick={() => action('/obligations/' + current.id + '/demo-completion', 'Conflicting fixture submitted.', { scenario: 'conflicting' })}>Add conflicting evidence</Button>
          <Button asChild variant="outline"><Link to={'/passport?obligation=' + current.id}>Verify closure in Passport</Link></Button>
        </div></Panel>}

      <Panel title="Recent evidence and decisions"><p className="muted">Selected patient records; inclusion does not establish qualifying completion evidence.</p>
        {documents.error && <Feedback message={documents.error.message} error />}
        {recent.length ? <><div className="table-wrap"><table><thead><tr><th>Date</th><th>Evidence / Decision</th><th>Source / Facility</th><th>Type</th><th>Status</th></tr></thead>
          <tbody>{recent.slice(visibleRecentPage * pageSize, (visibleRecentPage + 1) * pageSize).map(item => <tr key={item.key}><td>{item.date ? item.date.slice(0, 10) : 'Not recorded'}</td>
            <td><strong>{item.sourceLink ? <Link to={item.sourceLink}>{item.title}</Link> : item.title}</strong><details><summary>Record details</summary><pre>{displayJson(item.detail)}</pre></details></td>
            <td>{item.facility || 'Not recorded in this view'}</td><td>{item.type}</td><td>{item.status}</td></tr>)}</tbody></table></div>
          <PageControls page={visibleRecentPage} total={recent.length} onChange={setRecentPage} name="evidence and decisions" /></> : <Empty>No evidence or decision events recorded for this patient.</Empty>}
      </Panel>
      <details className="panel audit-technical"><summary><History size={17} />Verification results · full recorded history</summary><AuditEvents events={verification} /></details>
    </AuditPanel>

    <AuditPanel tab="Decision History" selected={tab}><Panel title="Decision History"><p className="muted">Evidence retrieval, clinician review, decision recording, follow-up and verified obligation closure are recorded as separate events.</p>
      {prevention.error && <Feedback message={prevention.error.message} error />}
      {history.length ? <><div className="table-wrap"><table><thead><tr><th>Decision event</th><th>Time · system time</th><th>Actor</th><th>Outcome / linked obligation</th><th>Supporting evidence</th></tr></thead>
        <tbody>{history.slice(visibleDecisionPage * pageSize, (visibleDecisionPage + 1) * pageSize).map(event => {
          const decision = prevention.data?.decisions.find(item => item.id === event.decision_id);
          return <tr key={event.sequence}><td><strong>{label(event.action)}</strong><small>{demoPatient(event.patient_id)}</small><details><summary>Decision identifier</summary>{event.decision_id}</details></td>
            <td>{moment(event.recorded)}</td><td>{label(event.actor)}</td><td>{typeof event.detail.outcome === 'string' ? label(event.detail.outcome) : 'Not recorded on this event'}
              {decision && <small><Link to={'/passport?obligation=' + decision.obligation_id}>{data.clinical_obligations.find(item => item.id === decision.obligation_id) ? obligationTitle(data, data.clinical_obligations.find(item => item.id === decision.obligation_id)!) : 'Open linked obligation'}</Link></small>}</td>
            <td><details><summary>Inspect decision audit event</summary><pre>{displayJson(event.detail)}</pre></details></td></tr>;
        })}</tbody></table></div><PageControls page={visibleDecisionPage} total={history.length} onChange={setDecisionPage} name="decision events" /></> : <Empty>{prevention.isPending ? 'Loading decision history…' : 'No decision history recorded.'}</Empty>}
    </Panel></AuditPanel>

    <AuditPanel tab="Audit Trail" selected={tab}><Panel title="Lifecycle audit history"><AuditEvents events={data.audit_events} /></Panel>
      {data.demo_run_archive.length > 0 && <details className="panel expandable"><summary>Archived Amira demo runs</summary><ul className="inset archive-list">{data.demo_run_archive.map(run =>
        <li key={run.id}><strong>{moment(run.recorded)}</strong> · {run.audit_count} audit events · {label(run.actor)}<small>{run.id}</small></li>)}</ul></details>}
    </AuditPanel>

    <AuditPanel tab="Model Payload" selected={tab}>{role !== 'viewer' && data.patients[0] && <>
      <label className="audit-payload-patient">Payload patient<select aria-label="Payload patient" value={payloadPatient || data.patients[0].id} onChange={event => setPayloadPatient(event.target.value)}>
        {data.patients.map(item => <option key={item.id} value={item.id}>{patientName(item)}</option>)}</select></label>
      <ModelPayload key={payloadPatient || data.patients[0].id} token={token} role={role} patientId={payloadPatient || data.patients[0].id} active={tab === 'Model Payload'} />
    </>}</AuditPanel>

    <AuditPanel tab="FHIR Export" selected={tab}><Panel title="FHIR R4 export"><Interoperability />
      {data.patients.length ? data.patients.map(item => <div className="record-link" key={item.id}><strong>{patientName(item)}</strong>
        <Button variant="outline" onClick={() => void download(item.id)}><ArrowDownToLine size={16} />Download FHIR bundle</Button></div>) : <Empty>No patient bundles available.</Empty>}
    </Panel></AuditPanel>
    <p className="audit-policy-note">Illustrative policy — pending clinical confirmation.</p>
  </div>;
}
