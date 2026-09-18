'use strict';
const BASE = 'https://dataserver.cptec.inpe.br/dataserver_dimnt/das/carlos.bastarz/sandbox/SMNAMonitoringApp/cron_scripts/';
const $ = id => document.getElementById(id);
const inventoryKey=()=>window.SMNA_CONFIG.environments[$('environment').value].inventoryKey;
const logsKey=()=>window.SMNA_CONFIG.environments[$('environment').value].logsKey;
const products = [{environment:window.SMNA_CONFIG.environments['smna-fn'].sourceKey,name:'SMNA-FNCEP',label:'SMNA-FNCEP'}];
const selectors = ['date', 'variable', 'level', 'forecast'];
const cache = new Map();
let revision = 0, view = 'status';
const variableNames = {Zonal_wind_u:'Vento zonal (u)',Meridional_wind_v:'Vento meridional (v)',Omega:'Omega',Stream_function:'Função de corrente',Velocity_potential:'Potencial de velocidade',Geopotential_height:'Altura geopotencial',Absolute_temperature:'Temperatura absoluta',Specific_humidity:'Umidade específica',Vertical_dist_total_cloud_cover:'Cobertura de nuvens',Time_mean_surface_relative_humidity:'Umidade relativa à superfície',Surface_pressure:'Pressão à superfície',Surface_temperature:'Temperatura à superfície',Pressure_reduced_to_msl:'Pressão ao nível do mar','10_metre_u-wind_component':'Vento zonal a 10 m','10_metre_v-wind_component':'Vento meridional a 10 m','Inst._precipitable_water':'Água precipitável'};
function dateLabel(d){return /^\d{10}$/.test(d)?`${d.slice(6,8)}/${d.slice(4,6)}/${d.slice(0,4)} · ${d.slice(8)} UTC`:d;}
function notice(text, error=false){$('notice').textContent=text;$('notice').classList.toggle('error',error);}
async function resource(path){
 const hit=cache.get(path); if(hit && Date.now()-hit.time<60000)return hit.value;
 const response=await fetch(BASE+path,{signal:AbortSignal.timeout(15000),cache:'no-cache'});
 if(!response.ok){const e=new Error(`Servidor respondeu HTTP ${response.status}.`);e.status=response.status;throw e;}
 const value={text:await response.text(),modified:response.headers.get('last-modified')};cache.set(path,{time:Date.now(),value});
 let cachedBytes=0;for(const item of cache.values())cachedBytes+=item.value.text.length*2;
 while(cache.size>1&&(cache.size>60||cachedBytes>16*1024*1024)){const key=cache.keys().next().value;cachedBytes-=cache.get(key).value.text.length*2;cache.delete(key);}
 return value;
}
async function listing(path, files=false){
 try{
  const {text}=await resource('anls_imgs/'+path);
  const doc=new DOMParser().parseFromString(text,'text/html');
  return [...doc.querySelectorAll('a[href]')].map(a=>a.getAttribute('href')).filter(x=>files?/^\d+\.jpg$/.test(x):/^[\w.\-]+\/$/.test(x)).map(x=>decodeURIComponent(x.replace(files?/\.jpg$/:/\/$/,'')));
 }catch(e){if(e.status===404)return [];throw e;}
}
function path(product, depth=3){const parts=[product.environment,product.name,...selectors.slice(0,depth).map(id=>$(id).value)];return parts.map(encodeURIComponent).join('/')+'/';}
function setOptions(id, values, label, preferred){const select=$(id),old=preferred??select.value;select.replaceChildren(...values.map(v=>new Option(label(v),v)));if(values.includes(old))select.value=old;select.disabled=!values.length;}
function clearMaps(text){$('map-grid').replaceChildren(...products.map(product=>{const card=document.createElement('article');card.className='map-card';const heading=document.createElement('h2');heading.textContent=product.label;const frame=document.createElement('div');frame.className='map-frame';const p=document.createElement('p');p.className='image-message';p.textContent=text;frame.append(p);card.append(heading,frame);return card;}));}
async function loadMaps(start=0){
 const ticket=++revision;
 for(let i=start;i<selectors.length;i++)$(selectors[i]).disabled=true;
 clearMaps('Consultando disponibilidade…');notice('Consultando os arquivos disponíveis…');
 try{
  let available,comparisonDates=[];
  for(let stage=start;stage<4;stage++){
   available=await Promise.all(products.map(p=>listing(path(p,stage),stage===3)));
   if(ticket!==revision)return;
   let values=[...new Set(available.flat())];
   if(stage===0)values=values.filter(v=>/^\d{10}$/.test(v)).sort().reverse();
   else if(stage===1)values.sort((a,b)=>(variableNames[a]||a).localeCompare(variableNames[b]||b,'pt-BR'));
   else values=values.filter(v=>/^\d+$/.test(v)).sort((a,b)=>stage===2?Number(b)-Number(a):Number(a)-Number(b));
   if(!values.length){for(let i=stage;i<4;i++)setOptions(selectors[i],[],x=>x);clearMaps('Nenhuma imagem publicada para esta seleção.');notice('Não há arquivos para esta seleção. Escolha outra data ou variável.');return;}
   if(stage===0&&start===0)comparisonDates=values.filter(v=>available.every(list=>list.includes(v)));
   if(stage===3&&start===0&&available.some(list=>!list.length)&&comparisonDates.length>1){comparisonDates.shift();$('date').value=comparisonDates[0];stage=0;continue;}
   const label=stage===0?dateLabel:stage===1?(v=>variableNames[v]||v.replaceAll('_',' ')):stage===2?(v=>v):(v=>`${v} horas`);
   setOptions(selectors[stage],values,label,stage===0&&start===0?(values.find(v=>available.every(list=>list.includes(v)))||values[0]):stage===1&&start===0?'Zonal_wind_u':stage===3&&start===0?(values.find(v=>available.every(list=>list.includes(v)))||values[0]):undefined);
  }
  if(ticket!==revision)return;
  drawMaps(available,ticket);
  notice(`${dateLabel($('date').value)} · ${variableNames[$('variable').value]||$('variable').value} · Nível ${$('level').value} · +${$('forecast').value} h`);
 }catch(e){if(ticket!==revision)return;clearMaps('Não foi possível consultar as imagens.');notice('Falha ao acessar o servidor de dados.',true);}
}
function showImageViewer(url,description){
 $('viewer-title').textContent=description;$('large-image').src=url;$('large-image').alt=description;$('original-link').href=url;$('viewer').showModal();
}
function drawMaps(available,ticket){
 $('map-grid').replaceChildren();
 products.forEach((product,index)=>{
  const card=document.createElement('article');card.className='map-card';
  const h=document.createElement('h2');h.textContent=product.label;
  const frame=document.createElement('div');frame.className='map-frame';
  const message=document.createElement('p');message.className='image-message';
  const bottom=document.createElement('div');bottom.className='card-bottom';
  const meta=document.createElement('span');meta.textContent=`${product.label} · +${$('forecast').value} h`;bottom.append(meta);
  card.append(h,frame,bottom);$('map-grid').append(card);
  if(!available[index].includes($('forecast').value)){message.textContent='Imagem não publicada para esta combinação.';frame.append(message);return;}
  message.textContent='Carregando imagem…';frame.append(message);
  const url=BASE+'anls_imgs/'+path(product)+encodeURIComponent($('forecast').value)+'.jpg';
  const description=`${product.label} · ${dateLabel($('date').value)} · ${variableNames[$('variable').value]||$('variable').value} · nível ${$('level').value} · +${$('forecast').value} h`;
  const img=new Image();img.alt=description;img.decoding='async';
  const imageButton=document.createElement('button');imageButton.className='image-button';imageButton.setAttribute('aria-label',`Ampliar ${description}`);
  const link=document.createElement('a');link.href=url;link.target='_blank';link.rel='noopener';link.textContent='Abrir original ↗';
  const timer=setTimeout(()=>{if(ticket===revision && !img.complete)message.textContent='O servidor está demorando a enviar a imagem. Aguarde ou atualize a disponibilidade.';},15000);
  img.onload=()=>{clearTimeout(timer);if(ticket!==revision)return;imageButton.append(img);frame.replaceChildren(imageButton);bottom.append(link);};
  img.onerror=()=>{clearTimeout(timer);if(ticket!==revision)return;message.textContent='Imagem indisponível no momento. Atualize para tentar novamente.';frame.replaceChildren(message);};
  imageButton.addEventListener('click',()=>{showImageViewer(url,description);});
  img.src=url;
 });
}
function parseCSV(text){
 const rows=[];let row=[],field='',quoted=false;
 text=text.replace(/^\uFEFF/,'');
 for(let i=0;i<text.length;i++){
  const c=text[i];
  if(c==='"'){if(quoted&&text[i+1]==='"'){field+='"';i++;}else quoted=!quoted;}
  else if(c===','&&!quoted){row.push(field);field='';}
  else if((c==='\n'||c==='\r')&&!quoted){if(c==='\r'&&text[i+1]==='\n')i++;row.push(field);if(row.some(v=>v!==''))rows.push(row);row=[];field='';}
  else field+=c;
 }
 if(quoted)throw new Error('CSV incompleto');
 if(field!==''||row.length){row.push(field);rows.push(row);}return rows;
}
function statusLogURL(value,environment,header){
 // Rebuild known log links from the current environment; never insert CSV HTML.
 if(!/^Action (GSI|PRE|MODEL|POS)$/.test(header)||!Object.values(window.SMNA_CONFIG.environments).some(e=>e.logsKey===environment))return null;
 const m=value.match(/<a\b[^>]*\bhref\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))[^>]*>\s*CHECK LOGS\s*<\/a>/i);
 if(!m)return null;
 try{
  const url=new URL(m[1]||m[2]||m[3],BASE);
  if(url.protocol!=='https:'||url.hostname!=='dataserver.cptec.inpe.br')return null;
  const file=url.pathname.split('/').pop();
  const match=file.match(/^(gsi|pre|model|pos)_\d{10}(?:\.\d{10})?\.log$/);
  if(!match||match[1]!==header.slice(7).toLowerCase())return null;
  return BASE+`logs/${environment}/${match[1]}/${file}`;
 }catch{return null;}
}
async function loadStatus(){
 const ticket=++revision,env=logsKey();
 $('status-table').replaceChildren();$('table-meta').textContent='';$('csv-link').hidden=true;notice('Consultando status operacional…');
 try{
  const source=`logs/${env}/logs.csv`;$('csv-link').href=BASE+source;$('csv-link').hidden=false;
  const {text,modified}=await resource(source);
  if(ticket!==revision)return;
  const [headers,...rows]=parseCSV(text);
  if(!headers?.includes('Current Date')||!headers.includes('Last Operational Run'))throw new Error('Formato inesperado');
  const translations={'Current Date':'Data do registro','Last Operational Run':'Ciclo operacional'};
  const table=$('status-table'),thead=document.createElement('thead'),tr=document.createElement('tr');
  for(const h of headers){const th=document.createElement('th');th.scope='col';th.textContent=translations[h]||h;tr.append(th);}thead.append(tr);table.append(thead);
  const tbody=document.createElement('tbody');
  for(const row of rows){const tr=document.createElement('tr');headers.forEach((header,i)=>{const td=document.createElement('td'),value=row[i]??'';if(header.startsWith('Status ')&&['A','C','P'].includes(value)){const badge=document.createElement('span');badge.className='badge '+({A:'awaiting',C:'completed',P:'processing'}[value]);badge.textContent=value;badge.title={A:'Aguardando',C:'Concluído',P:'Processando'}[value];td.append(badge);}else {const href=statusLogURL(value,env,header);if(href){const a=document.createElement('a');a.href=href;a.textContent='⚠️ CHECK LOGS';a.target='_blank';a.rel='noopener noreferrer';td.append(a);}else td.textContent=value;}tr.append(td);});tbody.append(tr);}table.append(tbody);
  $('csv-link').href=BASE+source;$('csv-link').hidden=false;
  $('table-meta').textContent=`${rows.length} registros${modified?' · Arquivo atualizado em '+new Date(modified).toLocaleString('pt-BR',{timeZone:'UTC'})+' UTC':''}`;
  const latest=rows.map(r=>r[headers.indexOf('Current Date')]).filter(Boolean).sort().at(-1);
  const parsed=latest?Date.parse(latest.replace(/^(\d{4}-\d{2}-\d{2})-(\d{2}:\d{2})$/,'$1T$2:00Z')):NaN;
  const old=Number.isFinite(parsed)&&Date.now()-parsed>36*3600000;
  notice(rows.length?`${old?'Dados antigos: ':''}último registro publicado em ${latest}. Horários em UTC.`:'Nenhum registro publicado.',old);
 }catch(e){if(ticket!==revision)return;notice('Não foi possível carregar o arquivo CSV de status deste ambiente.',true);}
}
let logStage='gsi', logFiles={}, logBlob=null, obsData=[], obsFiltered=[], obsPage=0;
const PAGE_SIZE=100;
function fileDownload(text,name){const url=URL.createObjectURL(new Blob([text],{type:'text/plain;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
async function loadLogs(){
 const ticket=++revision,env=logsKey();
 $('log-date').disabled=true;$('log-file').disabled=true;$('log-content').textContent='';$('log-download').hidden=true;$('log-meta').textContent='';notice('Consultando os ciclos disponíveis…');
 logFiles={};
 document.querySelectorAll('[data-stage]').forEach(b=>b.disabled=true);
 const results=await Promise.allSettled(['gsi','pre','model','pos'].map(async stage=>{
  try{const {text}=await resource(`logs/${env}/${stage}/`);const doc=new DOMParser().parseFromString(text,'text/html');
   const pattern=new RegExp(`^${stage}_(\\d{10})(?:\\.\\d{10})?\\.log$`);
   return [stage,[...doc.querySelectorAll('a[href]')].map(a=>a.getAttribute('href')).filter(f=>pattern.test(f))];
  }catch(e){if(e.status===404)return [stage,[]];throw e;}
 }));
 if(ticket!==revision)return;
 for(const r of results)if(r.status==='fulfilled')logFiles[r.value[0]]=r.value[1];
 if(results.some(r=>r.status==='rejected')){notice('Não foi possível consultar os diretórios dos logs.',true);return;}
 const cycles=[...new Set(Object.values(logFiles).flat().map(f=>f.match(/_(\d{10})/)[1]))].sort().reverse();
 setOptions('log-date',cycles,dateLabel,cycles[0]);
 if(!cycles.length){notice('Nenhum log publicado para este ambiente.');return;}
 document.querySelectorAll('[data-stage]').forEach(b=>b.disabled=false);
 selectLog();
}
function selectLog(){
 const files=(logFiles[logStage]||[]).filter(f=>f.startsWith(`${logStage}_${$('log-date').value}`)).sort();
 setOptions('log-file',files,x=>x);loadLogFile();
}
async function loadLogFile(){
 const ticket=++revision,file=$('log-file').value;
 $('log-content').textContent='';$('log-download').hidden=true;$('log-meta').textContent='';
 if(logBlob){URL.revokeObjectURL(logBlob);logBlob=null;}
 if(!file){notice('Nenhum log desta etapa foi publicado para o ciclo selecionado.');return;}
 notice(`Carregando ${logStage.toUpperCase()}…`);
 try{
  const {text}=await resource(`logs/${logsKey()}/${logStage}/${file}`);
  if(ticket!==revision)return;
  $('log-content').textContent=text||'Arquivo vazio.';$('log-content').scrollTop=0;
  $('log-meta').textContent=`${file} · ${new Intl.NumberFormat('pt-BR').format(text?text.split('\n').length:0)} linhas`;
  logBlob=URL.createObjectURL(new Blob([text],{type:'text/plain;charset=utf-8'}));$('log-download').href=logBlob;$('log-download').download=`${$('environment').value}_${file}`;$('log-download').hidden=false;
  notice(`${dateLabel($('log-date').value)} · ${logStage.toUpperCase()}`);
 }catch(e){if(ticket===revision)notice('Não foi possível carregar o log. Atualize para tentar novamente.',true);}
}
function observationDate(value){
 if(!/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(value))return null;
 const d=new Date(value.replace(' ','T')+'Z');
 return Number.isFinite(d.getTime())&&d.toISOString().slice(0,19)===value.replace(' ','T')?value:null;
}
function normalizeObservations(text){
 const [headers,...rows]=parseCSV(text);
 const required=['Tamanho do Download (KB)','Data do Download','Fuso Horário','Nome do Arquivo','Tipo de Arquivo','Horário Sinótico','Tipo de Observação','Data da Observação'];
 if(!headers||required.some(h=>!headers.includes(h)))throw new Error('Formato de inventário inesperado');
 const data=[];let skipped=0;
 for(const row of rows){
  const r=Object.fromEntries(headers.map((h,i)=>[h,row[i]??'']));
  if(!r['Nome do Arquivo']){skipped++;continue;}
  const rawSize=r['Tamanho do Download (KB)'],size=Number(rawSize),hour=Number(r['Horário Sinótico']);
  let date=observationDate(r['Data da Observação']),inferred=false;
  if(!date&&observationDate(r['Data do Download'])&&r['Horário Sinótico']!==''&&[0,6,12,18].includes(hour)){
   date=r['Data do Download'].slice(0,10)+` ${String(hour).padStart(2,'0')}:00:00`;inferred=true;
  }
  if(!date||!rawSize||!Number.isFinite(size)||size<0){skipped++;continue;}
  data.push({date,download:r['Data do Download'],timezone:r['Fuso Horário'],file:r['Nome do Arquivo'],type:r['Tipo de Observação'],fileType:r['Tipo de Arquivo'],hour:Number(date.slice(11,13)),size,inferred,originalDate:r['Data da Observação']});
 }
 return {data:data.sort((a,b)=>b.date.localeCompare(a.date)),skipped};
}
function checkboxes(id,values){$(id).replaceChildren(...values.map(v=>{const label=document.createElement('label'),input=document.createElement('input');input.type='checkbox';input.value=v;input.checked=true;input.addEventListener('change',filterObservations);label.append(input,document.createTextNode(v));return label;}));}
async function loadObservations(){
 const ticket=++revision;obsData=[];obsFiltered=[];$('obs-table').replaceChildren();$('obs-total').textContent='';$('obs-meta').textContent='';$('obs-page').textContent='';$('obs-prev').disabled=true;$('obs-next').disabled=true;$('obs-download').disabled=true;
 $('obs-controls').querySelectorAll('input,select').forEach(x=>x.disabled=true);notice('Carregando inventário de observações…');
 try{
  const source=`obsm/${inventoryKey()}/mon_rec_obs_final.csv`;$('obs-source').href=BASE+source;
  const {text}=await resource(source);
  if(ticket!==revision)return;
  const {data,skipped}=normalizeObservations(text);obsData=data;
  if(!data.length){notice('Nenhum registro válido disponível no inventário.');return;}
  const dates=data.map(r=>r.date.slice(0,10)).sort();
  $('obs-start').value=dates[0];$('obs-end').value=dates.at(-1);
  for(const id of ['obs-start','obs-end']){$(id).min=dates[0];$(id).max=dates.at(-1);}
  checkboxes('obs-types',[...new Set(data.map(r=>r.type))].sort());checkboxes('obs-files',[...new Set(data.map(r=>r.fileType))].sort());
  $('obs-controls').querySelectorAll('input,select').forEach(x=>x.disabled=false);
  $('obs').dataset.skipped=String(skipped);filterObservations();
 }catch(e){if(ticket===revision)notice('Não foi possível carregar o inventário deste ambiente.',true);}
}
function filterObservations(){
 const start=$('obs-start').value,end=$('obs-end').value;
 const types=[...$('obs-types').querySelectorAll('input:checked')].map(x=>x.value),files=[...$('obs-files').querySelectorAll('input:checked')].map(x=>x.value);
 const hours=$('obs-hour').value==='all'?null:$('obs-hour').value.split(',').map(Number);
 obsFiltered=obsData.filter(r=>r.date.slice(0,10)>=start&&r.date.slice(0,10)<=end&&types.includes(r.type)&&files.includes(r.fileType)&&(!hours||hours.includes(r.hour)));obsPage=0;
 drawObservations();
 notice(!start||!end||start>end?'Informe um período válido.':`${obsFiltered.length.toLocaleString('pt-BR')} registros no período selecionado.`,!start||!end||start>end);
}
function obsFactor(){return 1024**['Bytes','KiB','MiB','GiB','TiB'].indexOf($('obs-unit').value);}
function observationHeaders(){return ['Data da observação · UTC','Origem da data','Tipo de observação','Tipo de arquivo',`Tamanho (${$('obs-unit').value})`,'Nome do arquivo','Data do download','Fuso do download','Data da observação na origem'];}
function observationCells(r){return [r.date,r.inferred?'Reconstruída':'Original',r.type,r.fileType,(r.size/obsFactor()).toFixed(6),r.file,r.download,r.timezone,r.originalDate];}
function drawObservations(){
 const total=obsFiltered.reduce((s,r)=>s+r.size,0),inferred=obsFiltered.filter(r=>r.inferred).length;
 $('obs-total').textContent=`Soma dos registros: ${(total/obsFactor()).toLocaleString('pt-BR',{maximumFractionDigits:3})} ${$('obs-unit').value}`;
 $('obs-meta').textContent=`${inferred.toLocaleString('pt-BR')} datas reconstruídas nesta seleção. ${$('obs').dataset.skipped||0} registros inválidos ignorados na origem. Registros repetidos são preservados.`;
 const table=$('obs-table'),head=document.createElement('thead'),hr=document.createElement('tr');
 observationHeaders().forEach(h=>{const th=document.createElement('th');th.scope='col';th.textContent=h;hr.append(th);});head.append(hr);
 const body=document.createElement('tbody');
 for(const r of obsFiltered.slice(obsPage*PAGE_SIZE,(obsPage+1)*PAGE_SIZE)){const tr=document.createElement('tr');observationCells(r).forEach(value=>{const td=document.createElement('td');td.textContent=value;tr.append(td);});body.append(tr);}
 table.replaceChildren(head,body);
 const pages=Math.ceil(obsFiltered.length/PAGE_SIZE);$('obs-page').textContent=pages?`Página ${obsPage+1} de ${pages} · até ${PAGE_SIZE} registros`:'Nenhum registro';$('obs-prev').disabled=obsPage===0;$('obs-next').disabled=obsPage+1>=pages;$('obs-download').disabled=!obsFiltered.length;
}
function observationCSV(){return [observationHeaders(),...obsFiltered.map(observationCells)].map(row=>row.map(x=>'"'+String(x).replaceAll('"','""')+'"').join(',')).join('\r\n');}
function update(){
 $('env-label').textContent=view==='maps'?'SMNA-FNCEP':$('environment').selectedOptions[0].text;
 if(view==='gsi'){++revision;notice('');window.loadGSIDiagnostics();}else if(view==='maps')loadMaps();else if(view==='status')loadStatus();else if(view==='logs')loadLogs();else if(view==='obs')loadObservations();else {++revision;notice('');}
}
function switchView(next){
 view=next;
 for(const name of ['maps','status','logs','obs','gsi','about']){
  $(name).hidden=next!==name;
  if(next===name)$('tab-'+name).setAttribute('aria-current','page');else $('tab-'+name).removeAttribute('aria-current');
 }
 $('map-controls').hidden=next!=='maps';$('log-controls').hidden=next!=='logs';$('obs-controls').hidden=next!=='obs';$('gsi-controls').hidden=next!=='gsi';
 document.querySelector('.parameters').hidden=next==='about';$('environment').hidden=next==='maps';document.querySelector('label[for="environment"]').hidden=next==='maps';$('refresh').hidden=false;$('env-label').hidden=next==='about';
 const titles={gsi:['Diagnósticos GSI','Minimização, observações e desempenho por ciclo de análise.'],maps:['Campos Meteorológicos','Campos meteorológicos do SMNA no SMNA-FNCEP.'],status:['Status Operacional','Acompanhamento das etapas GSI, PRE, MODEL e POS.'],logs:['Logs Completos','Logs completos das etapas de execução.'],obs:['Inventário Observações','Inventário dos arquivos de observações.'],about:['Sobre','Sistema de Monitoramento da Assimilação de Dados · CPTEC/INPE']};
 document.querySelector('.source').hidden=next==='gsi';$('title').textContent=titles[next][0];$('subtitle').textContent=titles[next][1];update();
}
$('tab-maps').addEventListener('click',()=>switchView('maps'));
$('tab-status').addEventListener('click',()=>switchView('status'));
for(const name of ['logs','obs','gsi','about'])$('tab-'+name).addEventListener('click',()=>switchView(name));
$('log-date').addEventListener('change',selectLog);$('log-file').addEventListener('change',loadLogFile);
document.querySelectorAll('[data-stage]').forEach(button=>button.addEventListener('click',()=>{logStage=button.dataset.stage;document.querySelectorAll('[data-stage]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));selectLog();}));
for(const id of ['obs-start','obs-end','obs-hour','obs-unit'])$(id).addEventListener('change',filterObservations);
$('obs-prev').addEventListener('click',()=>{if(obsPage>0){obsPage--;drawObservations();}});
$('obs-next').addEventListener('click',()=>{if((obsPage+1)*PAGE_SIZE<obsFiltered.length){obsPage++;drawObservations();}});
$('obs-download').addEventListener('click',()=>fileDownload(observationCSV(),`obs_storage_${$('environment').value}.csv`));
$('environment').addEventListener('change',update);
selectors.forEach((id,i)=>$(id).addEventListener('change',()=>loadMaps(i===3?3:i+1)));
$('refresh').addEventListener('click',()=>{cache.clear();if(view==='gsi')window.loadGSIDiagnostics(true);else update();});
$('close-viewer').addEventListener('click',()=>$('viewer').close());
window.addEventListener('DOMContentLoaded',()=>{$('environment').value=window.SMNA_CONFIG.defaultEnvironment;if(location.hash==='#gsi')switchView('gsi');else switchView('status');});
