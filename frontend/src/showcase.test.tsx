// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it } from 'vitest';
import { DependencyMap, Journey, populationCounts, RunTrace, WorkflowSteps, workflowStatus } from './showcase';
import type { Obligation, Snapshot } from './types';

afterEach(cleanup);

const initial: Obligation = { id: 'prior', patient_id: 'demo-amira', rule_key: 'pre@1', source_id: 'flag',
  owner: 'Demo coordinator', status: 'open', created: '2026-11-17T12:00:00Z' };
const later: Obligation = { ...initial, id: 'later', rule_key: 'preg@1', source_id: 'pregnancy' };
const data: Snapshot = {
  patients: [{ id: 'demo-amira', stage: 'pregnancy', resource: { resourceType: 'Patient', id: 'demo-amira' } }],
  clinical_evidence: [{ id: 'flag', patient_id: 'demo-amira', resource: { resourceType: 'Observation', id: 'flag' } }],
  life_stage_events: [{ id: 'event', patient_id: 'demo-amira', stage: 'pregnancy', recorded: initial.created, evidence_id: 'pregnancy' }],
  rule_versions: [], clinical_obligations: [initial, later],
  obligation_dependencies: [{ id: 'edge', obligation_id: 'later', depends_on: 'prior', rule_key: 'preg@1', kind: 'requires_verified_closure' }],
  agent_executions: [], clinical_approvals: [], closure_evidence: [], demo_run_archive: [],
  care_coordination_tasks: [{ id: 'review', obligation_id: 'prior', execution_id: 'run', action: 'Review', status: 'pending' }],
  audit_events: [1, 2].map((sequence) => ({ sequence, recorded: initial.created, actor: 'coordinator',
    action: 'closure_blocked', patient_id: 'demo-amira', obligation_id: 'prior', rule_key: 'pre@1', evidence_refs: [], detail: {} })),
};

describe('persisted demo readouts', () => {
  it('counts distinct blocked obligations and removes a verified closure from the blocked count', () => {
    expect(populationCounts(data)).toEqual({ patients: 1, open: 2, pending: 1, transitions: 1, verified: 0, blocked: 1 });
    const closed = { ...initial, status: 'closed' as const };
    expect(populationCounts({ ...data, clinical_obligations: [closed, later] })).toMatchObject({ verified: 1, blocked: 0, open: 1 });
  });

  it('marks pregnancy current and postpartum planned', () => {
    render(<Journey stage="pregnancy" />);
    expect(screen.getByText('Pregnancy').closest('li')?.getAttribute('aria-current')).toBe('step');
    expect(screen.getByText('Planned').closest('li')?.textContent).toContain('Postpartum');
  });

  it('links both stored dependency records to their provenance', () => {
    render(<MemoryRouter><DependencyMap data={data} patientId="demo-amira" /></MemoryRouter>);
    const links = screen.getAllByRole('link');
    expect(links.map((link) => link.getAttribute('href'))).toEqual([
      '/passport?obligation=prior#provenance', '/passport?obligation=later#provenance',
    ]);
    expect(screen.getByText('Observation')).toBeTruthy();
    expect(screen.getByText('must close before')).toBeTruthy();
  });

  it('displays the recorded nodes and explicitly handles older traces', () => {
    const view = render(<RunTrace trace={['retrieve', 'prepare']} />);
    expect(screen.getAllByRole('listitem').map((item) => item.textContent)).toEqual(['Retrieve evidence', 'Prepare proposal']);
    view.rerender(<RunTrace />);
    expect(screen.queryByRole('listitem')).toBeNull();
    expect(screen.getByText('This execution has no persisted node trace.')).toBeTruthy();
  });
});

it('shows the configured workflow without creating execution history', () => {
  render(<WorkflowSteps nodes={['retrieve', 'reconcile', 'prepare', 'route']} />);
  expect(screen.getAllByRole('listitem')).toHaveLength(4);
  expect(screen.getByText('Route to human review')).toBeTruthy();
  expect(screen.queryByRole('list', { name: 'Recorded LangGraph nodes' })).toBeNull();
});

it('distinguishes request progress, review decisions, escalation and graph failures', () => {
  const run: Snapshot['agent_executions'][number] = {
    id: 'run', obligation_id: 'prior', actor: 'coordinator', recorded: initial.created,
    result: { evidence_refs: ['Observation/flag'], finding: 'missing_closure_evidence', route: 'human_review', action: 'Review' },
  };
  expect(workflowStatus(undefined)).toBe('not_started');
  expect(workflowStatus(undefined, undefined, true)).toBe('running');
  expect(workflowStatus(run, 'pending')).toBe('waiting_for_review');
  expect(workflowStatus(run, 'approve')).toBe('completed');
  expect(workflowStatus(run, 'request_evidence')).toBe('escalated');
  expect(workflowStatus({ ...run, result: { ...run.result, finding: 'failed' } })).toBe('failed');
});
