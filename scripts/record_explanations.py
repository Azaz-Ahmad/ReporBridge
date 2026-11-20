"""Capture accepted single-call explanations from the authorized local synthetic demo only."""
import argparse,json,os,sys,time,urllib.request,http.cookiejar
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--base-url',default='http://127.0.0.1:8000');parser.add_argument('--output',default=str(ROOT/'backend/demo-replays/explanation-v1'));parser.add_argument('--replay-check',action='store_true');parser.add_argument('--cases',nargs='+',choices=['tsp','history'],default=['tsp','history'])
    args=parser.parse_args();from dotenv import load_dotenv
    load_dotenv(ROOT/'.env');url=args.base_url.rstrip('/');parsed=urlsplit(url)
    if parsed.hostname not in {'localhost','127.0.0.1','::1'} or parsed.scheme not in {'http','https'} or parsed.username or parsed.password or parsed.query or parsed.fragment:raise SystemExit('Local demo URL required.')
    opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def api(path,body=None):
        req=urllib.request.Request(url+'/api'+path,data=json.dumps(body).encode() if body is not None else None,headers={'Authorization':'Bearer '+os.environ['COORDINATOR_TOKEN'],'Content-Type':'application/json'})
        with opener.open(req,timeout=90) as response:return json.load(response)
    session=api('/session')
    if session.get('role')!='coordinator' or not session.get('demo_mode'):raise SystemExit('Synthetic coordinator demo session required.')
    status=api('/v1/agents/clinical-evidence/status')['explanations'];mode='replay' if args.replay_check else 'live'
    if status['mode']!=mode:raise SystemExit('Restart the backend explicitly in '+mode+' mode before this operation.')
    target=Path(args.output).resolve();target.mkdir(parents=True,exist_ok=True)
    for name in [case+'-demo-amira' for case in args.cases]:
        if not args.replay_check and (target/(name+'.json')).exists():raise SystemExit('Accepted recording exists; use a new directory. Originals are preserved.')
    api('/v1/tsp/demo/reset',{})
    sys.path.insert(0,str(ROOT/'backend'))
    from app.explanations import schema_hash
    from app.clinical.normalize import digest
    from app.investigation.replay import scrub
    outcomes=[]
    for case in args.cases:
        prefix='/v1/tsp' if case=='tsp' else '/v1/history-handoff'
        if case=='history':api(prefix+'/seed',{});api(prefix+'/patients/demo-amira/receive',{})
        begin=time.perf_counter();run=api(prefix+'/patients/demo-amira/explanations',{'request_id':'record-fields-'+str(time.time_ns())});d=run['detail'];e=d['explanation']
        report=scrub({'case':case,'run_id':run['id'],'mode':mode,'model':d['configuration']['model'],'latency_ms':round((time.perf_counter()-begin)*1000),'usage':d['usage'],'accepted':e['accepted'],'agent_abstained':e['agent_abstained'],'error':d['error'],'validation':d.get('validation'),'field_mismatches':e['field_mismatches'],'model_history':d.get('model_history',[]),'tool_history':d['tool_history'],'trace':d['trace'],'fallback':e['fallback']})
        (target/(case+'-'+mode+'-result-'+str(time.time_ns())+'.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
        if e['accepted'] and not args.replay_check:
            history=d['model_history'];assert len(history)==1 and d['usage']['model_calls']==1 and not d['tool_history']
            record=scrub({'format':'explanation-v1','accepted':True,'model':d['configuration']['model'],'reported_model':history[0]['reported_model'],'response_id':history[0]['response_id'],'context':d['explanation_context'],'context_hash':digest(d['explanation_context']),'schema_hash':schema_hash(),'fields':e['fields'],'input_tokens':d['usage']['input_tokens'],'output_tokens':d['usage']['output_tokens'],'duration_ms':d['duration_ms'],'validation':d['validation']})
            (target/(case+'-demo-amira.json')).write_text(json.dumps(record,indent=2),encoding='utf-8')
        print(json.dumps({k:v for k,v in report.items() if k not in {'fallback','model_history'}},ensure_ascii=True),flush=True);outcomes.append(e['accepted'])
    raise SystemExit(0 if all(outcomes) else 1)
if __name__=='__main__':main()
