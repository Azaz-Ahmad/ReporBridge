import { useState, type FormEvent } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { api } from './api';
import { Button, Empty, Feedback, Status } from './ui';
import { label } from './types';

type Evidence = {
  id: string;
  patient_id: string;
  kind: string;
  resource_id: string;
  source: string;
  version: number;
  status: string;
  digest: string;
  clinical_time: string | null;
  received: string;
  supersedes: string | null;
  citation: string;
  method: 'structured' | 'document';
  section: string | null;
  position: number | null;
  content: string | null;
  quality: { state: string; warnings: string[] };
  provenance: { source_system: string; authorization_role: string; resource_reference: string; evidence_id: string };
  normalized: { document?: { type: string; content_ref: string | null; available: boolean } };
};
type Page = { items: Evidence[]; next_offset: number | null; outcome: string };
const kinds = ['Patient', 'Observation', 'Condition', 'Encounter', 'DiagnosticReport', 'DocumentReference',
  'MedicationRequest', 'MedicationStatement', 'ServiceRequest', 'CarePlan'];

export function ClinicalExplorer({ patientId, token, coordinator }: { patientId: string; token: string; coordinator: boolean }) {
  const [expanded, setExpanded] = useState(false);
  const [draft, setDraft] = useState('');
  const [term, setTerm] = useState('');
  const [kind, setKind] = useState('');
  const [history, setHistory] = useState(false);
  const [offset, setOffset] = useState(0);
  const limit = 6;
  const base = '/v1/clinical/patients/' + encodeURIComponent(patientId);
  const results = useQuery({
    enabled: expanded,
    queryKey: ['clinical-explorer', patientId, token, term, kind, history, offset],
    queryFn: () => {
      const filters = { history, limit, offset, ...(kind ? { kind } : {}) };
      if (term) return api<Page>(token, '/v1/clinical/retrieval/search', 'POST',
        { ...filters, patient_id: patientId, query: term, mode: 'hybrid' });
      const params = new URLSearchParams(Object.entries(filters).map(([key, value]) => [key, String(value)]));
      return api<Page>(token, base + '/evidence?' + params.toString());
    },
  });
  const seed = useMutation({
    mutationFn: () => api(token, '/v1/clinical/demo/dataset', 'POST'),
    onSuccess: () => results.refetch(),
  });

  function search(event: FormEvent) {
    event.preventDefault();
    setOffset(0);
    setTerm(draft.trim());
  }

  return <details className="panel expandable clinical-explorer" onToggle={(event) => setExpanded(event.currentTarget.open)}>
    <summary>Clinical evidence explorer</summary>
    <div className="inset">
      <form className="clinical-search" onSubmit={search}>
        <label>Search evidence <input value={draft} onChange={(event) => setDraft(event.target.value)} maxLength={160} /></label>
        <Button type="submit">Search</Button>
        <label>Resource type <select value={kind} onChange={(event) => { setOffset(0); setKind(event.target.value); }}>
          <option value="">All supported types</option>
          {kinds.map((name) => <option key={name}>{name}</option>)}
        </select></label>
        <label className="clinical-history"><input type="checkbox" checked={history}
          onChange={(event) => { setOffset(0); setHistory(event.target.checked); }} /> Include superseded versions</label>
      </form>
      {coordinator && patientId === 'demo-amira' && <div className="actions">
        <Button variant="outline" type="button" disabled={seed.isPending} onClick={() => seed.mutate()}>Load Amira’s synthetic dataset</Button>
        {seed.isSuccess && <small role="status">Synthetic dataset available.</small>}
      </div>}
      {seed.error && <Feedback message={seed.error.message} error />}
      {results.isLoading && <p role="status">Loading patient-scoped evidence…</p>}
      {results.error && <Feedback message={results.error.message} error />}
      {results.data?.outcome === 'not_found' && <Empty>No matching evidence in the available records.</Empty>}
      <ul className="clinical-results">
        {results.data?.items.map((item) => <li key={item.id + '/' + (item.position ?? 'record')}>
          <details>
            <summary><strong>{item.provenance.resource_reference}</strong>
              <small>{item.source} · Version {item.version}{item.section ? ' · ' + item.section : ''}</small>
              <Status value={item.quality.state} />
            </summary>
            <div className="inset">
              <p>{item.citation} · Source status {label(item.status)}</p>
              <p>Clinical time {item.clinical_time ?? 'Unavailable'} · Received {item.received}</p>
              {item.quality.warnings.length > 0 && <p>Quality flags {item.quality.warnings.map(label).join(', ')}</p>}
              {item.supersedes && <p>Supersedes evidence <code>{item.supersedes}</code></p>}
              {item.normalized.document?.content_ref && <p>Content reference <code>{item.normalized.document.content_ref}</code></p>}
              <p>Recorded by {label(item.provenance.authorization_role)} · Integrity hash <code>{item.digest}</code></p>
              {item.content && <><p><strong>Source excerpt · untrusted clinical text</strong></p><blockquote>{item.content}</blockquote></>}
            </div>
          </details>
        </li>)}
      </ul>
      {(offset > 0 || results.data?.next_offset != null) && <div className="actions">
        <Button variant="outline" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))}>Previous</Button>
        <Button variant="outline" disabled={results.data?.next_offset == null} onClick={() =>
          setOffset(results.data?.next_offset ?? offset)}>Next</Button>
      </div>}
    </div>
  </details>;
}
