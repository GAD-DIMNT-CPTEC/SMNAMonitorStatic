/* Precomputed, local BAM diagnostics; supports file:// without fetch. */
(()=>{
const el=id=>document.getElementById(id);
let dataRoot='',index=null,indexTask=null,request=0,activeEnvironment='';
const base=()=>new URL(window.SMNA_CONFIG.bamRoot||'bam/',location.href).href.replace(/\/?$/,'/');
function script(url){return new Promise((resolve,reject)=>{const s=document.createElement('script');s.src=url;s.onload=()=>{s.remove();resolve();};s.onerror=()=>{s.remove();reject(Error('Não foi possível carregar os diagnósticos BAM deste ambiente.'));};document.head.append(s);});}
function loadIndex(force){if(force)indexTask=null;if(!indexTask)indexTask=script(base()+'index.js?v='+Date.now()).then(()=>{index=window.SMNA_BAM_INDEX;return index;}).catch(e=>{indexTask=null;throw e;});return indexTask;}
window.loadBAMDiagnostics=async(force=false)=>{
 const ticket=++request,root=el('bam'),select=el('bam-cycle');root.replaceChildren();select.disabled=true;
 const env=window.SMNA_CONFIG.environments[el('environment').value].label.toLowerCase();
 if(env!==activeEnvironment){select.replaceChildren();activeEnvironment=env;}
 text('p','Carregando diagnósticos BAM…',root);
 try{
  const catalog=await loadIndex(force);if(ticket!==request)return;
  const entry=catalog.environments[env],runs=entry?.runs||[];
  if(!runs.length){select.replaceChildren();throw Error('Não há diagnósticos BAM disponíveis para este ambiente.');}
  const previous=select.value;select.replaceChildren();
  for(const run of runs){const option=text('option',`${run.cycle.slice(6,8)}/${run.cycle.slice(4,6)}/${run.cycle.slice(0,4)} · ${run.cycle.slice(8)} UTC → ${run.end_cycle.slice(6,8)}/${run.end_cycle.slice(4,6)} ${run.end_cycle.slice(8)} UTC${run.normal_end?'':' · término não confirmado'}`,select);option.value=run.id;}
  if(runs.some(r=>r.id===previous))select.value=previous;select.disabled=false;
  const run=runs.find(r=>r.id===select.value);dataRoot=new URL(run.path,base()).href;
  await script(dataRoot+'diagnostics.js');if(ticket!==request)return;
  const d=window.SMNA_BAM_RUNS?.[run.id];if(!d||d.environment.toLowerCase()!==env)throw Error('Os dados recebidos não correspondem ao ambiente selecionado.');
  render(d);
  if(entry.errors?.length||run.error){const warning=document.createElement('p');warning.className='gsi-alert';warning.textContent=run.error||'A última coleta teve falhas. Os produtos disponíveis foram preservados.';root.prepend(warning);}
  const stamp=document.createElement('p');stamp.className='footnote';stamp.textContent='Catálogo gerado em '+catalog.generated_at+' · '+runs.length+' integrações disponíveis';root.prepend(stamp);
 }catch(e){if(ticket!==request)return;root.replaceChildren();text('p',e.message,root).className='gsi-alert';}
};
window.addEventListener('DOMContentLoaded',()=>el('bam-cycle').addEventListener('change',()=>window.loadBAMDiagnostics()));
function text(tag,value,parent){const n=document.createElement(tag);n.textContent=String(value);parent.append(n);return n;}
function table(parent,title,headers,rows,file){const details=document.createElement('details');parent.append(details);text('summary',title,details);if(file){const a=text('a','Baixar CSV',details);a.href=dataRoot+file+'.csv';a.download='';}const wrap=document.createElement('div');wrap.className='table-wrap';details.append(wrap);const t=document.createElement('table');wrap.append(t);const head=document.createElement('tr');t.append(head);headers.forEach(v=>text('th',v,head));rows.forEach(row=>{const tr=document.createElement('tr');t.append(tr);row.forEach(v=>text('td',v,tr));});}
function render(d){
const root=el('bam');root.replaceChildren();
text('p',`${d.source} · início ${d.start} · fim ${d.end}`,root);
const cards=document.createElement('div');cards.className='gsi-cards';root.append(cards);
for(const [label,value] of [['Execução',d.normal_end?'Término normal':'Término não confirmado'],['Resolução',d.resolution],['Integração prevista',`${d.expected_steps*d.dt/3600} h · ${d.expected_steps} passos × ${d.dt} s`],['Paralelismo',`${d.processes??'—'} processos · ${d.threads??'—'} thread/processo`]]){const c=document.createElement('div');cards.append(c);text('span',label,c);text('strong',value,c);}
text('p','Os valores globme são acompanhados de desvio-padrão espacial; não representam incerteza temporal. O log não informa tempo de parede, consumo de memória ou CFL. O término normal não garante qualidade física.',root).className='footnote';
if(!d.figures.length)text('p','O log ainda não contém diagnósticos suficientes para gerar figuras.',root).className='gsi-alert';
const gallery=document.createElement('div');gallery.className='bam-gallery';root.append(gallery);
d.figures.filter(f=>f.file!=='steps.png').forEach(f=>{const fig=document.createElement('figure');fig.className='gsi-figure';gallery.append(fig);text('h3',f.title,fig);const b=document.createElement('button');b.className='image-button';b.type='button';b.setAttribute('aria-label','Ampliar '+f.title);fig.append(b);const img=document.createElement('img');img.src=dataRoot+f.file;img.alt=f.title;img.loading='lazy';b.append(img);text('figcaption','Clique para ampliar.',fig);b.onclick=()=>{el('large-image').src=img.src;el('large-image').alt=f.title;el('viewer-title').textContent=f.title;el('original-link').href=img.src;el('viewer').showModal();};});
text('h2','Tabelas e rastreabilidade',root);
table(root,'Médias globais e desvios-padrão',['Validade UTC','Campo','Média','Desvio-padrão','Unidade'],d.global_fields,'global_fields');
table(root,'Perfis por nível · todos os valores impressos',['Validade UTC','LYR',...d.columns],d.profiles,'profiles');
table(root,'Linha AVE · preservada sem reinterpretar',['Validade UTC','LYR',...d.columns],d.averages,'averages');
table(root,'Logaritmo da pressão à superfície',['Validade UTC','G.M.LNP.','Z.S.LNP.','Z.A.LNP.'],d.pressure,'pressure');
table(root,'Coordenada vertical híbrida',['Índice','a','b','delb','p_r','delp_r','rpi_r','alpha_r'],d.hybrid,'hybrid');
table(root,'Passos de integração e inicialização',['Linha','Passo','Δt (s)','Tempo simulado (s)'],d.steps,'steps');
table(root,'Avisos do modelo',['Linha','Mensagem'],d.warnings.map(w=>[w.line,w.text]));
table(root,'Configuração dinâmica, física e arquivos de entrada',['Registro'],d.options.map(v=>[v]));
table(root,'Arquivos de saída registrados',['Arquivo e validade'],d.outputs.map(v=>[v]));
text('h2','Como interpretar',root);
const glossaryWrap=document.createElement('div');glossaryWrap.className='table-wrap';root.append(glossaryWrap);
const glossary=document.createElement('table');glossary.className='bam-glossary';glossary.setAttribute('aria-label','Definições dos diagnósticos BAM');glossaryWrap.append(glossary);
const glossaryHead=document.createElement('thead'),glossaryHeader=document.createElement('tr');glossaryHead.append(glossaryHeader);glossary.append(glossaryHead);
for(const label of ['Sigla','Descrição'])text('th',label,glossaryHeader).scope='col';
const glossaryBody=document.createElement('tbody');glossary.append(glossaryBody);
for(const [label,description] of [["LYR", "Índice da camada"], ["Z.S. DIV.", "Desvio Padrão da Média Zonal dos Coeficientes Espectrais da Previsão de 3 horas da Divergência"], ["Z.A. DIV.", "Média Zonal dos Coeficientes Espectrais da Previsão de 3 horas da Divergência"], ["Z.S. VOR.", "Desvio Padrão da Média Zonal dos Coeficientes Espectrais da Previsão de 3 horas da Vorticidade"], ["Z.A. VOR.", "Média Zonal dos Coeficientes Espectrais da Previsão de 3 horas da Vorticidade"], ["G.M. TEM.", "Média Zonal dos Coeficientes Espectrais da Previsão de 3 horas da Temperatura Absoluta"], ["Z.S. TEM.", "Desvio Padrão da Média Zonal dos Coeficientes Espectrais da Previsão de 3 horas da Temperatura Absoluta"], ["Z.A. TEM.", "Média Zonal dos Coeficientes Espectrais da Previsão de 3 horas da Temperatura Absoluta"], ["G.M. S.H.", "Média Zonal dos Coeficientes Espectrais da Previsão de 3 horas da Umidade Específica"], ["Z.S. S.H.", "Desvio Padrão da Média Zonal dos Coeficientes Espectrais da Previsão de 3 horas da Umidade Específica"], ["Z.A. S.H.", "Média Zonal dos Coeficientes Espectrais da Previsão de 3 horas da Umidade Específica"]]){const row=document.createElement('tr');glossaryBody.append(row);text('th',label,row).scope='row';text('td',description,row);}
text('p','Os valores são preservados nas unidades nativas. Os perfis usam o índice LYR (1 no topo, 64 na base), sem conversão para pressão. Os coeficientes híbridos são fornecidos separadamente. A linha AVE é transcrita literalmente, inclusive valores com precisão reduzida. Nenhum valor ausente é substituído por zero.',root);
text('p','O ambiente é definido pelo diretório de origem do log. Os passos de inicialização e reinícios de numeração são preservados e não somados como duração total. As figuras são geradas previamente pelo parser; o navegador apenas apresenta os produtos locais.',root);
const a=text('a','Baixar dados completos · JSON',root);a.href=dataRoot+'diagnostics.json';a.download='';text('p','SHA-256: '+d.sha256,root).style.overflowWrap='anywhere';
};
})();
