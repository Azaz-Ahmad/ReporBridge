// Presentation only. Never use these functions for API payloads or grounding.
export const PRODUCT_NAME = 'Ajyra AI - ReproBridge';
export const displayText = (value: string) => value.replaceAll('CITATION_PENDING_CLINICAL_CONFIRMATION', 'pending clinical confirmation').replaceAll('glycemic-assessment-pregnancy', 'illustrative pregnancy timing policy').replaceAll('documented-finding-followup', 'documented finding follow-up');
export const displayJson = (value: unknown) => displayText(JSON.stringify(value, null, 2));
export function demoPatient(id: string) {
 return ({'demo-amira':'Amira Haddad','demo-lina':'Lina Omar','demo-sara':'Sara Ali','demo-tsp-uncertain':'Uncertain dating patient','demo-handoff':'Simulated handoff patient'} as Record<string,string>)[id] || 'Synthetic patient';
}
