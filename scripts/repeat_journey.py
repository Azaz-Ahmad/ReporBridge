"""Repeat the complete browser journey sequentially; preserve per-invocation reports.
No live model access. Authentication uses fresh throwaway tokens; failure traces are redacted.
"""
import argparse,json,os,re,secrets,subprocess,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def redact(folder,tokens):
 for path in folder.rglob('*.zip'):
  temp=path.with_suffix('.sanitized.zip')
  with zipfile.ZipFile(path) as src,zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as dst:
   for item in src.infolist():
    value=src.read(item.filename)
    if not item.filename.endswith(('.png','.jpeg','.webm')):
     for token in tokens:value=value.replace(token.encode(),b'[REDACTED_DEMO_TOKEN]')
    dst.writestr(item,value)
  temp.replace(path)
def main():
 p=argparse.ArgumentParser();p.add_argument('--count',type=int,default=30);p.add_argument('--label',default='consecutive-30');a=p.parse_args()
 out=ROOT/'test-reports/release'/a.label;out.mkdir(parents=True,exist_ok=False);rows=[]
 for i in range(1,a.count+1):
  name=f'run-{i:02d}';report=out/(name+'.json');art=out/(name+'-artifacts')
  tokens={role:secrets.token_hex(32) for role in ['COORDINATOR','REVIEWER','VIEWER']}
  env=dict(os.environ,OPENAI_API_KEY='synthetic-test-key-no-live-use',E2E_BROWSER_CHANNEL='msedge',PLAYWRIGHT_JSON_OUTPUT_FILE=str(report),**{'E2E_'+r+'_TOKEN':v for r,v in tokens.items()})
  start=time.monotonic()
  with (out/(name+'.log')).open('w',encoding='utf-8') as log:
   run=subprocess.run(['cmd.exe','/d','/c','npm.cmd','run','test:e2e','--','--reporter=line,json','--output='+str(art)],cwd=ROOT/'frontend',env=env,stdout=log,stderr=subprocess.STDOUT)
  redact(art,list(tokens.values()))
  from redact_browser_artifacts import sanitize
  sanitize(out)
  stats=json.loads(report.read_text(encoding='utf-8'))['stats'] if report.exists() else {}
  row={'run':i,'exit_code':run.returncode,'seconds':round(time.monotonic()-start,2),'stats':stats};rows.append(row)
  (out/'summary.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');print(json.dumps(row),flush=True)
 print(json.dumps({'passed':sum(r['exit_code']==0 for r in rows),'failed':sum(r['exit_code']!=0 for r in rows)}),flush=True)
 raise SystemExit(int(any(r['exit_code'] for r in rows)))
if __name__=='__main__':main()
