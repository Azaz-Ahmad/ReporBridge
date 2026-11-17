import { useState, type ReactNode } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowDownToLine, ArrowRight, ArrowUpRight, CalendarDays, ClipboardList, GitBranch, HeartPulse, Link2, Plus, ShieldCheck, Users, Workflow } from 'lucide-react';
import { api } from './api';
import { Button, Empty, Feedback, Panel, Status } from './ui';
import { label, moment, patientName, type Audit, type Obligation, type Role, type Snapshot } from './types';

export type ScreenProps = {
  data: Snapshot; role: Role; token: string; busy: boolean;
  action: (path: string, success: string, body?: unknown) => void;
};

function Heading({ title, subtitle, children }: { title: string; subtitle: string; children?: ReactNode }) {
  return <div className="page-heading"><div><h1>{title}</h1><p>{subtitle}</p></div>{children}</div>;
}

function titleFor(data: Snapshot, item: Obligation) {
  return label(data.rule_versions.find((rule) => rule.id === item.rule_key)?.rule_id || item.rule_key);
}

export function Dashboard({ data, role, busy, action }: ScreenProps) {
  const metrics = [
    { title: 'Synthetic patients', value: data.patients.length, icon: Users, path: '/workspace', tone: 'violet' },
    { title: 'Open obligations', value: data.clinical_obligations.filter((item) => item.status === 'open').length, icon: ClipboardList, path: '/passport', tone: 'amber' },
    { title: 'Pending reviews', value: data.care_coordination_tasks.filter((task) => task.status === 'pending').length, icon: Workflow, path: '/resolution', tone: 'blue' },
    { title: 'Pregnancy transitions', value: data.life_stage_events.filter((event) => event.stage === 'pregnancy').length, icon: GitBranch, path: '/workspace', tone: 'violet' },
    { title: 'Verified closures', value: data.clinical_obligations.filter((item) => item.status === 'closed').length, icon: ShieldCheck, path: '/audit', tone: 'green' },
  ];
  return <>
    <div className="hero"><div><div className="eyebrow"><HeartPulse size={16} /> CARE CONTINUITY</div>
      <h1>Population intelligence</h1>
      <p>Track outstanding care across preconception and pregnancy.</p></div>
      {role === 'coordinator' && !data.patients.some((p) => p.id === 'demo-amira') &&
        <Button disabled={busy} onClick={() => action('/demo/seed', 'Synthetic patient and obligation are ready.')}><Plus size={16} /> Load demo patient</Button>}
    </div>
    <div className="metric-grid">{metrics.map(({ title, value, icon: Icon, path, tone }) => <Link key={title} className="metric" to={path}>
      <div><span className={'metric-icon ' + tone}><Icon size={19} /></span><ArrowUpRight size={15} /></div>
      <strong>{value}</strong><span>{title}</span>
    </Link>)}</div>
    <Panel title="Patient registry">
      {data.patients.length ? <div className="table-wrap"><table><thead><tr><th>Patient</th><th>Life stage</th><th>Open obligations</th><th>Workspace</th></tr></thead>
        <tbody>{data.patients.map((patient) => <tr key={patient.id}>
          <td><strong>{patientName(patient)}</strong><small>{patient.id}</small></td><td><Status value={patient.stage} /></td>
          <td>{data.clinical_obligations.filter((item) => item.patient_id === patient.id && item.status === 'open').length}</td>
          <td><Link className="text-link" to={'/workspace?patient=' + patient.id}>Open workspace <ArrowRight size={15} /></Link></td>
        </tr>)}</tbody></table></div>
        : <Empty>Load the demo patient as a coordinator to begin.</Empty>}
    </Panel>
    <Panel title="Recent activity" action={<Link className="text-link" to="/audit">View audit <ArrowRight size={15} /></Link>}>
      <AuditTable events={data.audit_events.slice(0, 4)} />
    </Panel>
  </>;
}

export function Workspace({ data, role, busy, action }: ScreenProps) {
  const [params, setParams] = useSearchParams();
  const patient = data.patients.find((item) => item.id === params.get('patient')) || data.patients[0];
  return <>
    <Heading title="Women’s health workspace" subtitle="Patient record, life-stage timeline, and source findings.">
      {patient && <label className="field-inline">Patient <select value={patient.id} onChange={(e) => setParams({ patient: e.target.value })}>
        {data.patients.map((item) => <option value={item.id} key={item.id}>{patientName(item)}</option>)}
      </select></label>}
    </Heading>
    {!patient ? <Empty>Load a synthetic patient from the population dashboard.</Empty> : <>
      <Panel title={patientName(patient)} action={<Status value={patient.stage} />}>
        <dl className="details"><div><dt>Patient ID</dt><dd>{patient.id}</dd></div>
          <div><dt>Birth date</dt><dd>{patient.resource.birthDate}</dd></div><div><dt>Administrative gender</dt><dd>{label(patient.resource.gender || 'unknown')}</dd></div></dl>
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
                ? 'Observation/' + event.evidence_id : 'Patient/' + patient.id}</small></li>)}
        </ul></Panel>
        <Panel title="Obligations">
          {data.clinical_obligations.filter((item) => item.patient_id === patient.id).map((item) =>
            <Link key={item.id} className="record-link" to={'/passport?obligation=' + item.id}><strong>{titleFor(data, item)}</strong><Status value={item.status} /><ArrowRight size={16} /></Link>,
          )}
          {!data.clinical_obligations.some((item) => item.patient_id === patient.id) && <Empty>No obligations recorded.</Empty>}
        </Panel>
      </div>
      <Panel title="Clinical evidence">
        <div className="table-wrap"><table><thead><tr><th>Resource</th><th>Finding</th><th>Value</th><th>Status</th></tr></thead>
          <tbody>{data.clinical_evidence.filter((row) => row.patient_id === patient.id).map(({ resource }) => <tr key={resource.id}>
            <td>{resource.resourceType}/{resource.id}</td><td>{label(resource.code?.coding?.[0]?.code || '—')}</td>
            <td>{resource.valueString || '—'}</td><td>{label(resource.status || '—')}</td></tr>)}</tbody></table></div>
      </Panel>
    </>}
  </>;
}

export function Passport({ data, role, busy, action }: ScreenProps) {
  const [params, setParams] = useSearchParams();
  const item = data.clinical_obligations.find((entry) => entry.id === params.get('obligation')) || data.clinical_obligations[0];
  const rule = data.rule_versions.find((entry) => entry.id === item?.rule_key);
  const source = data.clinical_evidence.find((entry) => entry.id === item?.source_id)?.resource;
  const edges = data.obligation_dependencies.filter((edge) => edge.obligation_id === item?.id || edge.depends_on === item?.id);
  return <>
    <Heading title="Clinical obligation passport" subtitle="Source evidence, ownership, and closure requirements.">
      {!!item && <label className="field-inline">Obligation <select value={item.id} onChange={(event) => setParams({ obligation: event.target.value })}>
        {data.clinical_obligations.map((entry) => <option key={entry.id} value={entry.id}>{titleFor(data, entry)} · {entry.patient_id}</option>)}
      </select></label>}
    </Heading>
    {!item || !rule || !source ? <Empty>Evaluate a synthetic patient to create an obligation.</Empty> : <>
      <Panel title={titleFor(data, item)} action={<Status value={item.status} />}>
        <div className="inset"><span className="pill amber">Illustrative demo rule</span></div>
        <dl className="details"><div><dt>Obligation ID</dt><dd>{item.id}</dd></div><div><dt>Patient ID</dt><dd>{item.patient_id}</dd></div>
          <div><dt>Pathway</dt><dd>{label(rule.pathway_id)}</dd></div><div><dt>Rule ID and version</dt><dd>{item.rule_key}</dd></div>
          <div><dt>Assigned owner</dt><dd>{item.owner}</dd></div><div><dt>Source evidence</dt><dd>{source.resourceType}/{source.id}</dd></div>
          <div><dt>Required follow-up</dt><dd>{rule.definition.description}</dd></div>
          <div><dt>Closure requirements</dt><dd>Final {rule.definition.closure} evidence, reviewer approval, and resolution of required dependencies.</dd></div>
          <div><dt>Rule documentation</dt><dd>{rule.definition.source}</dd></div></dl>
        {role === 'coordinator' && item.status === 'open' && <div className="actions inset">
          <Button disabled={busy} onClick={() => action('/obligations/' + item.id + '/agent', 'Coordination action routed for review.')}>
            <Workflow size={17} /> Run care-resolution agent</Button>
          <Button variant="outline" disabled={busy} onClick={() => action('/obligations/' + item.id + '/close', 'Closure verified.')}>Verify closure</Button>
        </div>}
      </Panel>
      <Panel title="Cross-pathway dependencies">
        {edges.length ? edges.map((edge) => {
          const predecessor = data.clinical_obligations.find((entry) => entry.id === edge.depends_on)!;
          const successor = data.clinical_obligations.find((entry) => entry.id === edge.obligation_id)!;
          return <div className="dependency" key={edge.id}><Link2 size={18} />
            <div><Link to={'/passport?obligation=' + predecessor.id}>{titleFor(data, predecessor)}</Link>
              {' must close before '}<Link to={'/passport?obligation=' + successor.id}>{titleFor(data, successor)}</Link>
              <small>{label(edge.kind)} · {edge.rule_key}</small></div><Status value={predecessor.status} /></div>;
        }) : <Empty>No dependency recorded for this obligation.</Empty>}
      </Panel>
      <Panel title="Obligation history"><AuditTable events={data.audit_events.filter((event) => event.obligation_id === item.id)} /></Panel>
    </>}
  </>;
}

export function Resolution({ data, role, busy, action }: ScreenProps) {
  const [notes, setNotes] = useState<Record<string, string>>({});
  return <>
    <Heading title="Care-resolution center" subtitle="Review the agent’s evidence reconciliation and proposed coordination actions." />
    {data.agent_executions.filter((execution) => execution.result.finding === 'failed').map((execution) =>
      <Panel key={execution.id} title="Coordination run failed" action={<Status value="failed" />}>
        <p className="inset">{moment(execution.recorded)} · {execution.result.action}
          {' '}<Link className="text-link" to={'/passport?obligation=' + execution.obligation_id}>Open passport</Link></p>
      </Panel>)}
    {!data.care_coordination_tasks.length && <Empty>Run the care-resolution agent from an open obligation passport.</Empty>}
    {[...data.care_coordination_tasks].reverse().map((task) => {
      const item = data.clinical_obligations.find((entry) => entry.id === task.obligation_id)!;
      const execution = data.agent_executions.find((entry) => entry.id === task.execution_id)!;
      const review = data.clinical_approvals.find((entry) => entry.task_id === task.id);
      const rule = data.rule_versions.find((entry) => entry.id === item.rule_key);
      const currentEvidence = data.clinical_evidence.filter((row) => row.patient_id === item.patient_id &&
        row.resource.resourceType === 'Observation' && row.resource.code?.coding?.some((coding) =>
          coding.system === 'https://reprobridge.example/fhir/CodeSystem/demo' && coding.code === rule?.definition.closure,
        ),
      );
      const evidenceRefs = currentEvidence.map((row) => row.resource.resourceType + '/' + row.id);
      const sourceRefs = data.clinical_evidence.filter((row) => row.patient_id === item.patient_id &&
        (row.id === item.source_id || row.resource.resourceType === 'Observation' && row.resource.code?.coding?.some(
          (coding) => coding.system === 'https://reprobridge.example/fhir/CodeSystem/demo' && coding.code === rule?.definition.trigger,
        ))).map((row) => row.resource.resourceType + '/' + row.id);
      const expectedRefs = [...new Set([...evidenceRefs, ...sourceRefs])].sort();
      const stale = JSON.stringify([...execution.result.evidence_refs].sort()) !== JSON.stringify(expectedRefs);
      return <Panel key={task.id} title={titleFor(data, item)} action={<Status value={task.status} />}>
        <div className="inset"><p className="proposal">{task.action}</p></div>
        <dl className="details"><div><dt>Reconciliation</dt><dd><Status value={execution.result.finding} /></dd></div>
          <div><dt>Routing</dt><dd>{label(execution.result.route)}</dd></div>
          <div><dt>Execution</dt><dd>{moment(execution.recorded)} · {label(execution.actor)}</dd></div>
          <div><dt>Evidence reviewed by agent</dt><dd>{execution.result.evidence_refs.join(', ')}</dd></div>
          {review && <div><dt>Reviewer decision</dt><dd>{label(review.decision)}{review.note && ' · ' + review.note}
            <small>{review.evidence_refs.join(', ') || 'No completion evidence at decision time'}</small></dd></div>}
        </dl>
        {task.status === 'pending' && stale && <div className="inset">
          <Feedback message="Evidence changed. Run coordination again before approving this proposal." error />
          {role === 'coordinator' && <Button disabled={busy} onClick={() =>
            action('/obligations/' + item.id + '/agent', 'Updated proposal sent for review.')}>Run coordination again</Button>}
        </div>}
        {role === 'reviewer' && task.status === 'pending' && <div className="inset review-controls">
          <strong>Current completion evidence</strong>
          {currentEvidence.length ? <ul>{currentEvidence.map((row) =>
            <li key={row.id}>{row.resource.resourceType}/{row.id} · {row.resource.status} · {row.resource.valueString}</li>,
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
    {role === 'coordinator' && current && <Panel title="Submit synthetic completion evidence">
      <div className="inset"><label className="field-inline">Obligation <select value={current.id} onChange={(event) => setSelected(event.target.value)}>
        {open.map((item) => <option key={item.id} value={item.id}>{titleFor(data, item)} · {item.patient_id}</option>)}</select></label>
        <div className="actions">
          <Button disabled={busy} onClick={() => action('/obligations/' + current.id + '/demo-completion', 'Verified fixture submitted. Reviewer approval is still required.', { scenario: 'verified' })}>Add verified evidence</Button>
          <Button disabled={busy} variant="danger" onClick={() => action('/obligations/' + current.id + '/demo-completion', 'Conflicting fixture submitted.', { scenario: 'conflicting' })}>Add conflicting evidence</Button>
        </div>
      </div>
    </Panel>}
    <Panel title="Verification results">
      <AuditTable events={data.audit_events.filter((event) => ['closure_verified', 'closure_blocked', 'closure_reopened'].includes(event.action))} />
    </Panel>
    <Panel title="FHIR R4 export">
      {data.patients.length ? data.patients.map((patient) => <div className="record-link" key={patient.id}>
        <strong>{patientName(patient)}</strong><Button variant="outline" onClick={() => void download(patient.id)}><ArrowDownToLine size={16} /> Download FHIR bundle</Button>
      </div>) : <Empty>No patient bundles available.</Empty>}
    </Panel>
    <Panel title="Lifecycle audit history"><AuditTable events={data.audit_events} /></Panel>
  </>;
}

function AuditTable({ events }: { events: Audit[] }) {
  if (!events.length) return <Empty>No events recorded yet.</Empty>;
  return <div className="table-wrap"><table><thead><tr><th>Action</th><th>Actor</th><th>Time</th><th>Evidence</th><th>Rule version</th></tr></thead>
    <tbody>{events.map((event) => <tr key={event.sequence}><td><strong>{label(event.action)}</strong>
      <small>{event.detail.reason || event.patient_id}</small></td><td>{label(event.actor)}</td><td>{moment(event.recorded)}</td>
      <td>{event.evidence_refs.join(', ') || '—'}</td><td>{event.rule_key || event.detail.evaluated_rule || '—'}</td></tr>)}</tbody></table></div>;
}
