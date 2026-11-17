export type Role = 'coordinator' | 'reviewer' | 'viewer';
export type Resource = {
  resourceType: string; id: string; name?: { given: string[]; family: string }[];
  birthDate?: string; gender?: string; status?: string; valueString?: string;
  code?: { coding?: { code: string; system: string }[] };
};
export type Patient = { id: string; stage: string; resource: Resource };
export type Rule = { id: string; rule_id: string; version: string; pathway_id: string;
  definition: { description: string; closure: string; source: string } };
export type Obligation = { id: string; patient_id: string; rule_key: string; source_id: string;
  owner: string; status: 'open' | 'closed'; created: string };
export type Audit = { sequence: number; recorded: string; actor: string; action: string; patient_id: string;
  obligation_id: string | null; rule_key: string; evidence_refs: string[]; detail: { reason?: string; evaluated_rule?: string } };
export type Task = { id: string; obligation_id: string; execution_id: string; action: string; status: string };
export type Snapshot = {
  patients: Patient[];
  clinical_evidence: { id: string; patient_id: string; resource: Resource }[];
  life_stage_events: { id: string; patient_id: string; stage: string; recorded: string; evidence_id: string }[];
  rule_versions: Rule[];
  clinical_obligations: Obligation[];
  obligation_dependencies: { id: string; obligation_id: string; depends_on: string; rule_key: string }[];
  agent_executions: { id: string; obligation_id: string; actor: string; recorded: string;
    result: { evidence_refs: string[]; finding: string; route: string; action: string } }[];
  care_coordination_tasks: Task[];
  clinical_approvals: { id: string; task_id: string; decision: string; actor: string; note: string; evidence_refs: string[] }[];
  closure_evidence: { id: string; obligation_id: string; evidence_id: string; approval_id: string; recorded: string }[];
  audit_events: Audit[];
};
export const label = (value: string) => value.replace(/[-_]/g, ' ').replace(/^./, (letter) => letter.toUpperCase());
export const patientName = (patient: Patient) => {
  const name = patient.resource.name?.[0];
  return name ? [...name.given, name.family].join(' ') : patient.id;
};
export const moment = (iso: string) => new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(iso));
