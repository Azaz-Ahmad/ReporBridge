import { displayText, displayJson } from './presentation';
export type ExplanationProjection={accepted:boolean;agent_abstained:boolean;label:string;text:string|null;fallback:{label:string;text:string}|null;field_mismatches?:string[]};
export function ExplanationOutput({detail}:{detail:{explanation?:ExplanationProjection;error?:string|null;trace?:string[]}}){
 const explanation=detail.explanation;if(!explanation)return null;
 return <div className="explanation-output"><strong>{explanation.label}</strong>
 {explanation.accepted?<p>{displayText(explanation.text || '')}</p>:<><p>Agent abstained. Its result has not been accepted.</p>{explanation.fallback&&<p>{displayText(explanation.fallback.text)}</p>}</>}
 <details><summary>Explanation trace</summary><pre>{displayJson({agent_abstained:explanation.agent_abstained,error:detail.error||null,field_mismatches:explanation.field_mismatches||[],steps:detail.trace||[]})}</pre></details></div>;
}
