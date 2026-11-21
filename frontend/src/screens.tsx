import { DemoCorrection } from './DemoCorrection';
import { CoordinationNextAction, GuidelineTraceability } from './Coordination';
import { useState, type ReactNode } from 'react';
import { Link, useLocation, useSearchParams } from 'react-router-dom';
import { ArrowDownToLine, ArrowRight, ArrowUpRight, CalendarDays, CircleAlert, ClipboardList, GitBranch, HeartPulse, Plus, RotateCcw, ShieldCheck, Users, Workflow } from 'lucide-react';
import { PRODUCT_NAME, demoPatient, displayText } from './presentation';
import { api } from './api';
import { EarlierRecords } from './History';
import { JuryOverview, DemoAdmin, JourneyStrip } from './Jury';
import { HANDOFF_PATIENT, HandoffSetup, HandoffPanel, HandoffTimeline } from './Handoff';
import { TspQueue, TspWindow } from './Tsp';
import { ClinicalExplorer } from './ClinicalExplorer';
import { ClinicalInvestigation } from './ClinicalInvestigation';
import { PreventionQueue, PreventionPassport, DecisionReadiness, DecisionTimeline, DecisionHistory } from './Prevention';
import { Button, Empty, Feedback, Panel, Status } from './ui';
import { closureMessage, completionEvidence, DependencyMap, Evaluation, Innovations, Interoperability, Journey, Lifecycle, obligationTitle as titleFor, populationCounts, RunTrace, WorkflowSteps, workflowStatus } from './showcase';
import { label, moment, patientName, type Audit, type Role, type Snapshot } from './types';

export type ScreenProps = {
  data: Snapshot; role: Role; token: string; busy: boolean; busyPath?: string;
  action: (path: string, success: string, body?: unknown) => void;
};

function Heading({ title, subtitle, children }: { title: string; subtitle: string; children?: ReactNode }) {
  return <div className="page-heading"><div><h1>{title}</h1><p>{subtitle}</p></div>{children}</div>;
}

export function Dashboard({ data, role, token, busy, action }: ScreenProps) {
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
    <div className="hero jury-hero"><div><h1>{PRODUCT_NAME}</h1><p>Keep unfinished care visible across pregnancy and care teams.</p></div>
    {amira ? <Button asChild><Link to="/workspace?patient=demo-amira">Open Amira’s journey</Link></Button> : <Button disabled={busy} onClick={()=>action('/demo/seed','Synthetic patients are ready.')}>Open Amira’s journey</Button>}</div>
    <JuryOverview data={data} token={token} />
    <DemoAdmin token={token}>
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

export function Workspace({ data, role, token, busy, action }: ScreenProps) {
  const [params, setParams] = useSearchParams();
  const patientId = params.get('patient');
  const patient = patientId ? data.patients.find((item) => item.id === patientId) : data.patients[0];
  const obligations = data.clinical_obligations.filter((item) => item.patient_id === patient?.id);
  const assessment = obligations.find((item) => data.rule_versions.some((rule) =>
    rule.id === item.rule_key && rule.pathway_id === 'preconception'));
  const scenario = assessment && data.case_context?.[assessment.id];
  return <>
    <Heading title="Women’s health workspace" subtitle="Patient record, life-stage timeline, and source findings.">
      {patient && <label className="field-inline">Patient <select value={patient.id} onChange={(e) => setParams({ patient: e.target.value })}>
        {data.patients.map((item) => <option value={item.id} key={item.id}>{patientName(item)}</option>)}
      </select></label>}
    </Heading>
    {!patient ? <Empty>{patientId ? 'This patient is unavailable. ' : 'Load a synthetic patient. '}
      <Link className="text-link" to="/">Open population dashboard</Link></Empty> : <>
      <Panel title={patientName(patient)} action={<Status value={patient.stage} />}>
        <Journey stage={patient.stage} />
        <JourneyStrip token={token} patientId={patient.id} />
        {assessment && scenario && <div className="clinical-context">
          <p className="field-kicker">Documented clinical context</p>
          <strong>{scenario.finding}</strong>
          <p>{assessment.status === 'closed' ? closureMessage(data, assessment)
            : patient.stage === 'pregnancy' && data.obligation_dependencies.some((edge) => edge.depends_on === assessment.id)
              ? 'Pregnancy is registered and this assessment is still open. The linked handoff review keeps it visible to the receiving care team.'
              : scenario.rationale}</p>
          <Link className="text-link" to={'/passport?obligation=' + assessment.id}>Open assessment passport <ArrowRight size={15} /></Link>
        </div>}
        <dl className="details">
          <div><dt>Birth date</dt><dd>{patient.resource.birthDate}</dd></div><div><dt>Current pathway</dt><dd>{label(patient.stage)}</dd></div>
          <div><dt>Administrative gender</dt><dd>{label(patient.resource.gender || 'unknown')}</dd></div></dl>
        {role === 'coordinator' && <div className="actions inset">
          <Button variant="outline" disabled={busy} onClick={() => action('/patients/' + patient.id + '/evaluate', 'Applicable rules evaluated.')}>Evaluate rules</Button>
          {patient.stage === 'preconception' && <Button disabled={busy} onClick={() => action('/patients/' + patient.id + '/pregnancy', 'Pregnancy registered. Existing obligations were retained.')}><CalendarDays size={17} /> Register pregnancy</Button>}
        </div>}
      </Panel>
      <div className="two-columns">
        <Panel title="Life-stage timeline"><ul className="timeline">
          {data.life_stage_events.filter((event) => event.patient_id === patient.id)
            .sort((first, later) => first.recorded.localeCompare(later.recorded)).map((event) => <li key={event.id}>
              <strong>{label(event.stage)}</strong><small>{moment(event.recorded)} · {event.evidence_id
                ? 'Source observation recorded' : 'Patient registration'}</small></li>)}
        </ul></Panel>
        <Panel title="Obligations">
          {obligations.map((item) =>
            <Link key={item.id} className="record-link" to={'/passport?obligation=' + item.id}><strong>{titleFor(data, item)}</strong><Status value={item.status} /><ArrowRight size={16} /></Link>,
          )}
          {!obligations.length && <Empty>No obligations recorded.</Empty>}
        </Panel>
      </div>
      <EarlierRecords token={token} role={role} patientId={patient.id} />
      <HandoffPanel token={token} role={role} patientId={patient.id} />
      <HandoffTimeline token={token} patientId={patient.id} />
      <DecisionTimeline token={token} patientId={patient.id} />
      <TspWindow token={token} patientId={patient.id} timeline />
      <div id="dependencies"><DependencyMap data={data} patientId={patient.id} /></div>
      <ClinicalExplorer key={patient.id} patientId={patient.id} token={token} coordinator={role === 'coordinator'} />
      <Panel title="Clinical evidence">
        <div className="table-wrap clinical-table"><table role="table"><thead><tr><th>Resource</th><th>Finding</th><th>Value</th><th>Status</th></tr></thead>
          <tbody role="rowgroup">{data.clinical_evidence.filter((row) => row.patient_id === patient.id).map(({ resource }) => <tr role="row" key={resource.id}>
            <td role="cell"><span className="mobile-cell-label" aria-hidden="true">Resource</span>{resource.resourceType}</td>
            <td role="cell"><span className="mobile-cell-label" aria-hidden="true">Finding</span>{resource.code?.text || label(resource.code?.coding?.[0]?.code || '—')}</td>
            <td role="cell"><span className="mobile-cell-label" aria-hidden="true">Value</span>{resource.valueString || '—'}</td>
            <td role="cell"><span className="mobile-cell-label" aria-hidden="true">Status</span>{label(resource.status || '—')}</td></tr>)}</tbody></table></div>
      </Panel>
    </>}
  </>;
}

export function Passport({ data, role, token, busy, action }: ScreenProps) {
  const [params, setParams] = useSearchParams();
  const obligationId = params.get('obligation');
  const item = obligationId ? data.clinical_obligations.find((entry) => entry.id === obligationId) : data.clinical_obligations[0];
  const rule = data.rule_versions.find((entry) => entry.id === item?.rule_key);
  const source = data.clinical_evidence.find((entry) => entry.id === item?.source_id)?.resource;
  const scenario = item && data.case_context?.[item.id];
  const { hash } = useLocation();
  const history = data.audit_events.filter((event) => event.obligation_id === item?.id);
  const patient = data.patients.find((entry) => entry.id === item?.patient_id);
  return <>
    <Heading title="Clinical obligation passport" subtitle="Source evidence, ownership, and closure requirements.">
      {!!item && <label className="field-inline">Passport obligation <select aria-label="Passport obligation" value={item.id} onChange={(event) => setParams({ obligation: event.target.value })}>
        {data.clinical_obligations.map((entry) => <option key={entry.id} value={entry.id}>{titleFor(data, entry)} · {demoPatient(entry.patient_id)}</option>)}
      </select></label>}
    </Heading>
    {!item || !rule || !source ? <Empty>{obligationId ? 'This obligation is unavailable in the current run. ' : 'Evaluate a synthetic patient to create an obligation. '}
      <Link className="text-link" to="/workspace">Open patient workspace</Link></Empty> : <>
      <section className="passport-cover">
        <span className="passport-icon"><ClipboardList size={25} /></span>
        <div><p className="field-kicker">Clinical obligation passport</p><h2>{titleFor(data, item)}</h2>
          <p>{patient ? patientName(patient) : demoPatient(item.patient_id)} · {label(rule.pathway_id)} pathway</p></div>
        <Status value={item.status} />
      </section>
      <EarlierRecords token={token} role={role} patientId={item.patient_id} />
      <HandoffPanel token={token} role={role} patientId={item.patient_id} />
      <PreventionPassport obligationId={item.id} token={token} role={role} />
      <TspWindow token={token} patientId={item.patient_id} role={role} />
      <GuidelineTraceability token={token} patientId={item.patient_id}/>
      <Panel title="Obligation checkpoints"><Lifecycle data={data} item={item} /></Panel>
      <Panel title="Care requirements" action={<span className="pill amber">Illustrative — Not Clinically Approved</span>}>
        <div className="clinical-context">
          <strong>{scenario?.finding || 'Documented source evidence'}</strong>
          <p>{scenario?.rationale || rule.definition.description}</p>
          {patient?.stage === 'pregnancy' && item.status === 'open' &&
            scenario && data.obligation_dependencies.some((edge) => edge.depends_on === item.id) &&
            <p>The assessment remains open after pregnancy registration and is linked to the pregnancy handoff review.</p>}
        </div>
        <dl className="details"><div><dt>Assigned owner</dt><dd>{item.owner}</dd></div>
          <div><dt>Next action</dt><dd><CoordinationNextAction token={token} patientId={item.patient_id}/></dd></div>
          <div><dt>What is needed for closure</dt><dd>{scenario?.completion || 'A qualifying final completion record.'} Reviewer approval must cover the current evidence and any configured prerequisite must be satisfied.</dd></div>
          <div><dt>Current closure check</dt><dd>{closureMessage(data, item)}</dd></div>
          <div><dt>Last updated</dt><dd>{moment(history[0]?.recorded ?? item.created)}</dd></div></dl>
        {role === 'coordinator' && item.status === 'open' && <div className="actions inset">
          <Button disabled={busy} onClick={() => action('/obligations/' + item.id + '/agent', 'Coordination action routed for review.')}>
            <Workflow size={17} /> Run care-resolution agent</Button>
          <Button variant="outline" disabled={busy} onClick={() => action('/obligations/' + item.id + '/close', 'Closure verified.')}>Verify closure</Button>
          <Link className="text-link" to={'/resolution?obligation=' + item.id}>Open review queue <ArrowRight size={15} /></Link>
        </div>}
      </Panel>
      <details className="panel expandable" id="provenance" open={hash === '#provenance' || undefined}>
        <summary>Source evidence and provenance</summary>
        <dl className="details"><div><dt>Source resource</dt><dd>{source.resourceType}/{source.id}</dd></div>
          <div><dt>Obligation ID</dt><dd>{item.id}</dd></div><div><dt>Patient ID</dt><dd>{item.patient_id}</dd></div>
          <div><dt>Rule ID and version</dt><dd>{item.rule_key}</dd></div>
          <div><dt>Recorded finding</dt><dd>{source.code?.text || scenario?.finding || label(source.code?.coding?.[0]?.code ?? 'Unavailable')} · {source.valueString || '—'}</dd></div>
          <div><dt>Configured evidence codes</dt><dd>{rule.definition.trigger} → {rule.definition.closure}</dd></div>
          <div><dt>Evidence status</dt><dd>{label(source.status ?? 'Unavailable')}</dd></div>
          <div><dt>Rule documentation</dt><dd>{rule.definition.source}</dd></div></dl>
        <div className="inset"><Link className="text-link" to={'/workspace?patient=' + item.patient_id}>Open patient evidence <ArrowRight size={15} /></Link></div>
      </details>
      <DependencyMap data={data} patientId={item.patient_id} obligationId={item.id} />
      <Panel title="Obligation history"><AuditTable events={history} /></Panel>
    </>}
  </>;
}

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

export function AuditScreen({ data, role, token, busy, action }: ScreenProps) {
  const [selected, setSelected] = useState('');
  const [error, setError] = useState('');
  const open = data.clinical_obligations.filter((item) => item.status === 'open');
  const current = open.find((item) => item.id === selected) || open[0];
  const [inspectedId, setInspectedId] = useState('');
  const inspected = data.clinical_obligations.find((item) => item.id === inspectedId) ||
    data.clinical_obligations.find((item) => item.status === 'closed') || current;
  const verification = data.audit_events.filter((event) => ['closure_verified', 'closure_blocked', 'closure_reopened'].includes(event.action));
  const lastResult = verification.find((event) => event.obligation_id === inspected?.id);
  const reviews = inspected ? data.clinical_approvals.filter((review) =>
    data.care_coordination_tasks.some((task) => task.id === review.task_id && task.obligation_id === inspected.id)) : [];
  const review = reviews.sort((a, b) => b.recorded.localeCompare(a.recorded))[0];
  const inspectedScenario = inspected && data.case_context?.[inspected.id];
  const proposed = data.care_coordination_tasks.some((task) => task.obligation_id === inspected?.id);
  async function download(patientId: string) {
    setError('');
    try {
      const bundle = await api(token, '/fhir/patients/' + patientId);
      const url = URL.createObjectURL(new Blob([JSON.stringify(bundle, null, 2)], { type: 'application/fhir+json' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = patientId + '-r4.json';
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'FHIR download failed.');
    }
  }
  return <>
    <Heading title="Evidence & audit" subtitle="Inspect submitted evidence, verified closures, and blocked decisions." />
    {error && <Feedback message={error} error />}
    {inspected && <Panel title="Closure evidence review" action={<label className="field-inline">Inspect obligation <select value={inspected.id}
      onChange={(event) => setInspectedId(event.target.value)}>
      {data.clinical_obligations.map((item) => <option key={item.id} value={item.id}>{titleFor(data, item)} · {demoPatient(item.patient_id)}</option>)}
    </select></label>}>
      <div className="verification-compare">
        <div><ClipboardList size={20} /><strong>Action initiated</strong>
          <p>{review ? 'Proposal decision · ' + label(review.decision) + ' by ' + label(review.actor)
            : proposed ? 'A coordination proposal is recorded for human review.' : 'No coordination proposal recorded.'}</p>
          <small>Approving a proposal to obtain evidence leaves closure pending.</small></div>
        <div><ShieldCheck size={20} /><strong>Care obligation verified as resolved</strong>
          <Status value={inspected.status} />
          <p>{closureMessage(data, inspected)}</p>
          {lastResult?.action === 'closure_blocked' && <small>Last closure attempt blocked. {lastResult.detail.reason}</small>}</div>
      </div>
      <dl className="details"><div><dt>Required evidence</dt><dd>{inspectedScenario?.completion || 'A qualifying final completion record.'} Evidence-specific approval and cleared prerequisites are required.</dd></div>
        <div><dt>Supporting records</dt><dd>{completionEvidence(data, inspected).map(({ resource }) =>
          (resource.code?.text || resource.resourceType) + ' · ' + resource.status).join(', ') || 'No completion evidence submitted'}</dd></div>
        <div><dt>Reviewer evidence references</dt><dd><details><summary>Reviewed source references</summary>{review?.evidence_refs.join(', ') || 'None recorded'}</details></dd></div></dl>
    </Panel>}
    {inspected && <Panel title="Correction and reopening"><Lifecycle data={data} item={inspected}/>
      <p>Assigned owner: {inspected.owner}</p>
      <DemoCorrection key={inspected.id} token={token} role={role} obligation={inspected}
        evidenceId={data.closure_evidence.find(row=>row.obligation_id===inspected.id)?.evidence_id}
        evidenceLabel={completionEvidence(data,inspected)[0]?.resource.code?.text}/>
    </Panel>}
    {role === 'coordinator' && current && <Panel title="Submit synthetic completion evidence">
      <div className="inset"><label className="field-inline">Completion evidence obligation <select aria-label="Completion evidence obligation" value={current.id} onChange={(event) => setSelected(event.target.value)}>
        {open.map((item) => <option key={item.id} value={item.id}>{titleFor(data, item)} · {demoPatient(item.patient_id)}</option>)}</select></label>
        <div className="actions">
          <Button disabled={busy} onClick={() => action('/obligations/' + current.id + '/demo-completion', 'Verified fixture submitted. Reviewer approval is still required.', { scenario: 'verified' })}>Add verified evidence</Button>
          <Button disabled={busy} variant="danger" onClick={() => action('/obligations/' + current.id + '/demo-completion', 'Conflicting fixture submitted.', { scenario: 'conflicting' })}>Add conflicting evidence</Button>
        </div>
      </div>
    </Panel>}
    <Panel title="Verification results">
      <AuditTable events={verification} />
    </Panel>
    <Panel title="FHIR R4 export">
      <Interoperability />
      {data.patients.length ? data.patients.map((patient) => <div className="record-link" key={patient.id}>
        <strong>{patientName(patient)}</strong><Button variant="outline" onClick={() => void download(patient.id)}><ArrowDownToLine size={16} /> Download FHIR bundle</Button>
      </div>) : <Empty>No patient bundles available.</Empty>}
    </Panel>
    <DecisionHistory token={token} />
    <Panel title="Lifecycle audit history"><AuditTable events={data.audit_events} /></Panel>
    {data.demo_run_archive.length > 0 && <details className="panel expandable"><summary>Archived Amira demo runs</summary>
      <ul className="inset archive-list">{data.demo_run_archive.map((run) =>
        <li key={run.id}><strong>{moment(run.recorded)}</strong> · {run.audit_count} audit events · {label(run.actor)}<small>{run.id}</small></li>)}</ul>
    </details>}
  </>;
}

function AuditTable({ events }: { events: Audit[] }) {
  if (!events.length) return <Empty>No events recorded yet.</Empty>;
  return <div className="table-wrap audit-table" role="region" aria-label="Scrollable audit table" tabIndex={0}><table><thead><tr><th>Action</th><th>Actor</th><th>Time</th><th>Evidence</th><th>Rule version</th></tr></thead>
    <tbody>{events.map((event) => <tr key={event.sequence}><td><strong>{label(event.action)}</strong>
      <small>{displayText(event.detail.reason || demoPatient(event.patient_id))}</small></td><td>{label(event.actor)}</td><td>{moment(event.recorded)}</td>
      <td>{event.evidence_refs.length ? <details><summary>Source references ({event.evidence_refs.length})</summary>{event.evidence_refs.join(', ')}</details> : '—'}</td><td><details><summary>Rule details</summary>{event.rule_key || event.detail.evaluated_rule || '—'}</details></td></tr>)}</tbody></table></div>;
}
