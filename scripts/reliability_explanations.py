"""Exactly ten live calls per explanation, against an isolated synthetic SQLite demo.
Uses configured model/key, never retries or silently changes models. Stores scrubbed traces.
"""
import json,os,subprocess,sys,time,urllib.request,http.cookiejar
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 from dotenv import dotenv_values
 env=dict(os.environ);env.update({k:v for k,v in dotenv_values(ROOT/'.env').items() if v is not None})
 if not env.get('OPENAI_API_KEY'):raise SystemExit('No configured key; no live runs made.')
 out=ROOT/'test-reports/release/live';out.mkdir(parents=True,exist_ok=True)
 if (out/'summary.json').exists():raise SystemExit('Prior live summary exists; refusing repeat paid runs.')
 env.update(DATABASE_URL='sqlite:///'+(out/'live.db').as_posix(),LLM_MODE='live',DEMO_MODE='true',REPROBRIDGE_TEST_MODE='true',CLINICAL_EVIDENCE_AGENT_ENABLED='true',EXPLANATION_RECORD_DIR='',LLM_RECORD_DIR='')
 python=str(ROOT/'.venv/Scripts/python.exe')
 subprocess.run([python,'-m','alembic','upgrade','head'],cwd=ROOT/'backend',env=env,check=True,stdout=subprocess.DEVNULL)
 log=(out/'server.log').open('w');server=subprocess.Popen([python,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8004'],cwd=ROOT/'backend',env=env,stdout=log,stderr=log)
 opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
 def api(path,body=None):
  req=urllib.request.Request('http://127.0.0.1:8004/api'+path,data=json.dumps(body).encode() if body is not None else None,headers={'Authorization':'Bearer '+env['COORDINATOR_TOKEN'],'Content-Type':'application/json'})
  with opener.open(req,timeout=100) as resp:return json.load(resp)
 try:
  for _ in range(60):
   try:api('/health');break
   except Exception:time.sleep(.5)
  api('/v1/tsp/demo/reset',{})
  sys.path.insert(0,str(ROOT/'backend'))
  from app.explanations import schema_hash
  from app.clinical.normalize import digest
  from app.investigation.replay import scrub
  rows=[]
  for case in ['tsp','history']:
   prefix='/v1/tsp' if case=='tsp' else '/v1/history-handoff'
   if case=='history':api(prefix+'/seed',{});api(prefix+'/patients/demo-amira/receive',{})
   for i in range(1,11):
    start=time.perf_counter()
    try:
     run=api(prefix+'/patients/demo-amira/explanations',{'request_id':f'release-reliability-{case}-{i}-{time.time_ns()}'})
     d=run['detail'];e=d['explanation'];row={'case':case,'trial':i,'accepted':e['accepted'],'latency_ms':round((time.perf_counter()-start)*1000),'model':d['configuration']['model'],'usage':d['usage'],'error':d['error'],'validation':d.get('validation'),'field_mismatches':e.get('field_mismatches')}
     (out/f'{case}-{i:02d}-trace.json').write_text(json.dumps(scrub(run),indent=2),encoding='utf-8')
     capsule=ROOT/'backend/demo-replays/explanation-v1'/f'{case}-demo-amira-fresh-v1.json'
     if e['accepted'] and not capsule.exists():
      h=d['model_history'][0]
      record={'format':'explanation-v1','accepted':True,'model':d['configuration']['model'],'reported_model':h['reported_model'],'response_id':h['response_id'],'context':d['explanation_context'],'context_hash':digest(d['explanation_context']),'schema_hash':schema_hash(),'fields':e['fields'],'input_tokens':d['usage']['input_tokens'],'output_tokens':d['usage']['output_tokens'],'duration_ms':d['duration_ms'],'validation':d['validation']}
      capsule.write_text(json.dumps(scrub(record),indent=2),encoding='utf-8')
    except Exception as error:row={'case':case,'trial':i,'accepted':False,'latency_ms':round((time.perf_counter()-start)*1000),'error_type':type(error).__name__}
    rows.append(row);(out/'summary.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');print(json.dumps(row),flush=True)
 finally:server.terminate();server.wait(timeout=15);log.close()
if __name__=='__main__':main()
