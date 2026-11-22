import { useEffect, useState, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useLocation, useSearchParams } from 'react-router-dom';
import { ArrowRight, ClipboardList, Workflow } from 'lucide-react';
import { CoordinationNextAction, GuidelineTraceability } from './Coordination';
import { HandoffPanel } from './Handoff';
import { HistoricalCandidates } from './HistoricalCandidates';
import { EarlierRecords } from './History';
import { JourneyStrip } from './Jury';
import { PreventionPassport, usePrevention } from './Prevention';
import { SourceDocumentsLink } from './SourceDocuments';
import { TspWindow, type WindowResult } from './Tsp';
import { closureMessage, completionEvidence, DependencyMap, Lifecycle, obligationTitle } from './showcase';
import { demoPatient, displayJson, displayText } from './presentation';
import { label, moment, patientName, type Audit, type Obligation, type Patient, type Resource, type Rule } from './types';
import { Button, Empty, Feedback, Panel, Status } from './ui';
import type { ScreenProps } from './screens';

const tabs = ['Overview', 'Evidence', 'Decision History', 'Audit Trail', 'Guideline Trace'] as const;
type Tab = typeof tabs[number];
const pageSize = 8;
function TabPanel({ name, active, children }: { name: Tab; active: Tab; children: ReactNode }) {
  const index = tabs.indexOf(name);
  return <div role="tabpanel" className="passport-tab-panel" id={'passport-panel-' + index} aria-labelledby={'passport-tab-' + index} hidden={name !== active}>{children}</div>;
}
function Pagination({ page, count, setPage, name }: { page: number; count: number; setPage: (page: number) => void; name: string }) {
  return <div className="passport-pagination"><span>{count ? page * pageSize + 1 : 0}–{Math.min((page + 1) * pageSize, count)} of {count}</span>
    <Button variant="outline" disabled={!page} onClick={() => setPage(page - 1)}>Previous {name}</Button>
    <Button variant="outline" disabled={(page + 1) * pageSize >= count} onClick={() => setPage(page + 1)}>Next {name}</Button></div>;
}
function ObligationAudit({ events }: { events: Audit[] }) {
  const [selected, setPage] = useState(0);
  const page = Math.min(selected, Math.max(0, Math.ceil(events.length / pageSize) - 1));
  if (!events.length) return <Empty>No events recorded yet.</Empty>;
  return <><div className="table-wrap audit-table" role="region" aria-label="Scrollable audit table" tabIndex={0}><table><thead><tr><th>Action</th><th>Actor</th><th>Timestamp · system time</th><th>Source evidence</th><th>Rule version</th></tr></thead>
    <tbody>{events.slice(page * pageSize, (page + 1) * pageSize).map(event => <tr key={event.sequence}><td><strong>{label(event.action)}</strong><small>{displayText(event.detail.reason || event.detail.candidate_title || demoPatient(event.patient_id))}{event.detail.demo_date && <> · {event.detail.demo_date} · demo calendar</>}</small></td>
      <td>{label(event.actor)}</td><td>{moment(event.recorded)}</td><td><details><summary>Source references ({event.evidence_refs.length})</summary>{event.evidence_refs.join(', ') || 'None recorded'}</details></td>
      <td><details><summary>Rule details</summary>{event.rule_key || event.detail.evaluated_rule || (event.detail.relevance_rule_id ? event.detail.relevance_rule_id + ' version ' + event.detail.relevance_rule_version : '—')}<pre>{displayJson(event.detail)}</pre></details></td></tr>)}</tbody>
  </table></div><Pagination page={page} count={events.length} setPage={setPage} name="audit events" /></>;
}

export function Passport(props: ScreenProps) {
  const { data, role, token } = props;
  const [params, setParams] = useSearchParams();
  const obligationId = params.get('obligation');
  const candidateId = params.get('candidate');
  const candidatePatient = params.get('patient');
  const item = candidateId ? undefined : obligationId ? data.clinical_obligations.find(entry => entry.id === obligationId) : data.clinical_obligations[0];
  const rule = data.rule_versions.find(entry => entry.id === item?.rule_key);
  const source = data.clinical_evidence.find(entry => entry.id === item?.source_id)?.resource;
  const patient = data.patients.find(entry => entry.id === item?.patient_id);
  return <div className="passport-page">
    <div className="page-heading passport-heading"><div><h1>Clinical Obligation Passport</h1><p>Source evidence, ownership, timing, and verified closure.</p></div>
      {!!item && <label className="field-inline">Passport obligation<select aria-label="Passport obligation" value={item.id} onChange={event => setParams({ obligation: event.target.value })}>
        {data.clinical_obligations.map(entry => <option key={entry.id} value={entry.id}>{obligationTitle(data, entry)} · {demoPatient(entry.patient_id)}</option>)}
      </select></label>}
    </div>
    <div className="passport-navigation">{(patient || candidatePatient) && <SourceDocumentsLink patientId={patient?.id || candidatePatient!} />}
      <Link className="text-link" to={item ? '/workspace?patient=' + item.patient_id : '/workspace'}>Open patient workspace <ArrowRight size={15} /></Link></div>
    {candidateId && candidatePatient && <HistoricalCandidates token={token} role={role} patientId={candidatePatient} candidateId={candidateId} />}
    {!item || !rule || !source ? <Empty>{candidateId ? 'A candidate requires clinician confirmation before it becomes an active obligation. ' : obligationId ? 'This obligation is unavailable in the current run. ' : 'Evaluate a synthetic patient to create an obligation. '}
      <Link className="text-link" to="/workspace">Open patient workspace</Link></Empty> : <ActivePassport {...props} item={item} rule={rule} source={source} patient={patient} />}
  </div>;
}

function ActivePassport({ data, role, token, busy, action, item, rule, source, patient }: ScreenProps & { item: Obligation; rule: Rule; source: Resource; patient?: Patient }) {
  const { hash } = useLocation();
  const [params] = useSearchParams();
  const [tab, setTab] = useState<Tab>(() => hash === '#provenance' ? 'Evidence' : 'Overview');
  const [decisionPage, setDecisionPage] = useState(0);
  useEffect(() => { if (hash === '#provenance') setTab('Evidence'); }, [hash]);
  const scenario = data.case_context?.[item.id];
  const history = data.audit_events.filter(event => event.obligation_id === item.id);
  const prevention = usePrevention(token);
  // Subscribe to the existing hero calculator cache without issuing another request.
  const timing = useQuery<WindowResult>({ queryKey: ['tsp', 'patient', item.patient_id, token], enabled: false });
  const decisions = prevention.data?.decisions.filter(decision => !decision.archived && decision.obligation_id === item.id && (!params.get('decision') || decision.id === params.get('decision'))) || [];
  const decisionHistory = (prevention.data?.history || []).filter(event => event.patient_id === item.patient_id).slice().reverse();
  const page = Math.min(decisionPage, Math.max(0, Math.ceil(decisionHistory.length / pageSize) - 1));
  const records = completionEvidence(data, item);
  const reviews = data.clinical_approvals.filter(review => data.care_coordination_tasks.some(task => task.id === review.task_id && task.obligation_id === item.id));
  const dependencies = data.obligation_dependencies.filter(edge => edge.obligation_id === item.id);

  return <>
    <section className="panel passport-summary" aria-label="Patient and obligation summary"><span className="passport-summary-icon"><ClipboardList size={25} /></span>
      <div><span className="field-kicker">Patient · {patient ? label(patient.stage) : 'Stage unavailable'}</span><strong>{patient ? patientName(patient) : demoPatient(item.patient_id)}</strong><JourneyStrip token={token} patientId={item.patient_id} compact /></div>
      <div><span className="field-kicker">{label(rule.pathway_id)} pathway</span><h2>{obligationTitle(data, item)}</h2><small>Assigned owner: {item.owner}</small></div><Status value={item.status} />
    </section>
    <TspWindow token={token} patientId={item.patient_id} role={role} passport owner={item.owner} nextAction={<CoordinationNextAction token={token} patientId={item.patient_id} />} />
    <div className="passport-tabs" role="tablist" aria-label="Passport sections">{tabs.map((name, index) => <button type="button" role="tab" key={name} id={'passport-tab-' + index} aria-controls={'passport-panel-' + index} aria-selected={tab === name} onClick={() => setTab(name)}>{name}</button>)}</div>

    <TabPanel name="Overview" active={tab}>
      <Panel title="Obligation checkpoints"><Lifecycle data={data} item={item} /></Panel>
      <div className="passport-overview-grid"><Panel title="Closure requirements">        <div className="passport-closure-check"><strong>Current closure check</strong><p>{closureMessage(data, item)}</p></div>
        <dl className="details"><div><dt>Qualifying completion evidence</dt><dd><strong>{records.length} record(s) submitted</strong><small>Qualification is determined by the server.</small></dd></div>
          <div><dt>Evidence-specific reviewer approval</dt><dd>{reviews.length ? reviews.map(review => <details key={review.id}><summary>{label(review.decision)} · {label(review.actor)} · {moment(review.recorded)}</summary><p>{review.note}</p>{review.evidence_refs.join(', ') || 'No source references recorded'}</details>) : 'No reviewer decision recorded.'}</dd></div>
          <div><dt>Dependency requirements</dt><dd>{dependencies.length ? dependencies.map(edge => { const prior = data.clinical_obligations.find(entry => entry.id === edge.depends_on); return <div key={edge.id}>{prior ? <Link to={'/passport?obligation=' + prior.id}>{obligationTitle(data, prior)} · {label(prior.status)}</Link> : 'Linked prerequisite unavailable'}</div>; }) : 'No dependencies recorded.'}</dd></div>
          </dl>
        <p className="passport-safety-note">Approval alone does not close care; evidence and prerequisites must pass server checks.</p>
        {role === 'coordinator' && item.status === 'open' && <div className="actions passport-primary-actions">
          <Button disabled={busy} onClick={() => action('/obligations/' + item.id + '/agent', 'Coordination action routed for review.')}><Workflow size={17} />Run care-resolution agent</Button>
          <Button variant="outline" disabled={busy} onClick={() => action('/obligations/' + item.id + '/close', 'Closure verified.')}>Verify closure</Button>
          <Link className="text-link" to={'/resolution?obligation=' + item.id}>Open review queue <ArrowRight size={15} /></Link>
        </div>}
      </Panel><PreventionPassport obligationId={item.id} token={token} role={role} passport /></div>
      <HistoricalCandidates token={token} role={role} patientId={item.patient_id} passportSummary />
      {data.obligation_dependencies.some(edge=>edge.obligation_id===item.id||edge.depends_on===item.id)&&<details className="panel passport-technical"><summary>Cross-pathway dependencies · {data.obligation_dependencies.filter(edge=>edge.obligation_id===item.id||edge.depends_on===item.id).length} recorded</summary><DependencyMap data={data} patientId={item.patient_id} obligationId={item.id} /></details>}
    </TabPanel>

    <TabPanel name="Evidence" active={tab}>
      <Panel title="Required and available evidence"><details><summary>Recorded finding and clinical context</summary><strong>{scenario?.finding || 'Documented source evidence'}</strong><p>{scenario?.rationale || rule.definition.description}</p><p>Owner: {item.owner} · Last updated: {moment(history[0]?.recorded ?? item.created)}</p></details><p>{scenario?.completion || 'A qualifying final completion record.'} Reviewer approval must cover the current evidence and any configured prerequisite must be satisfied.</p><p>{closureMessage(data, item)}</p>
        {records.length ? <ul className="passport-records">{records.map(({ id, resource }) => <li key={id}><strong>{resource.code?.text || resource.resourceType}</strong><Status value={resource.status || 'Unavailable'} /><details><summary>Completion source reference</summary>{resource.resourceType}/{resource.id}</details></li>)}</ul> : <Empty>No completion evidence submitted.</Empty>}
        {decisions.map(decision => <div key={decision.id}><h3>Decision evidence prerequisites</h3><ul className="decision-prerequisites">{decision.prerequisites.map(prerequisite => <li key={prerequisite.id}><strong>{prerequisite.category}</strong><Status value={prerequisite.status} /><small>{prerequisite.issues.map(label).join(', ')}</small><details><summary>Supporting source references</summary>{prerequisite.source_refs.join(', ') || 'No accessible source records'}</details></li>)}</ul></div>)}
        <Button variant="outline" onClick={() => setTab('Overview')}>Open current decision and reviewer controls</Button>
      </Panel>
      <EarlierRecords token={token} role={role} patientId={item.patient_id} /><HandoffPanel token={token} role={role} patientId={item.patient_id} />
      <details className="panel expandable" id="provenance" open={hash === '#provenance' || undefined}><summary>Source evidence and provenance</summary>
        <dl className="details"><div><dt>Source resource</dt><dd>{source.resourceType}/{source.id}</dd></div><div><dt>Obligation ID</dt><dd>{item.id}</dd></div><div><dt>Patient ID</dt><dd>{item.patient_id}</dd></div>
          <div><dt>Rule ID and version</dt><dd>{item.rule_key}</dd></div><div><dt>Recorded finding</dt><dd>{source.code?.text || scenario?.finding || label(source.code?.coding?.[0]?.code ?? 'Unavailable')} · {source.valueString || '—'}</dd></div>
          <div><dt>Configured evidence codes</dt><dd>{rule.definition.trigger} → {rule.definition.closure}</dd></div><div><dt>Evidence status</dt><dd>{label(source.status ?? 'Unavailable')}</dd></div><div><dt>Rule documentation</dt><dd>{displayText(rule.definition.source)}</dd></div></dl>
        <Link className="text-link" to={'/workspace?patient=' + item.patient_id}>Open patient evidence <ArrowRight size={15} /></Link>
      </details>
    </TabPanel>

    <TabPanel name="Decision History" active={tab}><Panel title="Decision History"><p className="muted">Recorded decision events for the selected patient. Decision recording and obligation closure are separate.</p>
      {prevention.error && <Feedback message={prevention.error.message} error />}
      {decisionHistory.length ? <><div className="table-wrap"><table><thead><tr><th>Event</th><th>Timestamp · system time</th><th>Actor</th><th>Outcome / details</th></tr></thead><tbody>{decisionHistory.slice(page * pageSize, (page + 1) * pageSize).map(event => <tr key={event.sequence}>
        <td><strong>{label(event.action)}</strong><details><summary>Decision reference</summary>{event.decision_id}</details></td><td>{moment(event.recorded)}</td><td>{label(event.actor)}</td>
        <td>{typeof event.detail.outcome === 'string' ? label(event.detail.outcome) : 'No outcome recorded on this event'}<details><summary>Rationale, evidence and event details</summary><pre>{displayJson(event.detail)}</pre></details></td>
      </tr>)}</tbody></table></div><Pagination page={page} count={decisionHistory.length} setPage={setDecisionPage} name="decision events" /></> : <Empty>{prevention.isPending ? 'Loading decision history…' : 'No decision history recorded for this patient.'}</Empty>}
    </Panel></TabPanel>

    <TabPanel name="Audit Trail" active={tab}><Panel title="Obligation history"><ObligationAudit events={history} /></Panel></TabPanel>
    <TabPanel name="Guideline Trace" active={tab}><div className="passport-guideline-grid"><GuidelineTraceability token={token} patientId={item.patient_id} recordedStatus />
      <Panel title="Rule and timing inputs"><dl className="details"><div><dt>Rule identifier / version</dt><dd>{rule.rule_id} · {rule.version}</dd></div><div><dt>Closure criteria</dt><dd>{scenario?.completion || rule.definition.description}<small>Evidence-specific approval and cleared prerequisites remain required.</small></dd></div>
        <div><dt>Rule provenance</dt><dd>{displayText(rule.definition.source)}</dd></div><div><dt>Timing policy</dt><dd>{timing.data ? `${timing.data.policy_id || 'Timing not established'} · version ${timing.data.policy_version || 'not established'}` : 'Calculator context unavailable or loading.'}</dd></div></dl>
        <h3>Timing inputs used</h3>{timing.data?.inputs_used.map(input => <div className="passport-timing-input" key={input.source_id}><span>Source date value {input.source_date} · version {input.version}</span>{input.due_date && <span> · EDD {input.due_date}</span>}<details><summary>Source reference</summary>{input.source_id}</details></div>)}
        {!!timing.data && !timing.data.inputs_used.length && <Empty>No timing inputs supplied by the calculator.</Empty>}
        {timing.data&&!timing.data.missing_evidence.length&&<p>No dating evidence gaps. Clinician review and approval remain required.</p>}
        <details><summary>Configured evidence codes</summary>{rule.definition.trigger} → {rule.definition.closure}</details>
      </Panel></div></TabPanel>
  </>;
}
