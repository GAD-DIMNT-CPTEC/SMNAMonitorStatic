/* Apply before styles render to avoid a light flash on reload. */
(()=>{
 const key='smna-theme',root=document.documentElement;
 const system=window.matchMedia('(prefers-color-scheme: dark)');
 let preference=null;
 try{const stored=localStorage.getItem(key);if(stored==='dark'||stored==='light')preference=stored;}catch{}
 function apply(theme){
  root.dataset.theme=theme;
  const toggle=document.getElementById('theme-toggle');
  if(toggle)toggle.setAttribute('aria-checked',String(theme==='dark'));
 }
 apply(preference|| (system.matches?'dark':'light'));
 document.addEventListener('DOMContentLoaded',()=>{
  const toggle=document.getElementById('theme-toggle');
  if(!toggle)return;
  apply(root.dataset.theme);
  toggle.addEventListener('click',()=>{
   preference=root.dataset.theme==='dark'?'light':'dark';
   apply(preference);
   try{localStorage.setItem(key,preference);}catch{}
  });
 });
 system.addEventListener('change',event=>{if(!preference)apply(event.matches?'dark':'light');});
})();
