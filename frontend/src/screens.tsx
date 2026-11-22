import {SourceDocumentsLink,LatestSourceDocuments} from './SourceDocuments';
import { HistoricalCandidates, HistoricalDetectionTimeline, HistoricalIdentificationBadge } from './HistoricalCandidates';
import { CoordinationNextAction, GuidelineTraceability } from './Coordination';
import { useState, type ReactNode } from 'react';
import { Link, useLocation, useSearchParams } from 'react-router-dom';
import { ArrowRight, ArrowUpRight, CalendarDays, CircleAlert, ClipboardList, GitBranch, HeartPulse, Plus, RotateCcw, ShieldCheck, Users, Workflow } from 'lucide-react';
import { PRODUCT_NAME, demoPatient, displayText } from './presentation';
import { api } from './api';
import { EarlierRecords } from './History';
import { JuryOverview, DemoAdmin, JourneyStrip } from './Jury';
import { HANDOFF_PATIENT, HandoffSetup, HandoffPanel, HandoffTimeline } from './Handoff';
import { DemoClock, TspQueue, TspWindow } from './Tsp';
import { ClinicalExplorer } from './ClinicalExplorer';
import { ClinicalInvestigation } from './ClinicalInvestigation';
import { PreventionQueue, PreventionPassport, DecisionReadiness, DecisionTimeline } from './Prevention';
import { Button, Empty, Feedback, Panel, Status } from './ui';
import { closureMessage, completionEvidence, DependencyMap, Evaluation, Innovations, Journey, Lifecycle, obligationTitle as titleFor, populationCounts, RunTrace, WorkflowSteps, workflowStatus } from './showcase';
import { label, moment, patientName, type Audit, type Role, type Snapshot } from './types';

export type ScreenProps = {
  data: Snapshot; role: Role; token: string; busy: boolean; busyPath?: string;
  action: (path: string, success: string, body?: unknown) => void;
};

function Heading({ title, subtitle, children }: { title: string; subtitle: string; children?: ReactNode }) {
  return <div className="page-heading"><div><h1>{title}</h1><p>{subtitle}</p></div>{children}</div>;
}

export function Dashboard({ data, token, busy, action }: ScreenProps) {
  const amira = data.patients.find((patient) => patient.id === 'demo-amira');
  return <>
    <div className="hero jury-hero"><div><h1>{PRODUCT_NAME}</h1><p>Keep unfinished care visible across pregnancy and care teams.</p></div>
    {amira ? <Button asChild><Link to="/workspace?patient=demo-amira">Open Amira’s journey</Link></Button> : <Button disabled={busy} onClick={()=>action('/demo/seed','Synthetic patients are ready.')}>Open Amira’s journey</Button>}</div>
    <HistoricalIdentificationBadge token={token}/>
    <JuryOverview data={data} token={token} />
  </>;
}

export function DemoTools({ data, role, token, busy, action }: ScreenProps) {
  const amira = data.patients.find((patient) => patient.id === 'demo-amira');
  const counts = populationCounts(data);
  const metrics = [
    { title: 'Synthetic patients', value: counts.patients, icon: Users, path: '/workspace', tone: 'teal' },
    { title: 'Open obligations', value: counts.open, icon: ClipboardList, path: '/passport', tone: 'amber' },
    { title: 'Pending reviews', value: counts.pending, icon: Workflow, path: '/resolution', tone: 'blue' },
    { title: 'Active transitions', value: counts.transitions, icon: GitBranch, path: '/workspace', tone: 'teal' },
    { title: 'Verified closures', value: counts.verified, icon: ShieldCheck, path: '/audit', tone: 'green' },
    { title: 'Blocked or escalated', value: counts.blocked, icon: CircleAlert, path: '/audit', tone: 'rose' },
  ];
  return <>
    <Heading title="Demo tools" subtitle="Synthetic demonstration controls and technical panels." />
    <DemoAdmin token={token}>
    <DemoClock token={token} role={role} controls />
    {!amira && <Button disabled={busy} onClick={()=>action('/demo/seed','Synthetic patient and obligation are ready.')}>Load demo patient</Button>}
    <div className="metric-grid">{metrics.map(({ title, value, icon: Icon, path, tone }) => <Link key={title} className="metric" to={path}>
      <div><span className={'metric-icon ' + tone}><Icon size={19} /></span><ArrowUpRight size={15} /></div>
      <strong>{value}</strong><span>{title}</span>
    </Link>)}</div>
    <PreventionQueue token={token} role={role} />
    <TspQueue token={token} role={role} />
    <HandoffSetup token={token} role={role} available={data.patients.some((patient) => patient.id === HANDOFF_PATIENT)} />
    <Panel title="Patient registry">
      {data.patients.length ? <div className="table-wrap"><table><thead><tr><th>Patient</th><th>Life stage</th><th>Open obligations</th><th>Workspace</th></tr></thead>
        <tbody>{data.patients.map((patient) => <tr key={patient.id}>
          <td><strong>{patientName(patient)}</strong></td><td><Status value={patient.stage} /></td>
          <td>{data.clinical_obligations.filter((item) => item.patient_id === patient.id && item.status === 'open').length}</td>
          <td><Link className="text-link" to={'/workspace?patient=' + patient.id}>Open workspace <ArrowRight size={15} /></Link></td>
        </tr>)}</tbody></table></div>
        : <Empty>Load the demo patient as a coordinator to begin.</Empty>}
    </Panel>
    {role === 'coordinator' && amira && <details className="panel expandable"><summary><RotateCcw size={15} /> Reset Amira demo</summary>
      <div className="inset reset-content">
        <p>Restore Amira to preconception with one open obligation. Previous demo records and audit history move to a separate archive.</p>
        <Button disabled={busy} variant="danger" onClick={() =>
          action('/demo/reset-amira', 'Amira is ready at preconception. Previous demo runs remain archived.')}>Confirm reset</Button>
      </div>
    </details>}
    <div className="two-columns"><Innovations /><Evaluation /></div>
    </DemoAdmin>
  </>;
}

export { Workspace } from './Workspace';

export { Passport } from './Passport';

export function Resolution({ data, role, token, busy, busyPath, action }: ScreenProps) {
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [params, setParams] = useSearchParams();
  const ordered = [...data.clinical_obligations].sort((a, b) => a.created.localeCompare(b.created));
  const requested = params.get('obligation');
  const selected = requested ? ordered.find((item) => item.id === requested) :
    ordered.find((item) => item.status === 'open') || ordered[0];
  const patient = data.patients.find((item) => item.id === selected?.patient_id);
  const runs = data.agent_executions.filter((run) => run.obligation_id === selected?.id)
    .sort((a, b) => b.recorded.localeCompare(a.recorded));
  const current = runs[0];
  const currentTask = data.care_coordination_tasks.find((task) => task.execution_id === current?.id);
  const agentPath = selected ? '/obligations/' + selected.id + '/agent' : undefined;
  const status = workflowStatus(current, currentTask?.status, !!agentPath && agentPath === busyPath);
  return <>
    <Heading title="Care-resolution center" subtitle="Coordinate reviewable care actions while clinicians retain decision authority." />
    {patient&&<LatestSourceDocuments token={token} patientId={patient.id}/>}
    {patient && <DecisionReadiness key={patient.id + "-decision"} patientId={patient.id} token={token} role={role} />}
    {patient && <ClinicalInvestigation key={patient.id} patientId={patient.id} token={token} role={role} />}
    <Panel title="Workflow overview" action={<Status value={status} />}>
      <div className="workflow-roles inset">
        <div><strong>Deterministic clinical rules</strong><p>Generate obligations and check the requirements for closure.</p></div>
        <div><strong>LangGraph orchestration</strong><p>Reconciles evidence and prepares a proposal using local deterministic logic.</p></div>
        <div><strong>Human clinician</strong><p>Reviews the proposal and authorizes action against the current evidence.</p></div>
      </div>
      <div className="inset">
        <WorkflowSteps nodes={data.workflow_nodes} />
        <p className="muted workflow-note">The API authorizes the request before execution and persists the result and audit. Human review takes place after routing.</p>
      </div>
    </Panel>
    <Panel title="Coordination case" action={ordered.length ? <label className="field-inline">Coordination obligation <select
      aria-label="Coordination obligation" value={selected?.id || ''} onChange={(event) => setParams({ obligation: event.target.value })}>
      {!selected && <option value="" disabled>Choose an obligation</option>}
      {ordered.map((item) => <option key={item.id} value={item.id}>{titleFor(data, item)} · {demoPatient(item.patient_id)}</option>)}
    </select></label> : undefined}>
      {selected ? <div className="inset coordination-case">
        <div><strong>{patient ? patientName(patient) : demoPatient(selected.patient_id)} · {titleFor(data, selected)}</strong>
          <p>{selected.status === 'closed' ? 'Verified closure has been recorded.' : !current
            ? 'A coordinator can run the workflow to prepare a proposal for human review.'
            : status === 'completed' ? 'A reviewer decision is recorded. Review completion and verified closure are separate.'
              : status === 'escalated' ? 'The case requires reviewer or evidence follow-up.' : 'Use the recorded execution below to see the current proposal and its evidence.'}</p></div>
        <div className="actions">
          {role === 'coordinator' && selected.status === 'open' && agentPath && <Button disabled={busy}
            onClick={() => action(agentPath, 'Coordination action routed for review.')}><Workflow size={16} /> Run care-resolution agent</Button>}
          <Button asChild variant="outline"><Link to={'/passport?obligation=' + selected.id}>Open selected passport <ArrowRight size={15} /></Link></Button>
        </div>
      </div> : <Empty>Select an obligation or <Link className="text-link" to="/">open the patient registry</Link>.</Empty>}
    </Panel>
    {runs.filter((execution) => execution.result.finding === 'failed').map((execution) =>
      <Panel key={execution.id} title="Coordination run failed" action={<Status value="failed" />}>
        <div className="inset"><p>{moment(execution.recorded)} · {execution.result.action}</p>
          <details><summary>Evidence references</summary>{execution.result.evidence_refs.join(', ') || 'None recorded'}</details>
          <RunTrace trace={execution.result.trace} />
          <Link className="text-link" to={'/passport?obligation=' + execution.obligation_id}>Open passport</Link></div>
      </Panel>)}
    {selected && runs.map((execution) => {
      const task = data.care_coordination_tasks.find((entry) => entry.execution_id === execution.id);
      if (!task) return null;
      const item = selected;
      const review = data.clinical_approvals.find((entry) => entry.task_id === task.id);
      const rule = data.rule_versions.find((entry) => entry.id === item.rule_key);
      const currentEvidence = completionEvidence(data, item);
      const evidenceRefs = currentEvidence.map((row) => row.resource.resourceType + '/' + row.id);
      const sourceRefs = data.clinical_evidence.filter((row) => row.patient_id === item.patient_id &&
        (row.id === item.source_id || row.resource.resourceType === 'Observation' && row.resource.code?.coding?.some(
          (coding) => coding.system === 'https://reprobridge.example/fhir/CodeSystem/demo' && coding.code === rule?.definition.trigger,
        ))).map((row) => row.resource.resourceType + '/' + row.id);
      const expectedRefs = [...new Set([...evidenceRefs, ...sourceRefs])].sort();
      const stale = JSON.stringify([...execution.result.evidence_refs].sort()) !== JSON.stringify(expectedRefs);
      return <Panel key={task.id} title={titleFor(data, item)} action={<Status value={task.status} />}>
        <div className="inset"><p className="field-kicker">Proposed follow-up</p><p className="proposal">{task.action}</p>
          <RunTrace trace={execution.result.trace} /></div>
        <dl className="details"><div><dt>Reconciliation</dt><dd><Status value={execution.result.finding} /></dd></div>
          <div><dt>Routing</dt><dd>{label(execution.result.route)} required</dd></div>
          <div><dt>Authorization</dt><dd>{label(execution.actor)} request accepted by the API.</dd></div>
          <div><dt>Execution</dt><dd>{moment(execution.recorded)} · {label(execution.actor)}</dd></div>
          <div><dt>Evidence reviewed by agent</dt><dd><details><summary>Source references</summary>{execution.result.evidence_refs.join(', ')}</details></dd></div>
          <div><dt>External tools invoked</dt><dd>None. Nodes use authorized records supplied by the backend.</dd></div>
          {review && <div><dt>Reviewer decision</dt><dd>{label(review.decision)}{review.note && ' · ' + review.note}
            <details><summary>Reviewed source references</summary>{review.evidence_refs.join(', ') || 'No completion evidence at decision time'}</details></dd></div>}
        </dl>
        {task.status === 'pending' && stale && <div className="inset">
          <Feedback message="Evidence changed. Run coordination again before approving this proposal." error />
          {role === 'coordinator' && <Button disabled={busy} onClick={() =>
            action('/obligations/' + item.id + '/agent', 'Updated proposal sent for review.')}>Run coordination again</Button>}
        </div>}
        {role === 'reviewer' && task.status === 'pending' && <div className="inset review-controls">
          <strong>Current completion evidence</strong>
          {currentEvidence.length ? <ul>{currentEvidence.map((row) =>
            <li key={row.id}>{row.resource.code?.text || row.resource.resourceType} · {row.resource.status} · {row.resource.valueString}<details><summary>Source identifier</summary>{row.resource.resourceType}/{row.id}</details></li>,
          )}</ul> : <p>No completion evidence submitted.</p>}
          <label>Review note <input value={notes[task.id] || ''} maxLength={300} onChange={(event) => setNotes({ ...notes, [task.id]: event.target.value })} /></label>
          <div className="actions">{(['approve', 'reject', 'request_evidence'] as const).map((decision) =>
            <Button key={decision} variant={decision === 'approve' ? 'primary' : decision === 'reject' ? 'danger' : 'outline'}
              disabled={busy || (decision === 'approve' && stale)}
              onClick={() => action('/tasks/' + task.id + '/review', 'Reviewer decision recorded.',
                { decision, note: notes[task.id] || '', evidence_refs: evidenceRefs })}>
              {decision === 'request_evidence' ? 'Request additional evidence' : label(decision)}</Button>)}</div>
        </div>}
      </Panel>;
    })}
  </>;
}

export { AuditScreen } from './AuditScreen';

function AuditTable({ events }: { events: Audit[] }) {
  if (!events.length) return <Empty>No events recorded yet.</Empty>;
  return <div className="table-wrap audit-table" role="region" aria-label="Scrollable audit table" tabIndex={0}><table><thead><tr><th>Action</th><th>Actor</th><th>Time</th><th>Evidence</th><th>Rule version</th></tr></thead>
    <tbody>{events.map((event) => <tr key={event.sequence}><td><strong>{label(event.action)}</strong>
      <small>{displayText(event.detail.reason || event.detail.candidate_title || demoPatient(event.patient_id))}{event.detail.demo_date && <span> · {event.detail.demo_date} · demo calendar</span>}</small></td><td>{label(event.actor)}</td><td>{moment(event.recorded)}</td>
      <td>{event.evidence_refs.length ? <details><summary>Source references ({event.evidence_refs.length})</summary>{event.evidence_refs.join(', ')}</details> : '—'}</td><td><details><summary>Rule details</summary>{event.rule_key || event.detail.evaluated_rule || (event.detail.relevance_rule_id ? event.detail.relevance_rule_id + ' version ' + event.detail.relevance_rule_version : '—')}</details></td></tr>)}</tbody></table></div>;
}
