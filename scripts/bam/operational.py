#!/usr/bin/env python3
"""Incremental BAM log collection and atomic static catalog publication (Linux)."""
import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urljoin

from parse_bam import parse, export

BASE = 'https://dataserver.cptec.inpe.br/dataserver_dimnt/das/carlos.bastarz/sandbox/SMNAMonitoringApp/cron_scripts/logs/'
NAME = re.compile(r'model_(\d{10})\.(\d{10})\.log\Z')
ENVS = ('smna-finpe', 'smna-fncep')

def utc():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

class Listing(HTMLParser):
    def __init__(self):
        super().__init__(); self.names=set()
    def handle_starttag(self, tag, attrs):
        href=dict(attrs).get('href', '')
        if tag=='a' and NAME.fullmatch(href): self.names.add(href)

def read_url(url, timeout):
    with urlopen(url, timeout=timeout) as r:
        return r.read()

def atomic(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,delete=False) as f:
        f.write(text); f.flush(); os.fsync(f.fileno()); temp=Path(f.name)
    temp.chmod(0o644); os.replace(temp,path)

def dump(data):
    return json.dumps(data,ensure_ascii=False,allow_nan=False).replace('<','\\u003c')

def run(args):
    out=args.output.resolve(); out.mkdir(parents=True,exist_ok=True)
    cache=args.cache.resolve();cache.mkdir(parents=True,exist_ok=True)
    with (out/'.update.lock').open('a') as lock:
        try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            print('Another BAM update holds the output lock.',file=sys.stderr); return 3
        index_path=out/'index.json'
        catalog=json.loads(index_path.read_text()) if index_path.exists() else {'schema':1,'environments':{}}
        # Content and generator fingerprint invalidate figures, even when filenames are unchanged.
        generator=hashlib.sha256(Path(__file__).read_bytes()+Path(__file__).with_name('parse_bam.py').read_bytes()).hexdigest()
        failures=[];generated=0;reused=0
        for env in ENVS:
            source=getattr(args,env.replace('-','_')) or BASE+env+'/model/'
            remote=source.startswith(('https://','http://'))
            previous=catalog['environments'].get(env,{'runs':[]})
            records={r['name']:r for r in previous['runs']}
            errors=[]
            try:
                if remote:
                    source=source.rstrip('/')+'/'
                    listing=Listing();listing.feed(read_url(source,args.timeout).decode('utf-8',errors='replace'));names=sorted(listing.names)
                else:
                    directory=Path(source)
                    if not directory.is_dir(): raise ValueError('Input directory does not exist')
                    names=sorted(p.name for p in directory.iterdir() if p.is_file() and NAME.fullmatch(p.name))
                if not names: raise ValueError('No model_YYYYMMDDHH.YYYYMMDDHH.log files found')
                if args.limit: names=names[-args.limit:]
                for name in names:
                    old=records.get(name)
                    try:
                        match=NAME.fullmatch(name);cycle,ending=match.groups()
                        start_date=datetime.strptime(cycle,'%Y%m%d%H');end_date=datetime.strptime(ending,'%Y%m%d%H')
                        if end_date<start_date: raise ValueError('End timestamp precedes cycle')
                        raw=read_url(urljoin(source,name),args.timeout) if remote else (Path(source)/name).read_bytes()
                        sha=hashlib.sha256(raw).hexdigest()
                        if old and old.get('sha256')==sha and old.get('generator')==generator and all((out/old['path']/p).is_file() for p in old.get('products',[])) and old.get('products'):
                            old['checked_at']=utc();old.pop('error',None);reused+=1;continue
                        local=cache/env/name;local.parent.mkdir(parents=True,exist_ok=True);local.write_bytes(raw)
                        data=parse(local)
                        # Verify filename cycle against the actual BAM header (not download time).
                        if datetime.strptime(data['start'],'%HZ %d/%m/%Y')!=start_date: raise ValueError('Filename cycle differs from BAM start')
                        if datetime.strptime(data['end'],'%HZ %d/%m/%Y')!=end_date: raise ValueError('Filename end differs from BAM planned end')
                        key=env+'/'+cycle+'.'+ending+'/'+sha[:16]+'-'+generator[:12]
                        target=out/key
                        if target.exists():
                            # Never overwrite published immutable assets. A unique new snapshot repairs missing products.
                            key+='-'+datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f');target=out/key
                        target.parent.mkdir(parents=True,exist_ok=True)
                        staging=Path(tempfile.mkdtemp(prefix='.build-',dir=target.parent))
                        try:
                            data.update(cycle=cycle,end_cycle=ending,source_url=urljoin(source,name) if remote else None,run_id=key)
                            export(data,staging,env.upper())
                            (staging/'diagnostics.js').write_text('window.SMNA_BAM_RUNS=window.SMNA_BAM_RUNS||{};window.SMNA_BAM_RUNS['+json.dumps(key)+']='+dump(data)+';\n',encoding='utf-8')
                            for p in staging.iterdir(): p.chmod(0o644)
                            staging.chmod(0o755);os.replace(staging,target)
                        finally:
                            if staging.exists(): shutil.rmtree(staging)
                        records[name]={'name':name,'cycle':cycle,'end_cycle':ending,'path':key+'/','id':key,'sha256':sha,'generator':generator,'normal_end':data['normal_end'],'checked_at':utc(),'products':sorted(p.name for p in target.iterdir())}
                        generated+=1
                        print(env,name,'published',flush=True)
                    except Exception as exc:
                        message=f'{env}/{name}: {exc}'; errors.append(message);print(message,file=sys.stderr,flush=True)
                        if old: old['error']='Falha ao atualizar este log; exibindo a última versão válida.'
                catalog['environments'][env]={'label':env.upper(),'source':source if remote else 'Diretório local','checked_at':utc(),'errors':errors,'runs':sorted(records.values(),key=lambda r:(r['cycle'],r['end_cycle']),reverse=True)}
            except Exception as exc:
                errors.append(f'{env}: {exc}');print(errors[-1],file=sys.stderr,flush=True)
                catalog['environments'][env]={**previous,'label':env.upper(),'checked_at':utc(),'errors':errors}
            failures.extend(errors)
        catalog['generated_at']=utc()
        # Publish the catalog only after all referenced immutable products exist.
        atomic(index_path,dump(catalog)+'\n')
        atomic(out/'index.js','window.SMNA_BAM_INDEX='+dump(catalog)+';\n')
        print(json.dumps({'generated':generated,'reused':reused,'failures':len(failures)},ensure_ascii=False),flush=True)
        return 2 if failures else 0

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--cache',type=Path,required=True,help='Private log cache, outside public site')
    p.add_argument('--smna-finpe',help='FINPE model directory or URL')
    p.add_argument('--smna-fncep',help='FNCEP model directory or URL')
    p.add_argument('--limit',type=int,default=0,help='Latest N logs to check per environment; 0 checks all; existing history preserved')
    p.add_argument('--timeout',type=int,default=45)
    a=p.parse_args()
    if a.limit<0 or a.timeout<=0: p.error('limit >= 0 and timeout > 0 required')
    os.umask(0o022)
    sys.exit(run(a))
