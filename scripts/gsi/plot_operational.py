#!/usr/bin/env python3
"""Render operational history and per-cycle PNG plots without a plotting server."""
import argparse,json
from operational import load_json
from environments import canonical_environment
from datetime import datetime
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.18,'savefig.facecolor':'white'})
BLUE='#0875c1';ORANGE='#d77622'
def save(fig,path):
    fig.tight_layout();fig.savefig(path,dpi=110);plt.close(fig)
def draw_summary(s,data,out,environment):
    p=data/'cycles'/(s['cycle']+'.json.gz');dest=out/(s['cycle']+'.png')
    if dest.exists() and dest.stat().st_mtime>=max(p.stat().st_mtime,Path(__file__).stat().st_mtime):return
    d=load_json(p);t=d['tables'];fig,axs=plt.subplots(2,2,figsize=(12,6.5))
    log_gradient=any((r.get('gradient') or 0)>0 for r in t['minimization'])
    offset=0
    for outer in sorted({r['outer'] for r in t['minimization']}):
        rr=[r for r in t['minimization'] if r['outer']==outer]
        xx=[offset+r['inner']-rr[0]['inner'] for r in rr]
        if offset:
            for ax in axs[0]:ax.axvline(offset-.5,color='#687887',ls='--',lw=.8,alpha=.6)
        for ax,key in zip(axs[0],['cost','gradient']):ax.plot(xx,[r[key] if r.get(key) is not None and (key=='cost' or not log_gradient or r[key]>0) else np.nan for r in rr],label=f'Externo {outer}',marker='o' if len(rr)==1 else None,markersize=4)
        offset=xx[-1]+1
    axs[0,0].set_title('Custo J');axs[0,1].set_title('Norma do gradiente');axs[0,1].set_yscale('log' if log_gradient else 'linear')
    for ax in axs[0]:
        ax.set_xlabel('Iteração acumulada')
        if t['minimization']:ax.legend()
    fit=[r for r in t['fits'] if r['use']=='asm'];obs=sorted({r['obs'] for r in fit});initial=[];final=[];counts=[]
    for o in obs:
        rr=sorted([r for r in fit if r['obs']==o],key=lambda r:r['evaluation']);f,l=rr[0],rr[-1]
        initial.append(1 if f.get('count',0)>0 and f.get('rms',0)>0 else np.nan)
        final.append(l['rms']/f['rms'] if f.get('rms',0)>0 and f.get('count',0)>0 and l.get('count',0)>0 and l.get('rms') is not None else np.nan);counts.append(l.get('count') or 0)
    x=np.arange(len(obs));axs[1,0].bar(x-.18,initial,.36,label='Primeira avaliação',color=BLUE);axs[1,0].bar(x+.18,final,.36,label='Última avaliação',color=ORANGE);axs[1,0].set_xticks(x,obs);axs[1,0].set_title('RMS relativo ao inicial · asm');axs[1,0].set_ylabel('RMS / RMS inicial');axs[1,0].legend(fontsize=8,ncol=2,loc='lower left',bbox_to_anchor=(0,1.01));axs[1,0].set_title('RMS relativo ao inicial · asm',pad=30)
    axs[1,1].bar(x,counts,color=BLUE);axs[1,1].set_xticks(x,obs);axs[1,1].set_title('Contagens finais · asm');axs[1,1].set_ylabel('Contagem tabulada (uv: vetores)')
    if not obs:
        for ax in axs[1]:ax.text(.5,.5,'Sem observações assimiladas tabuladas',ha='center',va='center',transform=ax.transAxes,fontsize=10)
        if axs[1,0].get_legend():axs[1,0].get_legend().remove()
    fig.suptitle('GSI · '+environment+' · '+s['cycle']+' UTC',fontsize=15);save(fig,dest)

def draw(s,data,out,environment):
    draw_summary(s,data,out,environment)
    from plot_diagnostics import render
    p=data/'cycles'/(s['cycle']+'.json.gz');folder=out/s['cycle'];manifest=folder/'figures.json'
    stamp=max(p.stat().st_mtime,Path(__file__).stat().st_mtime,Path(__file__).with_name('plot_diagnostics.py').stat().st_mtime)
    if manifest.exists() and manifest.stat().st_mtime>=stamp:
        return
    d=load_json(p);t=d['tables'];rid=s['cycle']
    tables={k:[dict(r,run_id=rid) for r in v] for k,v in t.items()}
    fit=[]
    for row in t['fits']:
        for metric in ('count','rms','bias','cpen','qcpen'):
            if metric in row:fit.append(dict(row,run_id=rid,type_code='all',is_total=True,metric=metric,value=row[metric]))
    tables['conventional_fit']=fit+tables['profiles']
    tables.setdefault('j_table',[])
    figures=render({'runs':[dict(s,run_id=rid,experiment=environment)],'tables':tables},folder,formats=('webp',),report=False)
    tmp=manifest.with_suffix('.tmp');tmp.write_text(json.dumps(figures,ensure_ascii=False));tmp.replace(manifest)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,required=True);ap.add_argument('--cycles',nargs='+',help='Regenerate plots for selected cycles; history remains complete');ap.add_argument('--available',action='store_true',help='Staging only: plot available cycle JSONs while extraction continues');a=ap.parse_args()
    index=json.loads((a.data/'index.json').read_text());environment=canonical_environment(index.get('environment'));
    if environment not in ('SMNA-FNCEP','SMNA-FINPE'):ap.error('O índice precisa identificar environment como SMNA-FNCEP ou SMNA-FINPE')
    out=a.data/'plots';out.mkdir(exist_ok=True)
    rows=([load_json(p)['summary'] for p in sorted((a.data/'cycles').glob('*.json.gz'))] if a.available else index['cycles']);valid=[s for s in rows if s['state']=='parsed']
    # Keep true time spacing and break missing-cycle gaps instead of connecting them.
    xs=[];ys={k:[] for k in ['wall_seconds','last_cost','radiance_nassim','cost_reduction_percent']};prev=None
    for s in rows:
        t=datetime.strptime(s['cycle'],'%Y%m%d%H')
        if prev and (t-prev).total_seconds()>21600:
            xs.append(prev+(t-prev)/2)
            for k in ys:ys[k].append(float('nan'))
        xs.append(t)
        for k in ys:ys[k].append(s.get(k) if s.get(k) is not None else float('nan'))
        prev=t
    fig,axs=plt.subplots(2,2,figsize=(12,6.5))
    for ax,k,label in zip(axs.flat,ys,['Tempo de execução (s)','Custo J final','Radiâncias: nassim final','Redução de J (%)']):
        ax.plot(xs,ys[k],'.-',lw=.7,ms=2.5,color=BLUE);ax.set_title(label);ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3,maxticks=5));ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%y'));ax.set_xlabel('Ciclo UTC')
    fig.suptitle('Histórico GSI · '+environment,fontsize=15);save(fig,out/'history.png')
    if a.cycles:valid=[s for s in valid if s['cycle'] in a.cycles]
    from concurrent.futures import ProcessPoolExecutor
    from itertools import repeat
    import multiprocessing,sys
    with ProcessPoolExecutor(max_workers=4,mp_context=multiprocessing.get_context('fork') if sys.platform=='linux' else None) as pool:
        for i,_ in enumerate(pool.map(draw,valid,repeat(a.data),repeat(out),repeat(environment)),1):
            if i%25==0 or i==len(valid):print(f'plots {i}/{len(valid)}',flush=True)
if __name__=='__main__':main()
