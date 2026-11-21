import { ArrowRight, CalendarDays, Check, CircleDot, ClipboardList, Database, GitBranch, HeartPulse, ShieldCheck, Workflow } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Empty, Panel, Status } from './ui';
import { label, moment, type Obligation, type Snapshot } from './types';
import results from './evaluation.json';

const evaluation: { run: string; automated: { label: string; result: string }[]; synthetic: string } = results;

const system = 'https://reprobridge.example/fhir/CodeSystem/demo';

export function obligationTitle(data: Snapshot, item: Obligation) {
  const rule = data.rule_versions.find((entry) => entry.id === item.rule_key);
  return data.case_context?.[item.id]?.title || rule?.definition.title || label(rule?.rule_id || item.rule_key);
}

export function closureMessage(data: Snapshot, item: Obligation) {
  if (item.status === 'closed') return 'Qualifying evidence, required approval and any prerequisite were recorded at closure.';
  const reason = data.closure_readiness?.[item.id];
  return reason === undefined ? 'Current closure check is unavailable.' : reason || 'Requirements met. A coordinator can verify closure.';
}

export function completionEvidence(data: Snapshot, item: Obligation) {
  const code = data.rule_versions.find((rule) => rule.id === item.rule_key)?.definition.closure;
  return data.clinical_evidence.filter(({ patient_id, resource }) => patient_id === item.patient_id &&
    resource.resourceType === 'Observation' && resource.code?.coding?.some((entry) => entry.system === system && entry.code === code));
}

export function populationCounts(data: Snapshot) {
  const verification = new Map<string, string>();
  for (const event of [...data.audit_events].sort((a, b) => b.sequence - a.sequence)) {
    if (event.obligation_id && !verification.has(event.obligation_id) &&
      ['closure_blocked', 'closure_reopened', 'closure_verified'].includes(event.action)) {
      verification.set(event.obligation_id, event.action);
    }
  }
  return {
    patients: data.patients.length,
    open: data.clinical_obligations.filter((item) => item.status === 'open').length,
    pending: data.care_coordination_tasks.filter((task) => task.status === 'pending').length,
    transitions: new Set(data.life_stage_events.filter((event) => event.stage === 'pregnancy' &&
      data.patients.some((patient) => patient.id === event.patient_id && patient.stage === 'pregnancy')).map((event) => event.patient_id)).size,
    verified: data.clinical_obligations.filter((item) => item.status === 'closed').length,
    blocked: data.clinical_obligations.filter((item) =>
      item.status === 'open' && ['closure_blocked', 'closure_reopened'].includes(verification.get(item.id) || '')).length,
  };
}

export function Journey({ stage }: { stage: string }) {
  return <ol className="stage-track" aria-label="Reproductive life stages">
    {['preconception', 'pregnancy', 'postpartum'].map((step) => {
      const current = step === stage;
      const completed = step === 'preconception' && stage === 'pregnancy';
      return <li key={step} aria-current={current ? 'step' : undefined} className={current ? 'current' : completed ? 'done' : ''}>
        <span>{completed ? <Check size={16} /> : <CircleDot size={16} />}</span>
        <div><strong>{label(step)}</strong><small>{current ? 'Current stage' : completed ? 'Recorded' : step === 'postpartum' ? 'Planned' : 'Available transition'}</small></div>
      </li>;
    })}
  </ol>;
}

export function DependencyMap({ data, patientId, obligationId }: { data: Snapshot; patientId: string; obligationId?: string }) {
  const items = data.clinical_obligations.filter((item) => item.patient_id === patientId);
  const edges = data.obligation_dependencies.filter((edge) =>
    !obligationId || edge.obligation_id === obligationId || edge.depends_on === obligationId);
  const connections = edges.flatMap((edge) => {
    const predecessor = items.find((item) => item.id === edge.depends_on);
    const successor = items.find((item) => item.id === edge.obligation_id);
    return predecessor && successor ? [{ edge, predecessor, successor }] : [];
  });
  function node(item: Obligation) {
    const rule = data.rule_versions.find((entry) => entry.id === item.rule_key);
    const source = data.clinical_evidence.find((entry) => entry.id === item.source_id)?.resource;
    return <Link className="dependency-node" to={'/passport?obligation=' + item.id + '#provenance'}>
      <span className="field-kicker">{label(rule?.pathway_id || '')}</span>
      <strong>{obligationTitle(data, item)}</strong>
      <small>{source ? source.code?.text || source.resourceType : 'Source unavailable'}</small>
      <Status value={item.status} />
    </Link>;
  }
  return <Panel title="Cross-pathway dependencies">
    {connections.length ? connections.map(({ edge, predecessor, successor }) => {
      const transition = data.life_stage_events.find((event) => event.patient_id === patientId && event.evidence_id === successor.source_id);
      return <div className="dependency-map" key={edge.id}>
        {transition && <div className="transition-note"><CalendarDays size={16} /> {label(transition.stage)} registered · {moment(transition.recorded)}<small>Pregnancy registration source</small></div>}
        <div className="dependency-grid">
          {node(predecessor)}
          <div className="dependency-edge"><ArrowRight size={21} /><strong>must close before</strong><small>{label(edge.kind)}</small></div>

          {node(successor)}
        </div>
        {edge.kind === 'requires_verified_closure' && <p className="dependency-context">
          The preconception obligation stays visible to the receiving team. This prerequisite applies to closing the linked review. Pregnancy care can proceed.
        </p>}
      </div>;
    }) : <Empty>No dependency recorded for this case yet.</Empty>}
  </Panel>;
}

export function Lifecycle({ data, item }: { data: Snapshot; item: Obligation }) {
  const tasks = data.care_coordination_tasks.filter((task) => task.obligation_id === item.id);
  const approvals = data.clinical_approvals.filter((review) => tasks.some((task) => task.id === review.task_id));
  const stages = [
    { title: 'Detected', active: true, detail: 'Rule and source recorded' },
    { title: 'Action prepared', active: tasks.length > 0, detail: tasks.length ? 'Proposal recorded' : 'Run coordination' },
    { title: 'Human review', active: approvals.length > 0, detail: approvals.length ? 'Decision recorded' : tasks.length ? 'Review pending' : 'Awaiting proposal' },
    { title: 'Evidence received', active: completionEvidence(data, item).length > 0, detail: completionEvidence(data, item).length ? 'Records submitted' : 'Evidence pending' },
    { title: 'Verified closure', active: item.status === 'closed', detail: item.status === 'closed' ? 'Obligation resolved' : 'Closure gate pending' },
    { title: 'Reopened', active: data.audit_events.some(event=>event.obligation_id===item.id&&event.action==='closure_reopened'), detail: data.audit_events.some(event=>event.obligation_id===item.id&&event.action==='closure_reopened') ? (item.status==='open'?'Correction recorded; returned to '+item.owner:'Reopening recorded in history') : 'If closing evidence is corrected' },
  ];
  return <ol className="lifecycle" aria-label="Obligation checkpoints">
    {stages.map((stage) => <li key={stage.title} className={stage.active ? 'done' : ''}>
      <span>{stage.active ? <Check size={15} /> : <CircleDot size={15} />}</span><strong>{stage.title}</strong><small>{stage.detail}</small>
    </li>)}
  </ol>;
}

const nodeLabels: Record<string, string> = {
  retrieve: 'Retrieve evidence', reconcile: 'Reconcile evidence', prepare: 'Prepare proposal', route: 'Route to human review',
};

const nodeDetail: Record<string, string> = {
  retrieve: 'Collects references from the patient evidence supplied by the API.',
  reconcile: 'Checks the available records for missing or conflicting evidence.',
  prepare: 'Builds a coordination proposal based on the evidence finding.',
  route: 'Returns the proposal for human review.',
};

export function WorkflowSteps({ nodes }: { nodes?: string[] }) {
  if (!nodes?.length) return <p className="muted">The workflow definition is unavailable.</p>;
  return <ol className="workflow-steps" aria-label="Configured LangGraph steps">
    {nodes.map((node) => <li key={node}><strong>{nodeLabels[node] || label(node)}</strong><small>{nodeDetail[node]}</small></li>)}
  </ol>;
}

export function workflowStatus(run: Snapshot['agent_executions'][number] | undefined, taskStatus?: string, running = false) {
  if (running) return 'running';
  if (!run) return 'not_started';
  if (run.result.finding === 'failed') return 'failed';
  if (taskStatus === 'request_evidence' ||
      (taskStatus === 'pending' && run.result.finding === 'conflicting_or_unqualified_evidence')) return 'escalated';
  if (taskStatus === 'pending') return 'waiting_for_review';
  if (taskStatus === 'approve' || taskStatus === 'reject') return 'completed';
  return taskStatus || 'recorded';
}

export function RunTrace({ trace }: { trace?: string[] }) {
  if (!trace?.length) return <p className="muted">This execution has no persisted node trace.</p>;
  return <ol className="run-trace" aria-label="Recorded LangGraph nodes">
    {trace.map((node, index) => <li key={node + index}><Check size={14} />{nodeLabels[node] || label(node)}</li>)}
  </ol>;
}

const innovations = [
  ['Life-Stage Transition Intelligence', '/workspace?patient=demo-amira', CalendarDays],
  ['Clinical Obligation Passport', '/passport', ClipboardList],
  ['Agentic Care-Resolution Orchestration', '/resolution', Workflow],
  ['Cross-Pathway Dependency Graph', '/workspace?patient=demo-amira#dependencies', GitBranch],
  ['Evidence-Verified Care Closure', '/audit', ShieldCheck],
  ['Mother–Child Continuity Intelligence', '', HeartPulse],
] as const;

export function Innovations() {
  return <details className="panel expandable"><summary>Innovation showcase</summary>
    <div className="innovation-grid">
      {innovations.map(([name, href, Icon]) => <div key={name}><Icon size={17} />
        {href ? <Link className="text-link" to={href}>{name}</Link> : <><strong>{name}</strong><Status value="planned" /></>}
      </div>)}
    </div>
    <p className="inset muted">The planned mother–child capability would link separate records through independently authorized relationships.</p>
  </details>;
}

export function Evaluation() {
  return <details className="panel expandable"><summary>Technical evaluation</summary>
    <div className="inset">
      {evaluation.run ? <>
        <h3>Automated verification</h3>
        <dl className="evaluation-grid">{evaluation.automated.map((item) =>
          <div key={item.label}><dt>{item.label}</dt><dd>{item.result}</dd></div>)}</dl>
        <h3>Synthetic rule scenarios</h3>
        <p>{evaluation.synthetic}</p>
        <small className="muted">Recorded run {evaluation.run}</small>
      </> : <p>Evaluation results are unavailable until the verification suite runs.</p>}
      <p className="muted">Clinical outcomes have not been established.</p>
    </div>
  </details>;
}

export function Interoperability() {
  return <div className="interop inset">
    <Database size={22} />
    <div><strong>Standalone FHIR R4 bundle</strong>
      <p>Export patient records, observations, obligation Tasks and Provenance. Imported Condition, Encounter, DiagnosticReport, ServiceRequest and CarePlan resources are included when present.</p>
      <p>Validated against the official R4 JSON schema and patient-local references. Full profiles and terminology remain unverified.</p>
      <p>Designed to work alongside existing EMRs through future site-specific adapters for mapping, identity and authorization. Live connectivity is planned.</p>
    </div>
  </div>;
}
