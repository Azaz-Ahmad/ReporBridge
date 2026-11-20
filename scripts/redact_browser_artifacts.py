"""Redact ephemeral demo authentication from Playwright reports and trace archives.
Retains stats, source evidence, failure steps and screenshots. Never prints secret values.
"""
import argparse,json,re,zipfile
from pathlib import Path

def tokens_in(report):
    found=set()
    def visit(value):
        if isinstance(value,dict):
            for key,item in value.items():
                if re.search(r'(TOKEN|API_KEY|PASSWORD)$',key,re.I) and isinstance(item,str) and len(item)>8:found.add(item)
                visit(item)
        elif isinstance(value,list):
            for item in value:visit(item)
    visit(report);return found

def sanitize(folder):
    folder=Path(folder);tokens=set();text_files=[];archives=list(folder.rglob('*.zip'))
    for path in folder.rglob('*'):
        if path.suffix.lower() not in {'.json','.log','.md','.html','.csv'} or not path.is_file():continue
        text_files.append(path)
        if path.suffix=='.json':
            try:tokens.update(tokens_in(json.loads(path.read_text(encoding='utf-8'))))
            except (ValueError,OSError):pass
    for path in archives:
        with zipfile.ZipFile(path) as source:
            for name in source.namelist():
                if name.endswith(('.trace','.network')):tokens.update(m.decode() for m in re.findall(rb'Bearer ([A-Za-z0-9_+\-/=]{20,})',source.read(name)))
    encoded=[token.encode() for token in tokens]
    def redact(data):
        for token in encoded:data=data.replace(token,b'[REDACTED_DEMO_CREDENTIAL]')
        return data
    changed=0
    for path in text_files:
        data=path.read_bytes();safe=redact(data)
        if safe!=data:path.write_bytes(safe);changed+=1
    for path in archives:
        temp=path.with_suffix('.safe.zip')
        with zipfile.ZipFile(path) as source,zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as destination:
            for item in source.infolist():
                data=source.read(item.filename)
                destination.writestr(item,data if item.filename.endswith(('.png','.jpeg','.webm')) else redact(data))
        temp.replace(path)
    return {'text_files_redacted':changed,'trace_archives_sanitized':len(archives)}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('folder');args=parser.parse_args();print(json.dumps(sanitize(args.folder)))
