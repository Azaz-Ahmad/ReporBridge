"""Repeat the real replay-mode transparency journey; optionally use fresh PostgreSQL schemas."""
import argparse,json,os,secrets,subprocess,time,sys,zipfile
from pathlib import Path
from contextlib import nullcontext
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser();p.add_argument('--count',type=int,default=30);p.add_argument('--postgres',action='store_true');p.add_argument('--label',required=True);p.add_argument('--capture-dir');p.add_argument('--video',action='store_true');p.add_argument('--api-port',type=int,default=8017);p.add_argument('--web-port',type=int,default=5187);a=p.parse_args()
 out=ROOT/'test-reports/transparency'/a.label;out.mkdir(parents=True,exist_ok=False)
 sys.path.insert(0,str(ROOT/'backend'))
 from dotenv import dotenv_values
 from verify_postgres import scratch_schema
 from redact_browser_artifacts import sanitize
 from app.investigation.replay import scrub
 values=dotenv_values(ROOT/'.env');rows=[]
 for i in range(1,a.count+1):
  with (scratch_schema() if a.postgres else nullcontext(None)) as database:
   report=out/f'run-{i:02d}.json';art=out/f'run-{i:02d}-artifacts'
   env={**os.environ,'OPENAI_API_KEY':'synthetic-test-key-no-live-use','LLM_MODE':'replay','E2E_BROWSER_CHANNEL':'msedge','PLAYWRIGHT_JSON_OUTPUT_FILE':str(report),
        'REPROBRIDGE_E2E_API_PORT':str(a.api_port),'REPROBRIDGE_E2E_WEB_PORT':str(a.web_port),
        **{'E2E_'+role+'_TOKEN':secrets.token_hex(32) for role in ['COORDINATOR','REVIEWER','VIEWER']}}
   if values.get('EXPLANATION_MODEL'):env['EXPLANATION_MODEL']=values['EXPLANATION_MODEL']
   if database:
    if database.password:env['PGPASSWORD']=database.password
    env['REPROBRIDGE_E2E_DATABASE_URL']=database.set(password=None).render_as_string(hide_password=False)
   if a.capture_dir:env['TRANSPARENCY_CAPTURE_DIR']=str(Path(a.capture_dir).resolve())
   if a.video:env['TRANSPARENCY_VIDEO']='true'
   start=time.monotonic()
   with (out/f'run-{i:02d}.log').open('w',encoding='utf-8') as log:
    result=subprocess.run(['cmd.exe','/d','/c','npm.cmd','run','test:e2e','--','--config=playwright.transparency.config.ts','--reporter=line,json','--output='+str(art)],cwd=ROOT/'frontend',env=env,stdout=log,stderr=subprocess.STDOUT)
   sanitize(out)
   # Reuse the existing scrubber to exclude header objects from retained trace JSON.
   for archive in art.rglob('*.zip'):
    temporary=archive.with_suffix('.scrubbed.zip')
    with zipfile.ZipFile(archive) as source,zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as target:
     for info in source.infolist():
      data=source.read(info.filename)
      if info.filename.endswith(('.trace','.network')):
       cleaned=[]
       for line in data.decode('utf-8').splitlines():
        try:cleaned.append(json.dumps(scrub(json.loads(line))))
        except ValueError:cleaned.append(line)
       data=('\n'.join(cleaned)+'\n').encode()
      target.writestr(info,data)
    temporary.replace(archive)
   stats=json.loads(report.read_text(encoding='utf-8'))['stats'] if report.exists() else {}
   log=(out/f'run-{i:02d}.log').read_text(encoding='utf-8',errors='replace')
   row={'run':i,'exit_code':result.returncode,'seconds':round(time.monotonic()-start,2),'stats':stats,'server_exceptions':log.count('ERROR:    Exception in ASGI application')}
   rows.append(row);(out/'summary.json').write_text(json.dumps(rows,indent=2));print(json.dumps(row),flush=True)
 print(json.dumps({'passed':sum(r['exit_code']==0 for r in rows),'failed':sum(r['exit_code']!=0 for r in rows)}),flush=True)
 raise SystemExit(int(any(r['exit_code'] or r['server_exceptions'] for r in rows)))
if __name__=='__main__':main()
