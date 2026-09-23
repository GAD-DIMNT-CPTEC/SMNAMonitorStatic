#!/usr/bin/env python3
"""Extract printed BAM diagnostics and generate offline tables/figures."""
import argparse, csv, hashlib, json, re
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

NUM = r'[-+]?\d*\.?\d+(?:[EeDd][-+]?\d+)?'
COLUMNS = ['Z.S. DIV.', 'Z.A. DIV.', 'Z.S. VOR.', 'Z.A. VOR.', 'G.M. TEM.', 'Z.S. TEM.', 'Z.A. TEM.', 'G.M. S.H.', 'Z.S. S.H.', 'Z.A. S.H.']

def parse(path):
    raw=path.read_bytes(); lines=raw.decode('utf-8',errors='replace').splitlines()
    d=dict(source=path.name,sha256=hashlib.sha256(raw).hexdigest(),columns=COLUMNS,profiles=[],global_fields=[],steps=[],pressure=[],options=[],warnings=[],outputs=[],hybrid=[],averages=[])
    stamp=None; hybrid=False
    for i,line in enumerate(lines):
        if 'Model hybrid levels' in line: hybrid=True
        if hybrid:
            v=line.split()
            if len(v)==8 and v[0].isdigit():
                try: d['hybrid'].append([int(v[0])]+[float(x) for x in v[1:]])
                except ValueError: pass
            elif len(v)==4 and v[0].isdigit() and d['hybrid']:
                d['hybrid_boundary']=[float(x) for x in v]; hybrid=False
        if '**(DumpOptions)**' in line:
            value=line.split('**(DumpOptions)**')[1].strip()
            if i+1<len(lines) and not lines[i+1].startswith('**'): value+=lines[i+1].strip()
            if value: d['options'].append(value)
        if re.search(r'WARN|ERROR|FATAL|ABORT',line,re.I): d['warnings'].append({'line':i+1,'text':line})
        m=re.search(r'among (\d+) processes with (\d+) threads',line)
        if m: d.update(processes=int(m[1]),threads=int(m[2]))
        m=re.search(r'model (\S+) runs from (.*?) to (.*?) with initial state from (.*)',line)
        if m: d.update(resolution=m[1],start=m[2],end=m[3],initial=m[4])
        m=re.search(r'model executes (\d+) timesteps of length (\d+) seconds',line)
        if m: d.update(expected_steps=int(m[1]),dt=int(m[2]))
        m=re.search(r'timestep (\d+) of length ([\d.]+) seconds at simulation time (\d+) days and ([\d.]+) seconds',line)
        if m: d['steps'].append([i+1,int(m[1]),float(m[2]),int(m[3])*86400+float(m[4])])
        m=re.search(r'State of the atmosphere at (.*):',line)
        if m: stamp=m[1]
        m=re.search(r'file also contains diagnostics at (.*):',line)
        if m: stamp=m[1]
        m=re.search(r'\*\*\(rmsgt\)\*\*\s+(\d+|AVE)\s+(.*)',line)
        if m:
            vals=re.findall(NUM,m[2])
            if len(vals)==10:
                row=[stamp,m[1]]+[float(x.replace('D','E')) for x in vals]
                d['averages' if m[1]=='AVE' else 'profiles'].append(row)
        if 'G.M.LNP.=' in line: d['pressure'].append([stamp]+[float(x) for x in re.findall(r'=\s*('+NUM+')',line)])
        m=re.search(r'\*\*\(globme\)\*\*(.*?)Glob.Mean=\s*('+NUM+r'); Std.Dev.=\s*('+NUM+r')\s*; in units of (.*)',line)
        if m:
            units=m[4]
            if i+1<len(lines) and lines[i+1]=='**-1': units+='**-1'
            d['global_fields'].append([stamp,m[1].strip(),float(m[2]),float(m[3]),units])
        if '**(opnfct)** writes file' in line:
            d['outputs'].append(line.split('writes file ')[1]+' '+(lines[i+1].split('**')[-1].strip() if i+1<len(lines) else ''))
    d['normal_end']=any('MODEL EXECUTION ENDS NORMALY' in x for x in lines)
    if not all(k in d for k in ('start','end','resolution','dt','expected_steps')): raise ValueError('Missing BAM configuration header')
    d['partial']=not d['normal_end']
    d['diagnostic_times']=list(dict.fromkeys(r[0] for r in d['profiles']))
    return d

def export(d,out,environment):
    out.mkdir(parents=True,exist_ok=True); d['environment']=environment; d['figures']=[]
    def save(fig,name,title):
        fig.suptitle(title+' · '+environment); fig.tight_layout(); fig.savefig(out/(name+'.png'),dpi=145); plt.close(fig)
        d['figures'].append({'file':name+'.png','title':title})
    times=list(dict.fromkeys(r[0] for r in d['profiles']))
    for group,indices,title in ([('temperature',[4,5,6],'Temperatura · perfis impressos'),('humidity',[7,8,9],'Umidade específica · perfis impressos'),('dynamics',[0,1,2,3],'Divergência e vorticidade · perfis impressos')] if d['profiles'] else []):
        fig,axes=plt.subplots(1,len(indices),figsize=(14,6),squeeze=False)
        for ax,col in zip(axes[0],indices):
            for time in times:
                rows=[r for r in d['profiles'] if r[0]==time]
                ax.plot([r[col+2] for r in rows],[int(r[1]) for r in rows],label=time)
            ax.set(title=COLUMNS[col],xlabel='Valor impresso (unidade nativa)',ylabel='Índice do nível LYR'); ax.grid(alpha=.2); ax.invert_yaxis()
        axes[0][-1].legend(fontsize=7); save(fig,group,title)
    for name,fields,title in [('precipitation',['TOTAL PRECIPITATION','CONVECTIVE PRECIPITATION'],'Precipitação · médias globais'),('fluxes',list(dict.fromkeys(r[1] for r in d['global_fields'] if r[4]=='W M**-2')),'Fluxos de energia · médias globais')]:
        fields=[f for f in fields if any(r[1]==f for r in d['global_fields'])]
        if not fields: continue
        plot_times=list(dict.fromkeys(r[0] for r in d['global_fields'] if r[1] in fields))
        fig,ax=plt.subplots(figsize=(12,5))
        for field in fields:
            rows=[r for r in d['global_fields'] if r[1]==field]
            ax.plot([plot_times.index(r[0]) for r in rows],[r[2] for r in rows],'o-',label=field)
        ax.set_xticks(range(len(plot_times)),plot_times,fontsize=8); ax.set_ylabel('kg m⁻² dia⁻¹' if name=='precipitation' else 'W m⁻²'); ax.grid(alpha=.2); ax.legend(fontsize=8); save(fig,name,title)
    for name,headers in [('profiles',['time','level']+COLUMNS),('global_fields',['time','field','mean','stddev','units']),('steps',['line','step','dt_seconds','simulation_seconds']),('hybrid',['level','a','b','delb','p_r','delp_r','rpi_r','alpha_r']),('pressure',['time','G.M.LNP.','Z.S.LNP.','Z.A.LNP.']),('averages',['time','level']+COLUMNS)]:
        with (out/(name+'.csv')).open('w',newline='') as f:
            w=csv.writer(f);w.writerow(headers);w.writerows(d[name])
    (out/'diagnostics.json').write_text(json.dumps(d,ensure_ascii=False,indent=2))
    (out/'diagnostics.js').write_text('window.SMNA_BAM = '+json.dumps(d,ensure_ascii=False).replace('<','\\u003c')+';\n')
    print(json.dumps({k:d.get(k) for k in ['resolution','start','end','normal_end']},ensure_ascii=False))
    print('profiles:',len(d['profiles']),'global fields:',len(d['global_fields']),'steps:',len(d['steps']))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('log',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--environment',choices=['SMNA-FINPE','SMNA-FNCEP'],required=True)
    a=p.parse_args();export(parse(a.log),a.output,a.environment)
