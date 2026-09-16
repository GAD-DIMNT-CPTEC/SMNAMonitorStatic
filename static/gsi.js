/* Local, precomputed diagnostics. Fetch only the index and the selected cycle. */
(()=>{
 const el=id=>document.getElementById(id);let index=null,detail=null,request=0,gallery=[];
 let dataRoot='',activeEnvironment='',loadTicket=0;
 const environment=()=>el('environment').value;
 const dataPath=path=>dataRoot+path.replace(/^gsi\//,'');
 const fmt=(v,d=2)=>v==null?'—':Number(v).toLocaleString('pt-BR',{maximumFractionDigits:d});
 const warning=m=>m.includes('field summaries have mean outside printed min/max')?`${m.split(' ')[0]} estatísticas de campos apresentam média fora do mínimo/máximo impresso; valores preservados para conferência da ponderação ou normalização.`:m;
 const date=c=>`${c.slice(6,8)}/${c.slice(4,6)}/${c.slice(0,4)} ${c.slice(8)}Z`;
 async function read(path,root=dataRoot){const r=await fetch(root+path.replace(/^gsi\//,''),{cache:'no-cache'});if(!r.ok)throw Error(`Dados indisponíveis (HTTP ${r.status})`);if(path.endsWith('.gz')){const bytes=new Uint8Array(await r.arrayBuffer());const text=bytes[0]===31&&bytes[1]===139?await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).text():new TextDecoder().decode(bytes);return JSON.parse(text);}return r.json();}
 const localMode=location.protocol==='file:',pendingLocal=new Map();
 function scriptData(path,root=dataRoot){return new Promise((resolve,reject)=>{const script=document.createElement('script');script.src=root+path.replace(/^gsi\//,'');script.onload=()=>{script.remove();resolve();};script.onerror=()=>{script.remove();reject(Error('Arquivo local ausente: '+path+'. Extraia a pasta completa do ZIP.'));};document.head.append(script);});}
 async function localCycle(c,env=activeEnvironment,root=dataRoot){const key=env+':'+c;if(!pendingLocal.has(key)){const task=scriptData(`gsi/local/${c}.js`,root).then(()=>{const data=window.SMNA_GSI_LOCAL[env].cycles[c];delete window.SMNA_GSI_LOCAL[env].cycles[c];return data;}).finally(()=>pendingLocal.delete(key));pendingLocal.set(key,task);}return pendingLocal.get(key);}
 async function readIndex(env,root){if(!localMode)return read('gsi/index.json',root);await scriptData('gsi/local/index.js',root);return window.SMNA_GSI_LOCAL[env].index;}
 function table(id,heads,rows){const t=el(id),h=document.createElement('thead'),b=document.createElement('tbody'),tr=document.createElement('tr');for(const v of heads){const c=document.createElement('th');c.textContent=v;tr.append(c);}h.append(tr);for(const row of rows){const r=document.createElement('tr');for(const v of row){const c=document.createElement('td');c.textContent=v;r.append(c);}b.append(r);}if(!rows.length){const r=document.createElement('tr'),c=document.createElement('td');c.colSpan=heads.length;c.textContent='Sem registros disponíveis';r.append(c);b.append(r);}t.replaceChildren(h,b);}
 function chart(){
 if(!index)return;
 const selected=el('gsi-chart').value,history=selected==='history',cycle=el('gsi-cycle').value;
 el('gsi-single').hidden=selected==='all';el('gsi-gallery').hidden=selected!=='all';
 if(selected==='all'){renderGallery();return;}
 const figure=gallery.find(f=>f.file===selected);
 el('gsi-image-link').disabled=true;
 el('gsi-image').alt=history?'Histórico de duração, custo, radiâncias e redução de J':figure?.title||'Custo, gradiente, RMS relativo e contagens de '+date(cycle);
 el('gsi-image-link').setAttribute('aria-label','Ampliar '+el('gsi-image').alt);
 el('gsi-caption').textContent=history?'Todos os ciclos disponíveis · UTC. Clique para ampliar.':`${figure?.description||'Resumo do ciclo '+date(cycle)+'.'} Clique para ampliar.`;
 el('gsi-image').hidden=false;
 const imagePath=figure?`gsi/plots/${cycle}/${figure.file}`:`gsi/plots/${history?'history':cycle}.png`;
 el('gsi-image').src=dataPath(imagePath)+'?v='+encodeURIComponent(index.generated_at);
 }
 function renderGallery(){
 const container=el('gsi-gallery');container.replaceChildren();
 const heading=document.createElement('h2');heading.textContent=`${gallery.length} gráficos disponíveis · ${date(el('gsi-cycle').value)}`;container.append(heading);
 if(!gallery.length){const note=document.createElement('p');note.textContent='Não há figuras disponíveis para este ciclo.';container.append(note);return;}
 for(const f of gallery){const figure=document.createElement('figure'),title=document.createElement('h3'),button=document.createElement('button'),img=document.createElement('img'),caption=document.createElement('figcaption');
 figure.className='gsi-figure';title.textContent=f.title.split(' — ')[0];button.className='image-button';button.type='button';button.disabled=true;button.setAttribute('aria-label','Ampliar '+f.title);img.alt=f.title;img.loading='lazy';img.src=dataPath(`gsi/plots/${el('gsi-cycle').value}/${f.file}`);caption.textContent=f.description+' Clique para ampliar.';
 img.addEventListener('load',()=>{button.disabled=false;});img.addEventListener('error',()=>{img.hidden=true;caption.textContent='Imagem não encontrada. Confira se a pasta completa foi extraída.';});button.addEventListener('click',()=>showImageViewer(img.src,img.alt));button.append(img);figure.append(title,button,caption);container.append(figure);}
 }
 const chartNames={convergence:'Minimização',fit:'Ajuste RMS',qc:'Uso e rejeição',profiles:'Perfis verticais',counts:'Contagens finais',radiances:'Radiâncias por satélite',channels:'Canais de radiância',constraints:'Massa e umidade',jterms:'Contribuições de J'};
 function chartOptions(){
 const select=el('gsi-chart'),previous=select.value,kind=previous.replace(/^\d{10}_/,'');
 select.replaceChildren(new Option('Todos os gráficos','all'),new Option('Resumo do ciclo','cycle'),...gallery.map(f=>new Option(chartNames[f.file.replace(/^\d{10}_/,'').replace(/\.(png|webp)$/,'')]||f.title.split(' — ')[0],f.file)),new Option('Histórico completo','history'));
 select.value=gallery.find(f=>f.file.replace(/^\d{10}_/,'')===kind)?.file||(['all','cycle','history'].includes(previous)?previous:'all');
 }

 const units={ps:'mb',t:'K',uv:'m/s',q:'% q-sat guess',sst:'°C',gps:'nativa'};
 function fits(){const rows=detail?.tables.fits||[],out=[];for(const obs of [...new Set(rows.filter(r=>r.use===el('gsi-use').value).map(r=>r.obs))].sort()){const rr=rows.filter(r=>r.obs===obs&&r.use===el('gsi-use').value).sort((a,b)=>a.evaluation-b.evaluation),a=rr[0],z=rr.at(-1);out.push([obs,units[obs]||a.units,`${a.evaluation} → ${z.evaluation}`,fmt(a.count,0),fmt(z.count,0),a.count>0?fmt(a.rms,4):'—',z.count>0?fmt(z.rms,4):'—',a.count>0?fmt(a.bias,4):'—',z.count>0?fmt(z.bias,4):'—']);}table('gsi-fit',['Variável','Unidade','Avaliações','N inicial','N final','RMS inicial','RMS final','Bias inicial','Bias final'],out);}
 async function cycle(){if(!index||!el('gsi-cycle').value)return;const n=++request,c=el('gsi-cycle').value,s=index.cycles.find(r=>r.cycle===c);detail=null;gallery=[];el('gsi-gallery').replaceChildren();el('gsi-state').textContent='Carregando ciclo…';el('gsi-cards').replaceChildren();el('gsi-image').hidden=true;el('gsi-image-link').disabled=true;el('gsi-json').hidden=true;el('gsi-quality').textContent='';el('gsi-warnings').replaceChildren();fits();table('gsi-humidity',[],[]);table('gsi-mass',[],[]);table('gsi-rad',[],[]);table('gsi-channels',[],[]);
 try{if(s.state!=='parsed')throw Error(s.error?.includes('No GSI files')?'Ainda não havia arquivos GSI neste ciclo no momento da extração.':(s.error||'Ciclo não interpretado'));const results=localMode?await localCycle(c).then(x=>[{status:'fulfilled',value:x.detail},{status:'fulfilled',value:x.figures}]):await Promise.allSettled([read(`gsi/cycles/${c}.json.gz`),read(`gsi/plots/${c}/figures.json`)]);if(n!==request)return;
 const [dataResult,figuresResult]=results;gallery=figuresResult.status==='fulfilled'?figuresResult.value.map(f=>({...f,title:f.title.replace(/\bSMNA-FN\b/g,'SMNA-FNCEP').replace(/\bSMNA-FC\b/g,'SMNA-FINPE'),file:f.file||f.png})):[];chartOptions();chart();
 if(dataResult.status!=='fulfilled')throw Error('As figuras disponíveis estão abaixo; não foi possível carregar as tabelas: '+dataResult.reason.message);
 const d=dataResult.value;detail=d;
 const cards=[['Término normal',s.completion_marker?'Confirmado':'Não confirmado'],['Tempo de execução',s.wall_seconds==null?'—':fmt(s.wall_seconds/60)+' min'],['Redução de J',s.cost_reduction_percent==null?'—':fmt(s.cost_reduction_percent)+'%'],['Radiâncias · nassim',fmt(s.radiance_nassim,0)]];
 for(const [label,value] of cards){const card=document.createElement('div'),small=document.createElement('span'),strong=document.createElement('strong');small.textContent=label;strong.textContent=value;card.append(small,strong);el('gsi-cards').append(card);}
 el('gsi-state').className=s.last_cost===0?'gsi-alert':'';el('gsi-state').textContent=`${s.last_cost===0?'Atenção: custo J zero. Confira as contagens de assimilação. ':''}${date(c)} · ${s.files} arquivos lidos · ${s.warnings} aviso(s) de extração${s.selected_stdout?' · reexecução identificada':''}`;
 el('gsi-json').href=dataPath(`gsi/cycles/${c}.json.gz`);el('gsi-json').hidden=false;fits();
 const rad=d.tables.radiance_summary,last=Math.max(...rad.map(r=>r.evaluation));table('gsi-rad',['Satélite','Instrumento','Aval.','nread','nkeep','nassim','Penalidade'],rad.filter(r=>r.evaluation===last).map(r=>[r.satellite,r.instrument,r.evaluation,fmt(r.nread,0),fmt(r.nkeep,0),fmt(r.nassim,0),fmt(r.penalty)]));
 table('gsi-channels',['Sensor','Canal','Contagem','Rejeitadas QC','Erro com sinal','Bias corrigido','RMS'],d.tables.radiance_channels.map(r=>[r.sensor,r.channel,fmt(r.count,0),fmt(r.qc_rejected,0),fmt(r.signed_error,4),fmt(r.bias_corrected,4),fmt(r.rms,4)]));
 table('gsi-humidity',['Aval.','Condição','Variável','Contagem','RMS nativo'],d.tables.humidity.map(r=>[r.evaluation,r.condition,r.variable,fmt(r.count,0),fmt(r.rms,6)]));
 table('gsi-mass',['Aval.','mean_ps','mean_pw','pdryini'],d.tables.mass.map(r=>[r.evaluation,fmt(r.mean_ps,6),fmt(r.mean_pw,6),fmt(r.pdryini,6)]));
 el('gsi-quality').textContent=`${s.unparsed} linhas não interpretadas. Arquivos de referência ausentes: ${s.missing.join(', ')||'nenhum'}. Memória máxima reportada: ${fmt(s.max_rss_kb,0)} KB.${s.selected_stdout?' Stdout associado: '+s.selected_stdout+'. Logs anteriores excluídos: '+s.excluded_stdout_files.join(', ')+'. Associação por sequência de minimização idêntica e horário de modificação.':''}`;
 for(const w of d.warnings){const li=document.createElement('li');li.textContent=`${w.source||'Execução'}${w.line?' · linha '+w.line:''}: ${warning(w.message)}`;el('gsi-warnings').append(li);}chart();
 }catch(e){if(n!==request)return;el('gsi-state').textContent=e.message;if(el('gsi-chart').value==='history')chart();}}
 function reset(){
 detail=null;gallery=[];index=null;el('gsi-cycle').disabled=true;el('gsi-chart').disabled=true;
 el('gsi-cycle').replaceChildren();el('gsi-gallery').replaceChildren();el('gsi-cards').replaceChildren();
 el('gsi-image').hidden=true;el('gsi-image-link').disabled=true;el('gsi-json').hidden=true;
 el('gsi-snapshot').textContent='';el('gsi-quality').textContent='';el('gsi-warnings').replaceChildren();
 el('gsi-state').className='';el('gsi-state').textContent='Carregando ambiente…';
 for(const id of ['gsi-summary-csv','gsi-fits-csv'])el(id).hidden=true;
 fits();for(const id of ['gsi-humidity','gsi-mass','gsi-rad','gsi-channels'])table(id,[],[]);
 }
 window.loadGSIDiagnostics=async(force=false)=>{
 const ticket=++loadTicket,env=environment(),config=window.SMNA_CONFIG.environments[env];++request;
 if(env!==activeEnvironment||force){reset();activeEnvironment=env;dataRoot=config.gsiRoot.replace(/\/?$/,'/');}
 try{
 if(!index){const loaded=await readIndex(env,dataRoot);if(ticket!==loadTicket)return;
 if(![config.label,...(config.aliases||[])].includes(loaded.environment))throw Error('O índice não corresponde ao ambiente '+config.label+'. Confira config.js e a geração dos dados.');
 index=loaded;el('gsi-cycle').replaceChildren(...[...index.cycles].reverse().map(s=>new Option(date(s.cycle)+(s.state!=='parsed'?' · indisponível':s.last_cost===0?' · custo zero':''),s.cycle)));
 el('gsi-cycle').value=[...index.cycles].reverse().find(s=>s.state==='parsed')?.cycle||index.cycles.at(-1)?.cycle||'';
 el('gsi-snapshot').textContent=`${config.label} · ${index.parsed} de ${index.discovered} ciclos interpretados · extração ${new Date(index.generated_at).toLocaleString('pt-BR',{timeZone:'UTC'})} UTC`;
 }
 if(ticket!==loadTicket)return;
 el('gsi-summary-csv').href=dataPath('gsi/cycles.csv');el('gsi-fits-csv').href=dataPath('gsi/fits.csv');
 for(const id of ['gsi-summary-csv','gsi-fits-csv'])el(id).hidden=false;
 if(!index.cycles.length){el('gsi-state').textContent='Nenhum ciclo disponível neste ambiente.';return;}
 el('gsi-cycle').disabled=false;el('gsi-chart').disabled=false;await cycle();
 }catch(e){if(ticket===loadTicket)el('gsi-state').textContent=e.message;}
 };
 el('gsi-image-link').addEventListener('click',()=>{const img=el('gsi-image');if(!img.hidden&&img.complete&&img.naturalWidth)showImageViewer(img.currentSrc||img.src,img.alt);});
 el('gsi-image').addEventListener('load',()=>{el('gsi-image-link').disabled=el('gsi-image').hidden;});
 el('gsi-cycle').addEventListener('change',cycle);el('gsi-chart').addEventListener('change',()=>{if(gallery.length||detail||el('gsi-chart').value==='history')chart();else el('gsi-image').hidden=true;});el('gsi-use').addEventListener('change',fits);el('gsi-image').addEventListener('error',()=>{el('gsi-image').hidden=true;el('gsi-image-link').disabled=true;el('gsi-caption').textContent='Gráfico indisponível para esta seleção.';});
})();
