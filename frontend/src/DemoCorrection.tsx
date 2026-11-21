import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from './api';
import { Button, Feedback } from './ui';
import type { Obligation, Role } from './types';

export function DemoCorrection({token, role, obligation, evidenceId, evidenceLabel}: {
  token: string; role: Role; obligation: Obligation; evidenceId?: string; evidenceLabel?: string;
}) {
  const [confirmed, setConfirmed] = useState(false);
  const cache = useQueryClient();
  const session = useQuery({queryKey:['jury-session',token],queryFn:()=>api<{demo_mode:boolean}>(token,'/session')});
  const mutation = useMutation({mutationFn:()=>api<{obligation_status:string;owner:string}>(token,
    '/v1/tsp/demo/obligations/'+obligation.id+'/correct-closing-evidence','POST',
    {evidence_id:evidenceId,confirmation:'invalidate closing synthetic evidence'}),
    onSuccess:()=>{setConfirmed(false);for(const key of ['snapshot','tsp','prevention','clinical-explorer','history','handoff'])cache.invalidateQueries({queryKey:[key]});}});
  useEffect(()=>{setConfirmed(false);mutation.reset();},[token,obligation.id,evidenceId]);
  if(!session.data?.demo_mode||role!=='coordinator')return null;
  return <div className="inset demo-correction" aria-label="Demo evidence correction">
    <strong>SIMULATED evidence correction · synthetic data only</strong>
    <p>Invalidate the recorded closing observation through the existing correction path. This can reopen the obligation and its dependants; the assigned owner is retained.</p>
    <Button variant="outline" disabled={mutation.isPending||obligation.status!=='closed'||!evidenceId} onClick={()=>setConfirmed(true)}>Simulate evidence correction (demo)</Button>
    {obligation.status!=='closed'&&<p>Available after verified closure with recorded synthetic evidence.</p>}
    {confirmed&&<div role="group" aria-label="Confirm simulated evidence correction"><p>Correct closing evidence: {evidenceLabel||'Recorded synthetic closing observation'}. Reconciliation and a fresh clinical review will be required. Continue?</p>
      <Button variant="danger" disabled={mutation.isPending} onClick={()=>mutation.mutate()}>Confirm simulated correction</Button>
      <Button variant="outline" disabled={mutation.isPending} onClick={()=>setConfirmed(false)}>Cancel simulated correction</Button></div>}
    {mutation.isPending&&<p aria-live="polite">Waiting for correction confirmation…</p>}
    {mutation.error&&<Feedback message={mutation.error.message} error/>}
    {mutation.data&&<Feedback message={'Simulated correction recorded. Obligation '+mutation.data.obligation_status+'; returned to assigned owner: '+mutation.data.owner+'.'}/>}
  </div>;
}
