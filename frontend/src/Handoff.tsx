import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api } from './api';
import { Button, Feedback, Panel, Status } from './ui';
import type { Role } from './types';

export const HANDOFF_PATIENT = 'demo-handoff';
export type Facility = { simulation: boolean; origin: string; receiving?: string | null;
  received_at?: string | null; transport?: string };
export type HandoffState = { simulation: boolean; patient_id: string; stage: string; obligation_id: string;
  obligation_status: string; responsible_team: string; original_owner: string; origin: string; receiving: string;
  received: boolean; received_at: string | null;
  owner_history: { recorded: string; previous_owner: string; owner: string; simulation: boolean }[] };
const base = '/v1/simulated-handoff';
const receivedDate = (value: string) => new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Dubai', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date(value));

export function FacilityChips({ facility }: { facility?: Facility }) {
  if (!facility?.simulation) return null;
  return <div className="facility-provenance"><div className="facility-chips"><span className="facility-chip">SIMULATED · {facility.origin}</span>
    {facility.receiving && <span className="facility-chip">SIMULATED · {facility.receiving}</span>}</div>
    {facility.received_at ? <p>Origin: {facility.origin}, received {receivedDate(facility.received_at)} · Asia/Dubai<br />received via simulated exchange</p>
      : <p>SIMULATED origin: {facility.origin}</p>}</div>;
}

function useHandoff(token: string, patientId: string) {
  return useQuery({ queryKey: ['handoff', patientId, token], enabled: patientId === HANDOFF_PATIENT,
    queryFn: () => api<HandoffState>(token, base + '/patients/' + patientId) });
}

function useRefresh() {
  const cache = useQueryClient();
  return () => { for (const key of ['handoff', 'snapshot', 'prevention', 'clinical-explorer']) cache.invalidateQueries({ queryKey: [key] }); };
}

export function HandoffSetup({ token, role, available }: { token: string; role: Role; available: boolean }) {
  const refresh = useRefresh();
  const seed = useMutation({ mutationFn: () => api<HandoffState>(token, base + '/demo/seed', 'POST'), onSuccess: refresh });
  return <Panel title="SIMULATED facility exchange"><p>Follow one synthetic obligation from Hospital A to Hospital B. This is a local simulation with no external connection.</p>
    <p className="muted">Facilities are provenance labels. Existing patient-scoped authorization remains in force.</p>
    {role === 'coordinator' && <Button disabled={seed.isPending} onClick={() => seed.mutate()}>Load simulated handoff demo</Button>}
    {(available || seed.data) && <Link className="text-link" to={'/workspace?patient=' + HANDOFF_PATIENT}>Open simulated handoff workspace</Link>}
    {seed.error && <Feedback message={seed.error.message} error />}</Panel>;
}

export function HandoffPanel({ token, role, patientId }: { token: string; role: Role; patientId: string }) {
  const query = useHandoff(token, patientId);
  const refresh = useRefresh();
  const change = useMutation({ mutationFn: (action: string) => api<HandoffState>(token, base + '/patients/' + patientId + '/' + action, 'POST'), onSuccess: refresh });
  if (patientId !== HANDOFF_PATIENT) return null;
  const state = query.data;
  return <Panel title="SIMULATED Hospital B receiving view">
    <p>Local simulation only · no external connection. Hospital labels do not grant patient access.</p>
    {query.error && <Feedback message={query.error.message} error />}
    {state && <><FacilityChips facility={{ simulation: true, origin: state.origin, receiving: state.receiving, received_at: state.received_at }} />
      <dl className="details"><div><dt>Responsible team</dt><dd>{state.responsible_team}</dd></div>
        <div><dt>Original owner retained in history</dt><dd>{state.original_owner}</dd></div>
        <div><dt>Carried obligation</dt><dd><Status value={state.obligation_status} /></dd></div></dl>
      <Link className="text-link" to={'/passport?obligation=' + state.obligation_id}>Open carried obligation</Link>
      {!state.received && <p>Register pregnancy at the simulated receiving facility before receiving Hospital A's records. The original unresolved obligation remains open.</p>}
      {role === 'coordinator' && <div className="actions">
        <Button disabled={change.isPending || state.stage !== 'pregnancy'} onClick={() => change.mutate('receive')}>Receive records from Hospital A</Button>
        {state.received && <Button variant="outline" disabled={change.isPending} onClick={() => change.mutate('origin/invalidate')}>Receive simulated origin invalidation</Button>}
      </div>}
      {state.received && <p>SIMULATED receipt recorded. Receiving records does not approve or close the obligation. Original sources and owner history are retained.</p>}
      <details><summary>SIMULATED owner history</summary><ul className="handoff-history">{state.owner_history.map((entry, index) => <li key={entry.recorded + index}>
        {entry.previous_owner} → {entry.owner}<small>{receivedDate(entry.recorded)} · SIMULATED</small></li>)}</ul></details>
    </>}{change.error && <Feedback message={change.error.message} error />}</Panel>;
}

export function HandoffTimeline({ token, patientId }: { token: string; patientId: string }) {
  const query = useHandoff(token, patientId);
  if (patientId !== HANDOFF_PATIENT || !query.data) return null;
  const state = query.data;
  return <Panel title="SIMULATED facility timeline"><ol className="handoff-history">
    <li><strong>Preconception obligation originated</strong><FacilityChips facility={{ simulation: true, origin: state.origin }} /></li>
    {state.stage === 'pregnancy' && <li><strong>Pregnancy registered at the receiving facility</strong><span className="facility-chip">SIMULATED · {state.receiving}</span></li>}
    {state.received && <li><strong>Unresolved obligation surfaced in the receiving view</strong><FacilityChips facility={{ simulation: true, origin: state.origin, receiving: state.receiving, received_at: state.received_at }} /></li>}
  </ol></Panel>;
}
