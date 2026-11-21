import { useQuery } from '@tanstack/react-query';
import { api } from './api';
import type { WindowResult } from './Tsp';
import { Feedback } from './ui';

export type CoordinationResult = WindowResult & { coordination: {
  action: string | null; owner_role: string | null; policy_id: string; policy_version: string;
  scope: string; policy_matched: boolean;
} };

export function ActionText({ result }: { result: CoordinationResult }) {
  return <>{result.coordination.action ? <>{result.coordination.action} ({result.coordination.owner_role})</> : 'None — no coordination action specified for this state.'}</>;
}

export function CoordinationNextAction({ token, patientId }: { token: string; patientId: string }) {
  const query = useQuery({ queryKey: ['tsp', 'coordination', patientId, token],
    queryFn: () => api<CoordinationResult>(token, '/v1/tsp/patients/' + patientId + '/coordination') });
  if (query.error) return <Feedback message={query.error.message} error />;
  if (!query.data) return <span role="status">Loading coordination action…</span>;
  return <div><ActionText result={query.data} /><p className="muted">Coordination only. No automatic action or owner change. Based on {query.data.status.replaceAll('_', ' ')} as of {query.data.as_of}.</p></div>;
}
