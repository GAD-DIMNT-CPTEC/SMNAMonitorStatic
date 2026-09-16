#!/usr/bin/env python3
"""Read dated operational directories sequentially; publish compact, static diagnostics."""
import argparse, gzip, hashlib, json, re, sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from environments import canonical_environment, STORAGE_IDS
from gsi_parser import Run, VERSION, write_csv, valid_cycle

EXPORT_VERSION = '1.3.0-env'
KEEP = ['minimization','cost_terms','conventional_fit','observation_counts','radiance_summary','radiance_totals','humidity','mass','j_table']
def load_json(p):
    return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
def dump(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix('.tmp');raw=json.dumps(obj,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode();tmp.write_bytes(gzip.compress(raw,mtime=0) if p.suffix=='.gz' else raw);tmp.replace(p)
def compact(rows):
    return [{k:v for k,v in r.items() if k not in ('run_id','cycle','experiment')} for r in rows]
def summarize(run):
    t=run.tables;m=run.meta
    s={k:m.get(k) for k in ['cycle','completion_marker','wall_seconds','max_rss_kb','files']}
    s.update(state='parsed',warnings=len(run.warnings),unparsed=len(t['unparsed']),missing=m['missing_reference_files'])
    rows=t['minimization'];costs=t['cost_terms']
    if rows:
        s.update(initial_cost=rows[0]['cost'],last_cost=rows[-1]['cost'],last_gradient=rows[-1]['gradient'],gradient_records=len(rows))
    if costs:
        vals=[costs[-1][k] for k in ['Jb','Je','Jo','Jc','Jl'] if k in costs[-1]]
        if vals and all(v is not None for v in vals):s['last_cost']=sum(vals)
    if s.get('initial_cost') and s.get('last_cost') is not None:s['cost_reduction_percent']=100*(1-s['last_cost']/s['initial_cost'])
    rs=t['radiance_summary']
    if rs:s['radiance_nassim']=sum(r['nassim'] or 0 for r in rs if r['evaluation']==max(x['evaluation'] for x in rs))
    groups={}
    for r in t['conventional_fit']:
        if r['type_code']=='all' and r['is_total']:
            key=(r['obs'],r['use'],r['evaluation'])
            groups.setdefault(key,dict(obs=r['obs'],use=r['use'],evaluation=r['evaluation'],units=r['units']))[r['metric']]=r['value']
    tables={k:compact(t[k]) for k in KEEP if k!='conventional_fit'}
    tables['fits']=list(groups.values())
    tables['profiles']=compact([r for r in t['conventional_fit'] if r['type_code']=='all' and not r['is_total'] and r['metric'] in ('count','rms','bias') and r['use']=='asm'])
    for k in ['radiance_channels','field_statistics']:
        rows=t[k]
        if k=='radiance_channels' and rows:rows=[r for r in rows if r['evaluation']==max(x['evaluation'] for x in rows)]
        tables[k]=compact(rows)
    return {'summary':s,'tables':tables,'warnings':compact(run.warnings),'unparsed_by_file':dict(Counter(r['source'] for r in t['unparsed']))}
def select_stdout(files):
    logs=[p for p in files if p.suffix=='.log']
    if len(logs)<=1:return None,{}
    fort=next((p for p in files if p.name=='fort.220'),None)
    if fort is None:raise ValueError('Multiple stdout files without fort.220 for association')
    def trace(p):return [' '.join(s.split()) for s in p.read_text(errors='replace').splitlines() if s.strip().startswith('cost,grad,step,b,step?')]
    canonical=trace(fort)
    candidates=[p for p in logs if 0<=p.stat().st_mtime-fort.stat().st_mtime<=600 and canonical and trace(p)==canonical]
    if len(candidates)!=1:raise ValueError('Multiple stdout files: no unique match by fort.220 trace and modification time')
    selected=candidates[0]
    return selected.name,{'selected_stdout':selected.name,'excluded_stdout_files':[p.name for p in logs if p!=selected],'selection_rule':'Unique identical minimization trace; stdout modified within 600 seconds after fort.220.'}

def process(p,a):
    entry={'cycle':p.name};dest=a.output/'cycles'/(p.name+'.json.gz');cached=a.audit/(p.name+'.json')
    try:
        valid_cycle(p.name)
        files=sorted(f for f in p.iterdir() if re.fullmatch(r'fort\.\d+|gsi.*\.log',f.name,re.I) and f.is_file())
        stats=[(f.name,f.stat().st_size,f.stat().st_mtime_ns) for f in files]
        fingerprint=hashlib.sha256(json.dumps([EXPORT_VERSION,VERSION,a.environment,stats]).encode()).hexdigest()
        if not a.refresh and cached.exists() and dest.exists() and (old:=json.loads(cached.read_text())).get('fingerprint')==fingerprint:
            d=load_json(dest);entry=old;entry['cached']=True
        else:
            stdout_name,selection=select_stdout(files)
            run=Run(p,cycle=p.name,experiment=a.environment,run_id=STORAGE_IDS[a.environment]+'_'+p.name,stdout_name=stdout_name).parse()
            after=[(f.name,f.stat().st_size,f.stat().st_mtime_ns) for f in files]
            if stats!=after:raise ValueError('Files changed while reading; rerun after cycle finishes')
            d=summarize(run);d['summary'].update(selection);entry.update(fingerprint=fingerprint,cached=False,inventory=run.tables['inventory'],warnings=run.warnings,unparsed_by_file=d['unparsed_by_file'])
            dump(dest,d);dump(cached,entry)
            del run
        return d['summary'],entry,[{'cycle':p.name,**r} for r in d['tables']['fits']]
    except Exception as exc:
        # A bad cycle must not prevent the rest of the archive being processed.
        error=f'{type(exc).__name__}: {exc}'
        dest.unlink(missing_ok=True)
        return {'cycle':p.name,'state':'error','error':error},{'cycle':p.name,'error':error},[]

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--environment',required=True,type=canonical_environment,choices=['SMNA-FNCEP','SMNA-FINPE'],help='Identidade do conjunto de dados; use saída e auditoria separadas por ambiente')
    ap.add_argument('--input',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--audit',type=Path,required=True);ap.add_argument('--refresh',action='store_true')
    ap.add_argument('--workers',type=int,default=4,choices=range(1,9),help='Bounded cycle workers (1–8)')
    ap.add_argument('--limit',type=int,help='Optional latest N directories for a smoke test')
    a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=True);a.audit.mkdir(parents=True,exist_ok=True)
    dirs=sorted(p for p in a.input.iterdir() if p.is_dir() and re.fullmatch(r'\d{10}',p.name))
    if a.limit:dirs=dirs[-a.limit:]
    summaries=[];audit=[];fitrows=[]
    from concurrent.futures import ProcessPoolExecutor
    from itertools import repeat
    import multiprocessing
    with ProcessPoolExecutor(max_workers=a.workers,mp_context=multiprocessing.get_context("fork") if sys.platform=="linux" else None) as pool:
        for i,(summary,entry,fr) in enumerate(pool.map(process,dirs,repeat(a)),1):
            summaries.append(summary);audit.append(entry);fitrows.extend(fr)
            if i%10==0 or i==len(dirs):print(f'{i}/{len(dirs)} {summary["cycle"]}',flush=True)
    index={'schema_version':EXPORT_VERSION,'generated_at':datetime.now(timezone.utc).isoformat(),'environment':a.environment,'cycles':summaries,'discovered':len(dirs),'parsed':sum(s['state']=='parsed' for s in summaries)}
    dump(a.output/'index.json',index);dump(a.audit/'audit.json',audit)
    write_csv(a.output/'cycles.csv',summaries);write_csv(a.output/'fits.csv',fitrows)
    print(json.dumps({k:v for k,v in index.items() if k!='cycles'},indent=2))
    return 0 if index['parsed']==len(dirs) else 2
if __name__=='__main__':sys.exit(main())
