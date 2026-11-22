import { Link, useLocation, useSearchParams } from 'react-router-dom';
import { ArrowRight, CalendarDays, ClipboardList, Database, HeartPulse } from 'lucide-react';
import { ClinicalExplorer } from './ClinicalExplorer';
import { HandoffPanel, HandoffTimeline } from './Handoff';
import { HistoricalCandidates, HistoricalDetectionTimeline } from './HistoricalCandidates';
import { EarlierRecords } from './History';
import { JourneyStrip } from './Jury';
import { DecisionTimeline } from './Prevention';
import { SourceDocumentsLink } from './SourceDocuments';
import { TspWindow } from './Tsp';
import { closureMessage, DependencyMap, Journey, obligationTitle } from './showcase';
import { label, moment, patientName, type Obligation } from './types';
import { Button, Empty, Panel, Status } from './ui';
import type { ScreenProps } from './screens';

export function Workspace({ data, role, token, busy, action }: ScreenProps) {
  const [params, setParams] = useSearchParams();
  const { hash } = useLocation();
  const patientId = params.get('patient');
  const patient = patientId ? data.patients.find(item => item.id === patientId) : data.patients[0];
  const obligations = data.clinical_obligations.filter(item => item.patient_id === patient?.id);
  const assessment = obligations.find(item => data.rule_versions.some(rule => rule.id === item.rule_key && rule.pathway_id === 'preconception'));
  const scenario = assessment && data.case_context?.[assessment.id];
  const connections = data.obligation_dependencies.flatMap(edge => {
    const earlier = obligations.find(item => item.id === edge.depends_on);
    const later = obligations.find(item => item.id === edge.obligation_id);
    return earlier && later ? [{ edge, earlier, later }] : [];
  });
  const linked = new Set(connections.flatMap(({ earlier, later }) => [earlier.id, later.id]));
  const events = data.life_stage_events.filter(event => event.patient_id === patient?.id).sort((a, b) => a.recorded.localeCompare(b.recorded));
  const patientEvidence = data.clinical_evidence.filter(row => row.patient_id === patient?.id);
  const currentCare = patient && <div className="workspace-current-evidence"><h3>Selected patient’s clinical evidence</h3><p className="workspace-section-note">Currently loaded records. More Details contains the full evidence explorer.</p><p>Current pathway: {label(patient.stage)}</p>
    <div className="workspace-evidence-summary">{patientEvidence.slice(0, 3).map(({ id, resource }) => <article key={id}>
      <strong>{resource.code?.text || resource.resourceType}</strong><span>{resource.valueString || resource.resourceType}</span><Status value={resource.status || 'unknown'} />
    </article>)}</div>
    {!patientEvidence.length && <Empty>No clinical evidence available in this summary. Open the evidence explorer in More Details.</Empty>}
    {patientEvidence.length > 3 && <p className="muted">Showing 3 of {patientEvidence.length} records. The full clinical evidence table is in More Details.</p>}
    {events.filter(event => event.stage === 'pregnancy').map(event => {
      const source = patientEvidence.find(row => row.id === event.evidence_id)?.resource;
      const recorded = source as (typeof source & { effectiveDateTime?: string; serviceProvider?: { display?: string }; performer?: { display?: string }[] });
      const facility = recorded?.serviceProvider?.display || recorded?.performer?.[0]?.display;
      return <div className="workspace-registration" key={event.id}><strong>Pregnancy registration</strong>
        <p>{recorded?.effectiveDateTime ? 'Source date: ' + recorded.effectiveDateTime.slice(0, 10) : 'Registration event: ' + moment(event.recorded) + ' · system time'}</p>
        {facility && <span className="facility-chip">{facility}</span>}
        {!source && <p>Source observation is unavailable in this snapshot.</p>}
        <details><summary>Registration source reference</summary>{event.evidence_id || 'Not recorded'}</details>
      </div>;
    })}
    {!events.some(event => event.stage === 'pregnancy') && <p>No pregnancy registration recorded.</p>}
  </div>;

  function obligationCard(item: Obligation) {
    const rule = data.rule_versions.find(entry => entry.id === item.rule_key);
    return <article className="workspace-obligation" key={item.id}>
      <span className="field-kicker">{label(rule?.pathway_id || '')}</span>
      <Link className="text-link" to={'/passport?obligation=' + item.id}><strong>{obligationTitle(data, item)}</strong></Link>
      <p>{data.case_context?.[item.id]?.rationale || rule?.definition.description || 'No clinical rationale recorded.'}</p>
      <div className="workspace-obligation-actions"><Status value={item.status} />
        <Button asChild variant="outline"><Link to={'/passport?obligation=' + item.id}>Open obligation passport <ArrowRight size={15} /></Link></Button>
      </div>
    </article>;
  }

  return <div className="women-workspace">
    <div className="page-heading workspace-heading"><div><h1>Women’s Health Workspace</h1><p>Patient record, life-stage timeline, obligations, and source findings.</p></div>
      {patient && <label className="field-inline">Patient <select value={patient.id} onChange={event => setParams({ patient: event.target.value })}>
        {data.patients.map(item => <option value={item.id} key={item.id}>{patientName(item)}</option>)}
      </select></label>}
    </div>
    {!patient ? <Empty>{patientId ? 'This patient is unavailable. ' : 'Load a synthetic patient. '}<Link className="text-link" to="/">Open population dashboard</Link></Empty> : <>
      <section className="panel workspace-summary" aria-label="Patient summary">
        <div className="workspace-person"><span className="workspace-icon"><HeartPulse size={27} /></span><div><h2>{patientName(patient)}</h2><p>Birth date: {patient.resource.birthDate || 'Not recorded'}</p></div></div>
        <JourneyStrip token={token} patientId={patient.id} compact stage={patient.stage} actions={role === 'coordinator' && <div className="actions workspace-summary-actions">
          <Button variant="outline" disabled={busy} onClick={() => action('/patients/' + patient.id + '/evaluate', 'Applicable rules evaluated.')}>Evaluate rules</Button>
          {patient.stage === 'preconception' && <Button disabled={busy} onClick={() => action('/patients/' + patient.id + '/pregnancy', 'Pregnancy registered. Existing obligations were retained.')}><CalendarDays size={17} />Register pregnancy</Button>}
        </div>} />
      </section>

      <div className="workspace-journey-windows">
        <Panel title="Journey"><p className="workspace-section-note">Life stage and care continuity</p><Journey stage={patient.stage} /></Panel>
        <div className="workspace-window"><TspWindow token={token} patientId={patient.id} timeline compact /></div>
      </div>

      <section className="panel workspace-obligations" aria-label="Clinical obligations">
        <div className="panel-heading"><h2><ClipboardList size={21} />Obligations</h2><span>Recorded care obligations and dependencies</span></div>
        {connections.map(({ edge, earlier, later }) => <div className="workspace-dependency" key={edge.id}>
          {obligationCard(earlier)}<div className="workspace-dependency-arrow"><ArrowRight size={28} /><strong>{edge.kind === 'requires_verified_closure' ? 'Depends on completion' : 'Recorded dependency'}</strong><small>{label(edge.kind)}</small></div>{obligationCard(later)}
        </div>)}
        <div className="workspace-obligation-list">{obligations.filter(item => !linked.has(item.id)).map(obligationCard)}</div>
        {!obligations.length && <Empty>No obligations recorded.</Empty>}
      </section>

      <section className="panel workspace-evidence" aria-label="Evidence explorer">
        <div className="panel-heading"><h2><Database size={21} />Evidence explorer</h2><SourceDocumentsLink patientId={patient.id} /></div>
        <p className="workspace-section-note">Earlier records and current care evidence. Source inclusion does not establish completion.</p>
        <div className="workspace-evidence-grid">
          <EarlierRecords token={token} role={role} patientId={patient.id} compact currentCare={currentCare} />
          {patient.id !== 'demo-amira' && currentCare}
        </div>
        <HandoffPanel token={token} role={role} patientId={patient.id} />
      </section>

      <div className="workspace-candidates"><HistoricalCandidates token={token} role={role} patientId={patient.id} compact /></div>

      <details className="panel workspace-more" open={hash === '#dependencies' || undefined}><summary>More Details</summary>
        <HistoricalDetectionTimeline token={token} patientId={patient.id} />
        <section className="workspace-detail-section" aria-label="Life-stage timeline and clinical context">
          {assessment && scenario && <div className="clinical-context"><p className="field-kicker">Documented clinical context</p><strong>{scenario.finding}</strong>
            <p>{assessment.status === 'closed' ? closureMessage(data, assessment) : patient.stage === 'pregnancy' && data.obligation_dependencies.some(edge => edge.depends_on === assessment.id)
              ? 'Pregnancy is registered and this assessment is still open. The linked handoff review keeps it visible to the receiving care team.' : scenario.rationale}</p>
            <Link className="text-link" to={'/passport?obligation=' + assessment.id}>Open assessment passport <ArrowRight size={15} /></Link>
          </div>}
          <dl className="details"><div><dt>Birth date</dt><dd>{patient.resource.birthDate}</dd></div><div><dt>Current pathway</dt><dd>{label(patient.stage)}</dd></div><div><dt>Administrative gender</dt><dd>{label(patient.resource.gender || 'unknown')}</dd></div></dl>
          <Panel title="Life-stage timeline"><ul className="timeline">{events.map(event => <li key={event.id}><strong>{label(event.stage)}</strong><small>{moment(event.recorded)} · {event.evidence_id ? 'Source observation recorded' : 'Patient registration'}</small></li>)}</ul></Panel>
        </section>
        <DecisionTimeline token={token} patientId={patient.id} />
        <div id="dependencies"><DependencyMap data={data} patientId={patient.id} /></div>
        <HandoffTimeline token={token} patientId={patient.id} />
        <ClinicalExplorer key={patient.id} patientId={patient.id} token={token} coordinator={role === 'coordinator'} />
        <Panel title="Clinical evidence"><div className="table-wrap clinical-table"><table role="table"><thead><tr><th>Resource</th><th>Finding</th><th>Value</th><th>Status</th></tr></thead>
          <tbody role="rowgroup">{data.clinical_evidence.filter(row => row.patient_id === patient.id).map(({ resource }) => <tr role="row" key={resource.id}>
            <td role="cell"><span className="mobile-cell-label" aria-hidden="true">Resource</span>{resource.resourceType}</td>
            <td role="cell"><span className="mobile-cell-label" aria-hidden="true">Finding</span>{resource.code?.text || label(resource.code?.coding?.[0]?.code || '—')}</td>
            <td role="cell"><span className="mobile-cell-label" aria-hidden="true">Value</span>{resource.valueString || '—'}</td>
            <td role="cell"><span className="mobile-cell-label" aria-hidden="true">Status</span>{label(resource.status || '—')}</td>
          </tr>)}</tbody></table></div></Panel>
      </details>
    </>}
  </div>;
}
