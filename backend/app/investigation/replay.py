"""Explicit real-response transport replay. Tools and all clinical guards still execute."""
import json
import os
import re
import copy
import itertools
from dataclasses import asdict
from pathlib import Path
from sqlalchemy import select
from app import db
from app.clinical.access import authorize
from app.clinical.normalize import digest
from app.clinical.tools import ClinicalTools
from app.investigation.provider import Draft, ProviderFailure, Turn

ROOT=Path(__file__).resolve().parents[2]
DEFAULT_DIR=ROOT/"demo-replays"/"hardening-v1"


def directory():return Path(os.getenv("LLM_REPLAY_DIR") or DEFAULT_DIR)


def available():
    from app.prevention.tsp import demo_enabled
    if not demo_enabled() or not directory().is_dir():return False
    for file in directory().glob("*.json"):
        try:
            value=json.loads(file.read_text(encoding="utf-8"))
            if value.get("origin")=="live-openai-responses" and value.get("replayable") and value.get("frames") and value.get("requested_model")==os.getenv("OPENAI_MODEL","").strip():return True
        except (OSError,ValueError):pass
    return False


def scrub(value):
    """Never serialize clients, headers, credentials or opaque reasoning payloads."""
    secrets=[v for k,v in os.environ.items() if v and len(v)>=8 and ("API_KEY" in k or k.endswith("_TOKEN"))]
    def clean(v):
        if isinstance(v,dict):return {k:clean(x) for k,x in v.items() if k.lower() not in {"authorization","headers","api_key","access_token","encrypted_content"}}
        if isinstance(v,list):return [clean(x) for x in v]
        if isinstance(v,str):
            for secret in secrets:v=v.replace(secret,"[REDACTED]")
            return re.sub(r"(?:Bearer\s+\S+|sk-[A-Za-z0-9_-]{8,})","[REDACTED]",v,flags=re.I)
        return v
    return clean(value)


class Binding:
    def __init__(self,run,context):
        from app.investigation import tooling
        from app.investigation.graph import SYSTEM
        from app.prevention.window_grounding import prompt
        self.aliases={}
        window=run["detail"].get("window_context")
        if not window or context.patient_id not in {"demo-amira","demo-tsp-uncertain"}:
            raise ProviderFailure("replay_scenario_not_supported")
        self.scenario=("history-" if window.get("history") else "tsp-")+context.patient_id
        self.system=SYSTEM+prompt(window)
        if window.get("history"):
            from app.history_guard import prompt as history_prompt
            self.system+=history_prompt(window)
        with db.engine.begin() as connection:
            scope=authorize(connection,context.role,context.patient_id);tooling.synthetic_scope(connection,scope)
            retrieval=ClinicalTools(connection,scope).retrieval
            rows=retrieval.provider.catalog(scope)
            from app.rules import DEMO_TAG
            if any(DEMO_TAG not in row["resource"].get("meta",{}).get("tag",[]) for row in rows):raise ProviderFailure("replay_synthetic_scope_required")
            obligations=[dict(r) for r in connection.execute(select(db.obligations).where(db.obligations.c.patient_id==context.patient_id)).mappings()]
            for row in rows:
                self.aliases[row["id"]]="@evidence:"+digest([row["patient_id"],row["source"],row["kind"],row["resource_id"],row["version"],row["digest"]])
            for row in rows:
                if re.fullmatch(r"[a-f0-9]{32}",row["scope"]):self.aliases[row["scope"]]="@scope:"+digest([row["patient_id"],row["source"]])
            for row in obligations:self.aliases[row["id"]]="@obligation:"+digest([row["patient_id"],row["rule_key"]])
            evidence=[retrieval.get(evidence_id=row["id"]).evidence.model_dump(mode="json") for row in rows]
        self.reverse={v:k for k,v in self.aliases.items()}
        if len(self.reverse)!=len(self.aliases):raise ProviderFailure("replay_ambiguous_identity")
        # Hash guard/prompt source as well as clinical context; never reuse a recording after a rule change.
        code=[(ROOT/"app"/name).read_text(encoding="utf-8") for name in ["investigation/graph.py","history_guard.py","history_policy_v1.json","prevention/window_grounding.py"]]
        context_value={"window":{k:v for k,v in window.items() if k not in {"session_id","hash","history_hash"}},
                       "evidence":evidence,"obligations":[{k:r[k] for k in ["id","rule_key","status","owner"]} for r in obligations]}
        self.descriptor={"scenario":self.scenario,"context":self.canonical(context_value),"guard_sources":code}
        self.manifest=digest(self.descriptor)
        self.question=run["detail"]["question"]

    def match_manifest(self,expected):
        if self.manifest==expected:return True
        # The server's inputs_used ordering can follow random evidence IDs. Match only
        # permutations of the exact same complete inputs; never remove or alter an input.
        paths=[]
        def visit(v,path=()):
            if isinstance(v,dict):
                for k,x in v.items():
                    if k=="inputs_used" and isinstance(x,list) and 1<len(x)<=3:paths.append(path+(k,))
                    else:visit(x,path+(k,))
            elif isinstance(v,list):
                for i,x in enumerate(v):visit(x,path+(i,))
        visit(self.descriptor)
        if not paths or len(paths)>3:return False
        variants=[copy.deepcopy(self.descriptor)]
        for path in paths:
            expanded=[]
            for variant in variants:
                node=variant
                for key in path[:-1]:node=node[key]
                for permutation in itertools.permutations(node[path[-1]]):
                    candidate=copy.deepcopy(variant);target=candidate
                    for key in path[:-1]:target=target[key]
                    target[path[-1]]=list(permutation);expanded.append(candidate)
            variants=expanded
        if any(digest(v)==expected for v in variants):
            self.manifest=expected
            return True
        return False

    def replace(self,text,mapping):
        for old,new in sorted(mapping.items(),key=lambda x:-len(x[0])):text=text.replace(old,new)
        return text

    def canonical(self,v):
        if isinstance(v,dict):
            # Only transport/receipt metadata is normalized, never values, quality, versions or clinical dates.
            evidence="digest" in v and "resource_id" in v
            result={k:self.canonical(x) for k,x in v.items() if not (evidence and k in {"received","event_time"}) and k not in {"received_at"}}
            if evidence and "normalized" in result:
                result["normalized"]={k:x for k,x in result["normalized"].items() if k!="source_event_time"}
            if evidence and "provenance" in result:
                result["provenance"]={k:x for k,x in result["provenance"].items() if k not in {"received","event_time"}}
            return result
        if isinstance(v,list):
            result=[self.canonical(x) for x in v]
            if result and all(isinstance(x,dict) and "id" in x for x in result):result.sort(key=lambda x:str(x["id"]))
            return result
        if isinstance(v,str):
            try:return json.dumps(self.canonical(json.loads(v)),sort_keys=True,separators=(",",":"))
            except (ValueError,TypeError):return self.replace(v,self.aliases)
        return v

    def payload(self,messages,tools,final):
        if messages[0]!={"role":"system","content":self.system}:raise ProviderFailure("replay_prompt_mismatch")
        return {"manifest":self.manifest,"question":self.question,"messages":self.canonical([m for m in messages[1:] if m.get("type")!="reasoning"]),"tools":tools,"final":final}

    def key(self,messages,tools,final):return digest(self.payload(messages,tools,final))

    def match_request(self,expected,messages,tools,final,descriptor):
        payload=self.payload(messages,tools,final)
        if digest(payload)==expected:return True
        # Fresh UUIDs can change a page boundary for equal-time records. Reconstruct
        # only exact pages from the recorded, fully matched snapshot and require the
        # ORIGINAL request hash. Nothing is injected into actual tool results/grounding.
        pool=(descriptor or {}).get("context",{}).get("evidence",[])
        if not pool or len(pool)>8:return False
        variants=[payload]
        for index,message in enumerate(payload["messages"]):
            if message.get("type")!="function_call_output":continue
            try:body=json.loads(message["output"]);items=body["result"]["items"]
            except (ValueError,KeyError,TypeError):continue
            if not items or not all(isinstance(x,dict) and "digest" in x and not x.get("content") for x in items):continue
            if len(items)>len(pool):return False
            count=len(items);combinations=list(itertools.combinations(pool,count))
            if len(variants)*len(combinations)>256:return False
            expanded=[]
            for variant in variants:
                for combination in combinations:
                    candidate=copy.deepcopy(variant);replacement=copy.deepcopy(body)
                    replacement["result"]["items"]=sorted(combination,key=lambda x:str(x["id"]))
                    candidate["messages"][index]["output"]=json.dumps(replacement,sort_keys=True,separators=(",",":"))
                    expanded.append(candidate)
            variants=expanded
        return any(digest(v)==expected for v in variants)

    def encode(self,v):
        if isinstance(v,dict):return {k:self.encode(x) for k,x in v.items()}
        if isinstance(v,list):return [self.encode(x) for x in v]
        return self.replace(v,self.aliases) if isinstance(v,str) else v

    def decode(self,v):
        if isinstance(v,dict):return {k:self.decode(x) for k,x in v.items()}
        if isinstance(v,list):return [self.decode(x) for x in v]
        if isinstance(v,str):
            result=self.replace(v,self.reverse)
            if "@evidence:" in result or "@obligation:" in result:raise ProviderFailure("replay_source_mismatch")
            return result
        return v


class RecordingProvider:
    def __init__(self,inner,settings):self.inner=inner;self.settings=settings;self.frames=[]
    def bind_run(self,run,context):self.binding=Binding(run,context)
    def invoke(self,messages,tools,final=False):
        key=self.binding.key(messages,tools,final)
        turn=self.inner.invoke(messages,tools,final)
        payload=asdict(turn);payload["draft"]=turn.draft.model_dump(mode="json") if turn.draft else None
        payload["messages"]=[m for m in payload["messages"] if m.get("type")!="reasoning"]
        # Live continuation retains original reasoning; recording omits opaque encrypted content.
        original_payloads=payload.pop("payloads",[])
        self.frames.append({"key":key,"turn":self.binding.encode(scrub(payload)),"original_payloads":original_payloads})
        return turn
    def finish_run(self,run):
        target=Path(os.environ["LLM_RECORD_DIR"]);target.mkdir(parents=True,exist_ok=True)
        body={"format":2,"origin":"live-openai-responses","scenario":self.binding.scenario,"manifest":self.binding.manifest,"context_descriptor":self.binding.descriptor,
              "requested_model":self.settings.model,"base_url":self.settings.base_url,"frames":self.frames,
              "replayable":bool(self.frames),"result":{"status":run["status"],"validation":run["detail"].get("validation"),
              "usage":run["detail"]["usage"],"model_history":run["detail"].get("model_history",[]),"error":run["detail"].get("error"),"duration_ms":run["detail"]["duration_ms"]}}
        (target/(self.binding.scenario+".json")).write_text(json.dumps(scrub(body),indent=2),encoding="utf-8")
    def close(self):
        if callable(getattr(self.inner,"close",None)):self.inner.close()


class ReplayProvider:
    def __init__(self,settings):self.settings=settings;self.index=0
    def bind_run(self,run,context):
        self.binding=Binding(run,context)
        try:
            self.record=json.loads((directory()/(self.binding.scenario+".json")).read_text(encoding="utf-8"))
            if not self.record.get("replayable") or self.record.get("origin")!="live-openai-responses" or not self.binding.match_manifest(self.record.get("manifest")) or self.record.get("requested_model")!=self.settings.model:
                raise ValueError()
        except (OSError,ValueError):raise ProviderFailure("replay_recording_missing_or_context_changed") from None
    def invoke(self,messages,tools,final=False):
        try:
            if not hasattr(self,"binding"):raise ProviderFailure("replay_scenario_not_supported")
            return self._invoke(messages,tools,final)
        except ProviderFailure as error:
            error.not_sent=True
            error.telemetry={"llm_mode":"replay",**getattr(error,"telemetry",{})}
            raise
        except (KeyError,ValueError,TypeError):
            error=ProviderFailure("replay_recording_invalid");error.not_sent=True;error.telemetry={"llm_mode":"replay"};raise error from None
    def invoke_structured(self,messages,contract):
        error=ProviderFailure("replay_scenario_not_supported");error.not_sent=True;error.telemetry={"llm_mode":"replay"};raise error
    def _invoke(self,messages,tools,final=False):
        try:frame=self.record["frames"][self.index]
        except (KeyError,IndexError):
            # A live provider failure has no Turn, but its actual persisted metadata is recorded.
            result=self.record.get("result",{});history=result.get("model_history",[])
            error=result.get("error")
            if history and history[-1].get("error")==error and error:
                original=history[-1]
                failure=ProviderFailure(error,http_status=original.get("http_status"),model_name=original.get("reported_model"),response_id=original.get("response_id"))
                failure.not_sent=True
                failure.telemetry={"llm_mode":"replay","recorded_input_tokens":original["input_tokens"],"recorded_output_tokens":original["output_tokens"],"recorded_error":error}
                raise failure
            raise ProviderFailure("replay_recording_exhausted") from None
        if not self.binding.match_request(frame["key"],messages,tools,final,self.record.get("context_descriptor")):
            error=ProviderFailure("replay_request_mismatch");error.not_sent=True;error.telemetry={"llm_mode":"replay"};raise error
        from app.model_payloads import replay as record_replay
        record_replay(self.settings,frame.get("original_payloads",[]))
        self.index+=1;payload=self.binding.decode(frame["turn"])
        draft=Draft.model_validate(payload["draft"]) if payload.get("draft") else None
        turn=Turn(**{**payload,"draft":draft,"input_tokens":0,"output_tokens":0,"retries":0})
        turn.telemetry={"llm_mode":"replay","recorded_input_tokens":payload["input_tokens"],"recorded_output_tokens":payload["output_tokens"],"recorded_response_id":payload.get("response_id")}
        return turn
    def close(self):pass
