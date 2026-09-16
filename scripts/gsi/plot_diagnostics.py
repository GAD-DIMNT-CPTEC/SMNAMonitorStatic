#!/usr/bin/env python3
"""Render static PNG/SVG diagnostics and an offline HTML report from parser JSON."""
import argparse, html, json, re, io
from PIL import Image
from collections import Counter, defaultdict
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from gsi_parser import write_csv, write_json

plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,
                     'grid.alpha':.2,'figure.facecolor':'white','axes.titleweight':'semibold','savefig.facecolor':'white'})
COLORS=['#1467a5','#d16b24','#32845c','#9165ad','#c44857']

def subset(table,run):return [r for r in table if r['run_id']==run]
def finite(x):return x is not None and np.isfinite(x)
def esc(s):return html.escape(str(s))
def table_html(rows,cols):
    return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+esc(k)+'</th>' for k in cols)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+esc(r.get(k,''))+'</td>' for k in cols)+'</tr>' for r in rows)+'</tbody></table></div>'
def cost_sum(r):
    values=[r[k] for k in ['Jb','Je','Jo','Jc','Jl'] if k in r]
    return sum(values) if values and all(finite(x) for x in values) else None

def render(data,out, *, formats=("png","svg"), report=True):
    out.mkdir(parents=True,exist_ok=True);all_summaries=[];comparisons=[];gallery=[];assets=[];t=data['tables']
    def save(fig,name,title,description):
        fig.suptitle(title,fontsize=15,fontweight='semibold')
        fig.tight_layout(rect=(0,0,1,.94))
        for ext in formats:
            if ext=='webp':
                buffer=io.BytesIO();fig.savefig(buffer,format='png',dpi=155,bbox_inches='tight');buffer.seek(0)
                with Image.open(buffer) as im:im.save(out/(name+'.webp'),format='WEBP',lossless=True,method=4)
            else:fig.savefig(out/(name+'.'+ext),dpi=155,bbox_inches='tight')
            assets.append(name+'.'+ext)
        plt.close(fig);gallery.append((title,description,name+'.png',name+'.svg'))
    for run in data['runs']:
        rid=run['run_id'];label=f"{run['experiment']} · {run['cycle']}";slug=re.sub(r'[^a-zA-Z0-9_-]','_',rid)
        get=lambda name:subset(t[name],rid)
        rows=get('minimization');costs=get('cost_terms')
        summary={k:run.get(k) for k in ['run_id','cycle','experiment','completion_marker','wall_seconds','max_rss_kb']}
        if rows:
            a,b=rows[0],rows[-1];end=cost_sum(costs[-1]) if costs else b['cost']
            summary.update(initial_cost=a['cost'],last_cost=end,last_gradient=b['gradient'],last_gradient_inner=b['inner'],last_gradient_outer=b['outer'])
            if finite(a['cost']) and a['cost']!=0 and finite(end):summary['cost_reduction_percent']=100*(1-end/a['cost'])
            if finite(a['gradient']) and a['gradient']!=0 and finite(b['gradient']):summary['last_printed_gradient_reduction_percent']=100*(1-b['gradient']/a['gradient'])
            summary['outer_loops']=len({r['outer'] for r in rows});summary['gradient_records']=len(rows);summary['cost_term_records']=len(costs)
            fig,ax=plt.subplots(2,2,figsize=(12,8))
            offset=0
            log_gradient=any((r.get('gradient') or 0)>0 for r in rows)
            for color,outer in zip(COLORS,sorted({r['outer'] for r in rows})):
                rr=[r for r in rows if r['outer']==outer];x=[offset+r['inner']-rr[0]['inner'] for r in rr]
                if offset:
                    for a in (ax[0,0],ax[0,1],ax[1,1]):a.axvline(offset-.5,color='#687887',ls='--',lw=.8)
                offset=x[-1]+1
                ax[0,0].plot(x,[r['cost'] for r in rr],color=color,label=f'Externo {outer}',marker='o' if len(rr)==1 else None)
                ax[0,1].plot(x,[r['gradient'] if finite(r['gradient']) and (not log_gradient or r['gradient']>0) else np.nan for r in rr],color=color,label=f'Externo {outer}',marker='o' if len(rr)==1 else None)
                ax[1,1].plot(x,[r['step'] for r in rr],color=color,label=f'Externo {outer}',marker='o' if len(rr)==1 else None)
            for key,color in zip(['Jb','Jo','Jc','Jl'],COLORS):
                if costs:ax[1,0].plot(range(len(costs)),[r.get(key,np.nan) for r in costs],label=key,color=color)
            for a,title in zip(ax.flat,['Custo J','Norma do gradiente','Termos de custo','Passo da minimização']):a.set_title(title);a.legend();a.set_xlabel('Iteração acumulada')
            ax[0,1].set_yscale('log' if log_gradient else 'linear');ax[1,0].set_yscale('symlog',linthresh=1);ax[1,0].set_xlabel('Registro (sequência dos ciclos externos)')
            save(fig,slug+'_convergence',f'Minimização — {label}','Ciclos externos em sequência no eixo acumulado. O último registro costterms pode não ter gradiente correspondente; ausência não é zero.')
        fit=get('conventional_fit');group=defaultdict(dict)
        for r in fit:
            if r['type_code']=='all' and r['is_total']:
                group[(r['obs'],r['use'],r['evaluation'])][r['metric']]=r['value']
        obs=sorted({k[0] for k in group if k[1]=='asm'})
        if obs:
            fig,axes=plt.subplots(1,len(obs),figsize=(max(9,len(obs)*2.7),4),squeeze=False)
            for ax,o in zip(axes[0],obs):
                ev=sorted(k[2] for k in group if k[:2]==(o,'asm'));initial=group[(o,'asm',ev[0])];final=group[(o,'asm',ev[-1])]
                counts=[initial.get('count'),final.get('count')]
                vals=[initial.get('rms') if (counts[0] or 0)>0 else np.nan,final.get('rms') if (counts[1] or 0)>0 else np.nan]
                ax.bar([0,1],vals,color=COLORS[:2]);ax.set_xticks([0,1],[f'Aval. {ev[0]}',f'Aval. {ev[-1]}']);ax.set_title(o);ax.set_ylabel('RMS (unidade nativa)')
                change=100*(1-final['rms']/initial['rms']) if initial.get('rms') and final.get('rms') is not None else None
                comparisons.append(dict(run_id=rid,cycle=run['cycle'],obs=o,initial_evaluation=ev[0],final_evaluation=ev[-1],initial_count=counts[0],final_count=counts[1],initial_rms=initial.get('rms'),final_rms=final.get('rms'),initial_bias=initial.get('bias'),final_bias=final.get('bias'),rms_reduction_percent=change))
            save(fig,slug+'_fit',f'Ajuste às observações usadas — {label}','RMS de cada variável em sua própria unidade: ps em mb, t em K, uv em m/s, sst em °C; GPS mantém a convenção nativa do log. As amostras podem mudar entre avaliações.')
        if obs:
            fig,ax=plt.subplots(figsize=(10,4.5));bottom=np.zeros(len(obs))
            for use,color in zip(['asm','rej','mon'],COLORS):
                values=[]
                for o in obs:
                    last=max(k[2] for k in group if k[0]==o)
                    counts={u:group.get((o,u,last),{}).get('count',0) or 0 for u in ['asm','rej','mon']}
                    total=sum(counts.values());values.append(100*counts[use]/total if total else 0)
                ax.barh(obs,values,left=bottom,label=use,color=color);bottom+=np.array(values)
            ax.set_xlim(0,100);ax.set_xlabel('% das contagens tabuladas na última avaliação');ax.legend(loc='upper center',bbox_to_anchor=(.5,1.15),ncol=3);ax.invert_yaxis()
            save(fig,slug+'_qc',f'Uso, rejeição e monitoramento — {label}','Denominador: asm + rej + mon na tabela agregada de cada variável, não nread. Não misturar com contagens de perfis ou componentes de vento.')
        profiles=[o for o in ['t','uv','gps'] if any(r['obs']==o for r in fit)]
        if profiles:
            fig,axes=plt.subplots(1,len(profiles),figsize=(11,5),squeeze=False)
            for ax,o in zip(axes[0],profiles):
                rr=[r for r in fit if r['obs']==o and r['type_code']=='all' and r['use']=='asm' and not r['is_total']]
                ev=sorted({r['evaluation'] for r in rr})
                for e,color in zip([ev[0],ev[-1]],COLORS) if ev else []:
                    count={r['bin']:r['value'] for r in rr if r['evaluation']==e and r['metric']=='count'}
                    a=[r for r in rr if r['evaluation']==e and r['metric']=='rms' and (count.get(r['bin']) or 0)>0]
                    ax.plot([r['value'] for r in a],[(r['ptop_hpa']+r['pbot_hpa'])/2 for r in a],'-o',color=color,label=f'Aval. {e}',markersize=4)
                ax.invert_yaxis();ax.set_title(o);ax.set_xlabel('RMS (unidade nativa)');ax.set_ylabel('Centro da faixa de pressão (hPa)');ax.legend()
            save(fig,slug+'_profiles',f'Perfis de ajuste — {label}','Faixas sem observações são omitidas. A faixa agregada de 0–2000 hPa é excluída do perfil.')
        counts=get('observation_counts')
        if counts:
            last=max(r['evaluation'] for r in counts);rr=[r for r in counts if r['evaluation']==last]
            active=[r for r in rr if r['num']>0];summary['zero_count_families']=[r['obs'] for r in rr if r['num']==0]
            fig,ax=plt.subplots(figsize=(10,4.8));bars=ax.barh([r['obs'] for r in active],[r['num'] for r in active],color=COLORS[0]);ax.bar_label(bars,labels=[f"{r['num']:,}".replace(',', '.') for r in active],padding=4);ax.margins(x=.18);ax.set_xlabel('num impresso no log');ax.invert_yaxis()
            if not active:ax.text(.5,.5,'Nenhuma contagem positiva no log',ha='center',va='center',transform=ax.transAxes)
            save(fig,slug+'_counts',f'Contagens finais — {label}','Não somar avaliações. Para uv, num conta componentes u/v (duas por vetor); não interpretar a soma como observações independentes.')
        channels=get('radiance_channels');rad=get('radiance_summary')
        if rad:
            ev=sorted({r['evaluation'] for r in rad});sensors=sorted({r['satellite']+'/'+r['instrument'] for r in rad})
            fig,axes=plt.subplots(1,2,figsize=(12,4.5));x=np.arange(len(sensors))
            for j,e in enumerate(ev):
                a={r['satellite']+'/'+r['instrument']:r for r in rad if r['evaluation']==e}
                axes[0].bar(x+(j-1)*.25,[a[k]['nassim'] for k in sensors],width=.25,label=f'Aval. {e}',color=COLORS[j%len(COLORS)])
                axes[1].plot(sensors,[a[k]['penalty'] for k in sensors],'-o',label=f'Aval. {e}',color=COLORS[j%len(COLORS)])
            axes[0].set_xticks(x,sensors,rotation=25,ha='right');axes[1].tick_params(axis='x',rotation=25);axes[0].set_ylabel('# assim');axes[1].set_ylabel('Penalidade');axes[0].legend();axes[1].legend()
            summary['radiance_assimilated_final']=sum(r['nassim'] for r in rad if r['evaluation']==ev[-1])
            save(fig,slug+'_radiances',f'Radiâncias por plataforma — {label}','Estatísticas por plataforma/instrumento, preservando as três avaliações. Contagens por canal e por plataforma têm escopos diferentes.')
        if channels:
            last=max(r['evaluation'] for r in channels);rr=[r for r in channels if r['evaluation']==last];sensors=sorted({r['sensor'] for r in rr});ch=sorted({r['channel'] for r in rr})
            fig,axes=plt.subplots(1,2,figsize=(13,4))
            for ax,metric,title in zip(axes,['bias_corrected','rms'],['Viés após correção','RMS']):
                arr=np.full((len(sensors),len(ch)),np.nan)
                for r in rr:arr[sensors.index(r['sensor']),ch.index(r['channel'])]=r[metric]
                if metric=='bias_corrected':
                    limit=max(float(np.nanmax(np.abs(arr))),.01);im=ax.imshow(arr,aspect='auto',cmap='RdBu_r',vmin=-limit,vmax=limit)
                else:im=ax.imshow(arr,aspect='auto',cmap='viridis',vmin=0)
                ax.set_yticks(range(len(sensors)),sensors);ax.set_xticks(range(len(ch)),ch,fontsize=8);ax.set_xlabel('Canal');ax.set_title(title);ax.grid(False);fig.colorbar(im,ax=ax,shrink=.8)
            save(fig,slug+'_channels',f'Diagnósticos por canal — {label}','Valores finais disponíveis, incluindo canais monitorados (signed_error negativo na tabela CSV). Células vazias representam canais sem registro, não RMS zero.')
        mass=get('mass');humidity=get('humidity')
        if mass and humidity:
            fig,ax=plt.subplots(1,2,figsize=(11,4))
            for key,color in zip(['mean_ps','mean_pw','pdryini'],COLORS):
                rr=[r for r in mass if finite(r[key])]
                if not rr:continue
                base=rr[0][key];ax[0].plot([r['evaluation'] for r in rr],[r[key]-base for r in rr],'-o',label=key,color=color)
            for variable,color in zip(['Q','RH'],COLORS):
                rr=[r for r in humidity if r['variable']==variable and r['condition']=='SUPERSAT'];ax[1].plot([r['evaluation'] for r in rr],[r['count'] for r in rr],'-o',label=variable,color=color)
            ax[0].set_ylabel('Diferença em relação à avaliação 1 (unidade nativa)');ax[1].set_ylabel('Contagem SUPERSAT');ax[0].legend();ax[1].legend()
            for a in ax:a.set_xlabel('Avaliação');a.set_xticks(sorted({r['evaluation'] for r in mass}))
            save(fig,slug+'_constraints',f'Massa e umidade — {label}','Contagens Q e RH não devem ser somadas: podem representar os mesmos pontos. A posição do diagnóstico em relação ao clipping requer confirmação na versão SMNA.')
        jc=[r for r in get('j_table') if r['term']!='J Global']
        if jc:
            rr=[r for r in jc if r['outer']==min(r['outer'] for r in jc) and r['term']!='J Global'];fig,ax=plt.subplots(figsize=(10,4.5));bars=ax.barh([r['term'] for r in rr],[r['value'] for r in rr],color=COLORS[0]);ax.bar_label(bars,labels=[f"{r['value']:.1f}" for r in rr],padding=4);ax.margins(x=.18);ax.invert_yaxis();ax.set_xlabel('Contribuição J impressa')
            save(fig,slug+'_jterms',f'Contribuições iniciais de custo — {label}','Termos nomeados explicitamente no stdout. Não foram atribuídos nomes físicos aos componentes posicionais dos vetores J, b, c e EJ.')
        all_summaries.append(summary)
    if not report:
        return [{'title':a,'description':b,'file':str(Path(c).with_suffix('.'+formats[0]))} for a,b,c,d in gallery]
    # Multiple dates only: do not fabricate temporal evolution from a single cycle.
    if len({r['cycle'] for r in data['runs']})>=2:
        fig,ax=plt.subplots(1,2,figsize=(12,4))
        for exp in sorted({r['experiment'] for r in all_summaries}):
            rr=sorted([r for r in all_summaries if r['experiment']==exp],key=lambda r:(r['cycle'],r['run_id']))
            dates=[__import__('datetime').datetime.strptime(r['cycle'],'%Y%m%d%H') for r in rr]
            ax[0].plot(dates,[r.get('cost_reduction_percent',np.nan) for r in rr],'o',label=exp)
            ax[1].plot(dates,[r.get('wall_seconds',np.nan) for r in rr],'o',label=exp)
        ax[0].set_ylabel('Redução de J (%)');ax[1].set_ylabel('Tempo de parede (s)')
        for a in ax:a.legend();a.tick_params(axis='x',rotation=30)
        save(fig,'across_cycles','Comparação entre ciclos','Cada ponto é uma execução. Reexecuções da mesma data são preservadas; não há escolha automática de “melhor” execução.')
    write_csv(out/'cycle_summary.csv',all_summaries);write_csv(out/'fit_comparison.csv',comparisons)
    write_json(out/'figures.json',{'assets':assets,'summaries':all_summaries,'figures':[{'title':a,'description':b,'png':c,'svg':d} for a,b,c,d in gallery]})
    rows=[{k:(round(v,4) if isinstance(v,float) else v) for k,v in r.items()} for r in all_summaries]
    body='<h1>Diagnósticos GSI</h1><p>Resultados extraídos dos logs. Cada execução mantém data, experimento e origem. Figuras estáticas em PNG e SVG.</p>'
    body+='<h2>Execuções</h2>'+table_html(rows,['cycle','experiment','completion_marker','wall_seconds','initial_cost','last_cost','cost_reduction_percent'])
    body+='<p><a href="cycle_summary.csv">Resumo CSV</a> · <a href="fit_comparison.csv">Comparação de ajuste CSV</a></p>'
    body+='<h2>Cuidados de interpretação</h2><ul><li>O término normal não comprova convergência pelo critério do minimizador.</li><li>As amostras de observações mudam entre avaliações. Menor RMS não é validação independente da previsão.</li><li>Não somar linhas “all” com tipos individuais nem faixas de pressão com o total 0–2000 hPa.</li><li>Séries entre datas só são criadas com pelo menos dois ciclos distintos. Reexecuções são preservadas.</li><li>Campos nativos sem unidade confirmada permanecem sem conversão.</li></ul>'
    body+='<h2>Validação da extração</h2>'+table_html(data['warnings'],['source','line','message'])
    for title,desc,png,svg in gallery:body+=f'<section><h2>{esc(title)}</h2><p>{esc(desc)}</p><a href="{esc(svg)}">SVG vetorial</a><img src="{esc(png)}" alt="{esc(title)}"></section>'
    body+='<h2>Fontes de interpretação</h2><p>Rotinas oficiais <a href="https://github.com/NOAA-EMC/GSI/blob/124138df09f11f892442e2f073085f0d7af0f7a8/src/gsi/statsrad.f90">statsrad</a>, <a href="https://github.com/NOAA-EMC/GSI/blob/124138df09f11f892442e2f073085f0d7af0f7a8/src/gsi/dtast.f90">dtast</a> e <a href="https://github.com/NOAA-EMC/GSI/blob/124138df09f11f892442e2f073085f0d7af0f7a8/src/gsi/pcgsoi.f90">pcgsoi</a>. A compilação específica do SMNA pode conter diferenças.</p>'
    (out/'report.html').write_text('<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Diagnósticos GSI</title><style>body{max-width:1200px;margin:30px auto;padding:0 20px;font:16px/1.6 system-ui;color:#23384c}h1,h2{color:#125a8a}section{border-top:1px solid #ccd9e1;margin-top:35px}img{width:100%;height:auto}table{border-collapse:collapse;font-size:14px}th,td{padding:9px;border:1px solid #d6dfe6;text-align:left}th{background:#edf4f9}.scroll{overflow:auto}a{color:#136aa2}</style>'+body+'</html>')
    print(f'Generated {len(gallery)} figures and report.html in {out}')

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('diagnostics',type=Path);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args();render(json.loads(args.diagnostics.read_text()),args.output)
if __name__=='__main__':main()
