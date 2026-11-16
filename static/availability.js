/* Explain delays from the external data server without blocking the page. */
(()=>{
 const pending=new Set(),images=new Set(),watchers=new WeakMap();let failed=false;
 const box=()=>document.getElementById('data-server-notice');
 function render(){box().hidden=!(failed||[...pending].some(task=>task.slow));}
 function reset(){for(const cleanup of images)cleanup(false);for(const task of pending)task.cancel();pending.clear();failed=false;render();}
 function begin(url){
  if(new URL(url,location.href).hostname!=='dataserver.cptec.inpe.br')return ()=>{};
  const task={slow:false,cancel:()=>clearTimeout(timer)};
  const timer=setTimeout(()=>{task.slow=true;render();},8000);pending.add(task);
  return error=>{if(!pending.delete(task))return;task.cancel();if(error)failed=true;render();};
 }
 async function request(url,options,consume){const done=begin(url);try{const r=await fetch(url,options);if(!r.ok){const error=Error(`Servidor respondeu HTTP ${r.status}.`);error.status=r.status;throw error;}const result=await consume(r);done();return result;}catch(e){done(true);throw e;}}
 function image(img,url){
  watchers.get(img)?.(false);
  let done=()=>{},observer;
  const cleanup=error=>{images.delete(cleanup);watchers.delete(img);observer?.disconnect();done(error);img.removeEventListener('load',loaded);img.removeEventListener('error',errorHandler);};
  const loaded=()=>cleanup(false),errorHandler=()=>cleanup(true);
  images.add(cleanup);watchers.set(img,cleanup);
  img.addEventListener('load',loaded);img.addEventListener('error',errorHandler);
  // Lazy images are only expected to load as they approach the viewport.
  if(img.loading==='lazy'&&'IntersectionObserver' in window){observer=new IntersectionObserver(entries=>{if(entries.some(e=>e.isIntersecting)){observer.disconnect();if(!img.complete||!img.naturalWidth)done=begin(url);}}, {rootMargin:'300px'});observer.observe(img);}
  else done=begin(url);
  img.src=url;return cleanup;
 }
 window.SMNAAvailability={begin,request,image,reset};
})();
