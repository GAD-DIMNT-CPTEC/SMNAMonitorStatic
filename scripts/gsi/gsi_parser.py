#!/usr/bin/env python3
"""Extract SMNA/GSI text diagnostics. Python >=3.10, standard library only."""
from __future__ import annotations
import argparse, csv, hashlib, json, math, re, sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

VERSION = '1.1.1'
NUM = r'[+-]?(?:\d+\.?\d*|\.\d+)(?:(?:[EeDd][+-]?\d+)|(?:[+-]\d{3}(?![\d.])))?'
TOKEN = re.compile(NUM + r'|\*+|[+-]?(?:NaN|Infinity|Inf)', re.I)
FILES = [201,202,203,206,207,210,212,213,218,219,220,221,226,228,230,232,234,235,236]
FAMILY = {201:'ps',202:'uv',203:'t',204:'q',205:'spd',206:'ozone',207:'radiance',212:'gps',213:'sst'}
TABLES = ['minimization','cost_terms','reductions','line_search','solver_vectors','humidity','mass',
          'conventional_fit','observation_counts','observation_penalties','level_penalties','qc_events',
          'radiance_config','ozone_config','bias_coefficients','radiance_channels','radiance_summary',
          'radiance_qc','radiance_totals','ozone_totals','j_table','field_statistics','configuration',
          'resources','input_availability','messages','unparsed','inventory']

def number(s):
    if '*' in s: return None
    s=re.sub(r'^([+-]?(?:\d+\.\d*|\.\d+))([+-]\d{3})$',r'\1E\2',s)
    try: v=float(s.replace('D','E').replace('d','e'))
    except ValueError: return None
    return v if math.isfinite(v) else None

def numbers(s): return [number(m.group()) for m in TOKEN.finditer(s)]

def valid_cycle(value):
    if not re.fullmatch(r'\d{10}',str(value)): raise ValueError(f'Invalid cycle: {value}')
    datetime.strptime(str(value),'%Y%m%d%H')
    return str(value)

class Run:
    def __init__(self, directory, cycle=None, experiment='unspecified', run_id=None, stdout_name=None):
        self.directory=Path(directory).resolve()
        self.files=sorted(p for p in self.directory.iterdir() if p.is_file() and
                          (re.fullmatch(r'fort\.\d+',p.name) or ('gsi' in p.name.lower() and p.suffix=='.log')))
        if not self.files: raise ValueError(f'No GSI files in {directory}')
        if stdout_name is not None:
            if stdout_name not in [p.name for p in self.files if p.suffix=='.log']:raise ValueError('Selected stdout not found')
            self.files=[p for p in self.files if p.suffix!='.log' or p.name==stdout_name]
        stdout=[p for p in self.files if p.suffix=='.log']
        if len(stdout)>1: raise ValueError('Multiple stdout files in one directory: separate each execution and its fort files.')
        found=set()
        for p in stdout:
            for m in re.finditer(r'GESINFO:\s+Analysis date is\s+(\d{4})\s+(\d+)\s+(\d+)\s+(\d+)',p.read_text(errors='replace')):
                found.add(''.join([m[1],m[2].zfill(2),m[3].zfill(2),m[4].zfill(2)]))
            m=re.search(r'gsi(?:Stdout)?_(\d{10})',p.name,re.I)
            if m: found.add(m[1])
        if cycle: found.add(valid_cycle(cycle))
        if not found:
            for part in reversed(self.directory.parts):
                if re.fullmatch(r'\d{10}',part): found.add(part);break
        if len(found)!=1: raise ValueError(f'Cycle missing or ambiguous ({sorted(found)}): use --cycle or a manifest; do not mix executions.')
        self.cycle=valid_cycle(next(iter(found)));self.experiment=experiment
        self.run_id=run_id or f'{experiment}_{self.cycle}_{hashlib.sha256(str(self.directory).encode()).hexdigest()[:8]}'
        self.tables={k:[] for k in TABLES};self.warnings=[]
        self.meta={'run_id':self.run_id,'cycle':self.cycle,'experiment':experiment,'parser_version':VERSION,
                   'directory':str(self.directory),'completion_marker':False,'files':len(self.files)}
    def add(self, table, p, line, **data):
        record={'run_id':self.run_id,'cycle':self.cycle,'experiment':self.experiment,'source':p.name,'line':line,**data}
        self.tables[table].append(record)
        return record
    def warn(self, p, line, message):
        self.warnings.append({'run_id':self.run_id,'source':p.name,'line':line,'message':message})
    def parse(self):
        for p in self.files:
            lines=p.read_text(encoding='utf-8',errors='replace').splitlines()
            before=sum(map(len,self.tables.values()))
            if p.name=='fort.220':self.minimization(p,lines)
            elif p.name in ['fort.206','fort.207']:self.radiance(p,lines)
            elif p.name.startswith('fort.'):self.conventional(p,lines)
            else:self.stdout(p,lines)
            for n,s in enumerate(lines,1):
                if re.search(r'(?<!\S)\*{3,}(?!\S)',s) and re.search(r'(?:[Ee][+-]\d|o-g|costterms|count|bias|rms)',s):
                    if not s.strip().startswith('*'):self.warn(p,n,'Possible numeric overflow: inspect raw line.')
                if '\ufffd' in s:self.warn(p,n,'UTF-8 replacement character.')
            self.add('inventory',p,1,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                     lines=len(lines),records=sum(map(len,self.tables.values()))-before)
        present={p.name for p in self.files}
        self.meta['missing_reference_files']=[f'fort.{i}' for i in FILES if f'fort.{i}' not in present]
        if not self.meta['completion_marker']:self.warnings.append({'run_id':self.run_id,'source':'','line':0,'message':'Normal completion marker absent (not proof of failure).'})
        self.validate()
        return self
    def minimization(self,p,lines):
        outer=0;inner=None;i=0
        while i<len(lines):
            s=lines[i].strip();n=i+1
            m=re.match(r'Minimization iteration\s+(\d+)',s)
            if m:
                inner=int(m[1]);outer+=int(inner==0);i+=1;continue
            m=re.match(r'(J|b|c|EJ)\s*=(.*)',s)
            if m:
                values=numbers(m[2]);j=i+1
                while j<len(lines) and re.fullmatch(r'[\s\d.+EeDd*\-]+',lines[j]) and lines[j].strip():
                    values+=numbers(lines[j]);j+=1
                for k,v in enumerate(values,1):self.add('solver_vectors',p,n,outer=outer,inner=inner,vector=m[1],component=k,value=v,line_end=j)
                i=j;continue
            m=re.match(r'costterms\s+([\w,]+)\s*=\s*(.*)',s)
            if m:
                vals=numbers(m[2]);labels=m[1].split(',')
                if len(vals)==len(labels)+2 and all(v is not None for v in vals[:2]):
                    self.add('cost_terms',p,n,outer=int(vals[0]),inner=int(vals[1]),**dict(zip(labels,vals[2:])))
                else:self.warn(p,n,'Malformed costterms line')
            elif s.startswith('cost,grad,step,b,step?'):
                v=numbers(s.split('=',1)[1])
                if len(v)==6 and all(x is not None for x in v[:2]):
                    self.add('minimization',p,n,outer=int(v[0]),inner=int(v[1]),cost=v[2],gradient=v[3],step=v[4],beta=v[5],step_status=s.split()[-1])
                else:self.warn(p,n,'Malformed minimization line')
            elif s.startswith('penalty and grad reduction'):
                v=numbers(s.split('=',1)[1])
                if len(v)==6:self.add('reductions',p,n,outer=int(v[0]),inner=int(v[1]),cost_ratio_outer=v[2],gradient_ratio_outer=v[3],cost_ratio_initial=v[4],gradient_squared_ratio_initial=v[5])
            elif s.startswith('NL Index'):
                self.add('line_search',p,n,outer=outer,inner=inner,diagnostic='NL Index',values=numbers(s.split('Index',1)[1]),raw=s)
            elif s.startswith('NL Values'):
                raw=s
                if i+1<len(lines) and re.fullmatch(r'[\s\d.+EeDd*\-]+',lines[i+1]):
                    raw+=' '+lines[i+1].strip();i+=1
                self.add('line_search',p,n,outer=outer,inner=inner,diagnostic='NL Values',values=numbers(raw.split('Values',1)[1]),raw=raw,line_end=i+1)
            elif s.startswith(('stepsize','penalties','estimated penalty','pcgsoi: gnorm')):
                key,_,value=s.partition('=')
                if not _:key='gnorm';value=s.split(')',1)[-1]
                self.add('line_search',p,n,outer=outer,inner=inner,diagnostic=key.strip(),values=numbers(value),raw=s)
            elif (m:=re.match(r'(?:Q_DIAG:\s*)?(\d+)\s+(NEG|SUPERSAT)\s+(Q|RH)\s+COUNT,RMS=\s*(.*)',s)):
                v=numbers(m[4])
                if len(v)==2:self.add('humidity',p,n,evaluation=int(m[1]),condition=m[2],variable=m[3],count=v[0],rms=v[1])
            elif (m:=re.match(r'Q_DIAG:\s*(\d+)\s+mean_ps, mean_pw, pdryini=\s*(.*)',s)):
                v=numbers(m[2])
                if len(v)==3:self.add('mass',p,n,evaluation=int(m[1]),mean_ps=v[0],mean_pw=v[1],pdryini=v[2],unit='native_unconfirmed')
            elif s and not s.startswith(('Q_DIAG:','Minimization')):
                self.add('unparsed',p,n,section='minimization',raw=s)
            i+=1
    def conventional(self,p,lines):
        family=FAMILY.get(int(p.name.split('.')[1]),'unknown');top=[];bottom=[];evaluation=None;units='native'
        for n,line in enumerate(lines,1):
            s=line.strip()
            if s.startswith('current '):units=s.split('ranges in ',1)[-1] if 'ranges in ' in s else s;continue
            if ' ptop ' in s:top=numbers(s.split('ptop',1)[1]);continue
            if ' pbot ' in s:bottom=numbers(s.split('pbot',1)[1]);continue
            if s.startswith('pressure levels (hPa)='):
                v=numbers(s.split('=',1)[1]);top=v[:1];bottom=v[1:];continue
            m=re.match(r'o-g\s+(\d+)\s+(?:(\S+)\s+)?(asm|rej|mon)\s+(\d+|all)\s+(.*)',s)
            if m:
                evaluation=int(m[1]);obs=m[2] or family;use=m[3];typ=m[4];rest=m[5];subtype='all'
                if typ!='all':
                    pieces=rest.split(None,1)
                    if len(pieces)<2:self.warn(p,n,'Missing subtype');continue
                    subtype,rest=pieces
                metric_match=re.match(r'(count|bias|rms|cpen|qcpen)\s+(.*)',rest)
                base=dict(evaluation=evaluation,obs=obs,use=use,type_code=typ,subtype=subtype,units=units)
                if metric_match:
                    values=numbers(metric_match[2]);metric=metric_match[1]
                    if len(values)!=len(top) or len(top)!=len(bottom):self.warn(p,n,'Pressure bin count mismatch');continue
                    for k,v in enumerate(values):
                        self.add('conventional_fit',p,n,**base,metric=metric,value=v,bin=k,ptop_hpa=top[k],pbot_hpa=bottom[k],is_total=top[k]==0 and bottom[k]==2000)
                else:
                    values=numbers(rest)
                    if len(values)!=5:self.warn(p,n,'Malformed scalar fit');continue
                    for metric,v in zip(['count','bias','rms','cpen','qcpen'],values):
                        self.add('conventional_fit',p,n,**base,metric=metric,value=v,bin=0,ptop_hpa=top[0] if top else None,pbot_hpa=bottom[0] if bottom else None,is_total=True)
                continue
            m=re.match(r'type\s+(\S+)\s+jiter\s+(\d+)\s+nread\s+(\d+)\s+nkeep\s+(\d+)\s+num\s+(\d+)',s)
            if m:
                evaluation=int(m[2])
                self.add('observation_counts',p,n,evaluation=evaluation,obs=m[1],nread=int(m[3]),nkeep=int(m[4]),num=int(m[5]));continue
            m=re.match(r'type\s+(\S+)\s+pen=(.*)',s)
            if m:
                d={k:number(v) for k,v in re.findall(r'(pen|qcpen|r|qcr)\s*=\s*('+NUM+r')',s)}
                self.add('observation_penalties',p,n,evaluation=evaluation,obs=m[1],**d);continue
            m=re.match(r'num\((\w+)\)\s*=\s*(\d+)\s+at lev\s+(\d+)\s+([\w,]+)\s*=\s*(.*)',s)
            if m:
                v=numbers(m[5]);keys=m[4].split(',')
                if len(v)==len(keys):self.add('level_penalties',p,n,evaluation=evaluation,variable=m[1],count=int(m[2]),model_level=int(m[3]),**dict(zip(keys,v)))
                else:self.warn(p,n,'Model level penalty columns mismatch')
                continue
            if s.startswith('number'):
                self.add('qc_events',p,n,evaluation=evaluation,obs=family,description=s,values=numbers(s.split('=',1)[-1]));continue
            if s and not s.startswith(('o-g it','---')):self.add('unparsed',p,n,section='conventional',raw=s)
    def radiance(self,p,lines):
        stage=0;coeff=False;qc=None;qc_pending=False;channel_pending=False
        for n,line in enumerate(lines,1):
            s=line.strip()
            m=re.match(r'(\d+)\s+(\S+)\s+(?:chan|lev)\s*=',s)
            if m:
                params={key:number(value) for key,value in re.findall(r'(\w+)\s*=\s*('+NUM+r')',s)}
                self.add('radiance_config' if p.name=='fort.207' else 'ozone_config',p,n,index=int(m[1]),sensor=m[2],**params);continue
            if 'guess air mass bias correction' in s:coeff=True;continue
            if s.startswith('sat ') and 'penalty' in s:
                coeff=False;channel_pending=False
                # Each evaluation begins at the first satellite block after the summary.
                if not qc_pending:stage+=1;qc_pending=True
                qc=None;continue
            m=re.match(r'(\S+)\s+(\S+)\s+('+NUM+r')\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$',s)
            if qc_pending and m:
                qc=self.add('radiance_qc',p,n,evaluation=stage,satellite=m[1],instrument=m[2],**dict(zip(['penalty','nobs','iland','isnoice','icoast','ireduce','ivarl','nlgross'],numbers(' '.join(m.groups()[2:])))));continue
            if qc is not None and re.match(r'^[\d.+-]',s) and len(numbers(s))==8 and not re.search(r'[a-zA-Z]',re.sub(r'[EeDd][+-]?\d+','',s)):
                qc.update(dict(zip(['qcpenalty','qc1','qc2','qc3','qc4','qc5','qc6','qc7'],numbers(s))));qc['line_end']=n;qc=None;continue
            m=re.match(r'rad total\s+(penalty_all|qcpenalty_all|failed nonlinqc)=\s*(.*)',s)
            if m:
                self.add('radiance_totals',p,n,evaluation=stage,metric=m[1],value=number(m[2].strip()));channel_pending=True;qc_pending=False;continue
            m=re.match(r'o-g\s+(\d+)\s+rad\s+(\S+)\s+(\S+)\s+(.*)',s)
            if m:
                v=numbers(m[4]);channel_pending=False
                if len(v)==7:self.add('radiance_summary',p,n,evaluation=int(m[1]),satellite=m[2],instrument=m[3],**dict(zip(['nread','nkeep','nassim','penalty','qcpenalty','cpen','qccpen'],v)))
                else:self.warn(p,n,'Radiance summary columns mismatch')
                continue
            m=re.match(r'(\d+)\s+(\d+)\s+(\S+)\s+(.*)',s)
            if channel_pending and m:
                v=numbers(m[4])
                if len(v)==8:self.add('radiance_channels',p,n,evaluation=stage,index=int(m[1]),channel=int(m[2]),sensor=m[3],**dict(zip(['count','qc_rejected','signed_error','bias_uncorrected','bias_corrected','mean_penalty','rms','stddev'],v)))
                else:self.warn(p,n,'Radiance channel columns mismatch')
                continue
            m=re.match(r'(\d+)\s+(\S+)\s+(.*)',s)
            if coeff and m:
                for k,v in enumerate(numbers(m[3]),1):self.add('bias_coefficients',p,n,index=int(m[1]),sensor=m[2],coefficient=k,value=v)
                continue
            m=re.match(r'OUTER ITERATION jiter=\s*(\d+)',s)
            if m:stage=int(m[1]);continue
            m=re.match(r'ozone total\s+(\w+)=\s*(.*)',s)
            if m:self.add('ozone_totals',p,n,evaluation=stage,metric=m[1],value=number(m[2].strip()));continue
            if s and not s.startswith(('RADINFO_READ:','OZINFO_READ:','it ','qcpenalty')):self.add('unparsed',p,n,section='radiance',raw=s)
    def stdout(self,p,lines):
        outer=None;inner=None;jtable=False;config_group=None
        resources={'The total amount of wall time':('wall_seconds','s'),'The total amount of time in user mode':('user_seconds','s'),
                   'The total amount of time in sys mode':('system_seconds','s'),'The maximum resident set size (KB)':('max_rss_kb','KB')}
        for n,line in enumerate(lines,1):
            s=line.strip()
            if 'PROGRAM GSI_ANL HAS ENDED.' in s:self.meta['completion_marker']=True;self.meta['completion_line']=n
            m=re.search(r'(STARTING|ENDING) DATE-TIME\s+(.+)',s)
            if m:self.meta[m[1].lower()+'_datetime_raw']=m[2];self.add('messages',p,n,category='run_timestamp',message=s)
            m=re.search(r'START pcgsoi jiter=\s*(\d+)',s)
            if m:outer=int(m[1]);inner=0
            m=re.match(r'cost,grad,step,b,step\?\s*=\s*(.*)',s)
            if m:
                v=numbers(m[1]);outer=int(v[0]);inner=int(v[1])
                # fort.220 is canonical; avoid double ingestion of stdout's duplicate trace.
                if not any(f.name=='fort.220' for f in self.files) and len(v)==6:
                    self.add('minimization',p,n,outer=outer,inner=inner,cost=v[2],gradient=v[3],step=v[4],beta=v[5],step_status=s.split()[-1])
            m=re.match(r'Begin J table inner/outer loop\s+(\d+)\s+(\d+)',s)
            if m:inner=int(m[1]);outer=int(m[2]);jtable=True;continue
            if s.startswith('End Jo table'):jtable=False;continue
            if jtable:
                m=re.match(r'(.+?)\s+('+NUM+r')\s*$',s)
                if m:self.add('j_table',p,n,outer=outer,inner=inner,term=m[1].strip(),value=number(m[2]))
                continue
            m=re.match(r'(guess|sval|rval|analy|analysis)\s+(\S+)\s+(.*)',s)
            if m:
                v=numbers(m[3])
                if len(v)==3:self.add('field_statistics',p,n,outer=outer,inner=inner,stage=m[1],variable=m[2],mean=v[0],minimum=v[1],maximum=v[2],mean_outside_range=all(x is not None for x in v) and not v[1]<=v[0]<=v[2])
            m=re.match(r'&([A-Z][A-Z0-9_]*)',s)
            if m:config_group=m[1]
            if s=='/':config_group=None
            m=re.match(r'([A-Z][A-Z0-9_]*)\s*=\s*(.*)',s)
            if m:self.add('configuration',p,n,group=config_group,key=m[1],raw_value=m[2].rstrip(', '))
            if '=' in s:
                k,v=s.rsplit('=',1)
                if k.strip() in resources:
                    key,unit=resources[k.strip()];val=number(v.strip());self.add('resources',p,n,metric=key,value=val,unit=unit);self.meta[key]=val
                elif s.startswith('Number of '):self.add('resources',p,n,metric=k.strip(),value=number(v.strip()),unit='count')
            if 'read_obs_check:' in s:
                self.add('input_availability',p,n,available='not available' not in s,raw=s)
            if re.search(r'\bWARN(?:ING)?\b|\bFATAL\b|\bERROR\b|not found|not available|less than|exceeded|Reset to steepest',s,re.I):
                self.add('messages',p,n,category='diagnostic_message',message=s,context_next=lines[n].strip() if n<len(lines) else '')
    def validate(self):
        keys=set()
        for row in self.tables['minimization']:
            k=(row['outer'],row['inner'])
            if k in keys:self.warn(Path(row['source']),row['line'],'Duplicate minimization index; possible concatenated runs.')
            keys.add(k)
        costs={(r['outer'],r['inner']):r for r in self.tables['cost_terms']}
        for r in self.tables['minimization']:
            c=costs.get((r['outer'],r['inner']))
            if c and r['cost'] is not None:
                vals=[c[k] for k in ['Jb','Je','Jo','Jc','Jl'] if k in c]
                if all(v is not None for v in vals) and not math.isclose(sum(vals),r['cost'],rel_tol=1e-7,abs_tol=1e-5):self.warn(Path(r['source']),r['line'],'Cost != sum of named terms')
        bad=sum(r['mean_outside_range'] for r in self.tables['field_statistics'])
        if bad:self.warnings.append({'run_id':self.run_id,'source':'stdout','line':0,'message':f'{bad} field summaries have mean outside printed min/max; preserve values, inspect model weighting/normalization.'})

def discover(inputs):
    dirs=set()
    for value in inputs:
        p=Path(value).resolve()
        if not p.exists():raise ValueError(f'Input not found: {p}')
        if p.is_file():dirs.add(p.parent)
        else:
            for f in p.rglob('*'):
                if f.is_file() and (re.fullmatch(r'fort\.\d+',f.name) or ('gsi' in f.name.lower() and f.suffix=='.log')):dirs.add(f.parent)
    return sorted(dirs)

def write_json(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,allow_nan=False,indent=2)+'\n');tmp.replace(path)

def write_csv(path,rows):
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with Path(path).open('w',newline='',encoding='utf-8') as f:
        if not keys:return
        writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader()
        for r in rows:writer.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in r.items()})

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input',action='append',help='Directory root, repeatable; one directory per execution')
    ap.add_argument('--manifest',type=Path,help='JSON list of {directory, cycle?, experiment?, run_id?}')
    ap.add_argument('--cycle',help='Explicit YYYYMMDDHH, single execution only')
    ap.add_argument('--experiment',default='unspecified');ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--strict',action='store_true',help='Return nonzero when parsing warnings exist')
    args=ap.parse_args(argv)
    if bool(args.input)==bool(args.manifest):ap.error('Choose --input or --manifest')
    try:
        if args.manifest:
            if args.cycle:ap.error('--cycle cannot accompany --manifest')
            specs=json.loads(args.manifest.read_text())
            for spec in specs:spec['directory']=str((args.manifest.parent/Path(spec['directory'])).resolve())
        else:
            dirs=discover(args.input)
            if args.cycle and len(dirs)!=1:ap.error('--cycle requires exactly one execution directory')
            specs=[dict(directory=str(p),cycle=args.cycle,experiment=args.experiment) for p in dirs]
        if not specs:ap.error('No execution directories found')
        runs=[Run(**spec).parse() for spec in specs]
        if len({r.run_id for r in runs})!=len(runs):raise ValueError('Duplicate run_id')
        if len({r.directory for r in runs})!=len(runs):raise ValueError('Same execution directory specified multiple times')
    except (ValueError,OSError,TypeError) as exc:ap.error(str(exc))
    out=args.output;out.mkdir(parents=True,exist_ok=True)
    combined={k:[row for run in runs for row in run.tables[k]] for k in TABLES}
    for k,rows in combined.items():write_csv(out/(k+'.csv'),rows)
    data={'schema_version':VERSION,'runs':[r.meta for r in runs],'tables':combined,'warnings':[w for r in runs for w in r.warnings]}
    write_json(out/'diagnostics.json',data);write_csv(out/'runs.csv',data['runs']);write_csv(out/'parser_warnings.csv',data['warnings'])
    print(json.dumps({'runs':len(runs),'tables':{k:len(v) for k,v in combined.items()},'warnings':len(data['warnings'])},indent=2))
    return 2 if args.strict and data['warnings'] else 0

if __name__=='__main__':sys.exit(main())
