export default function({data,parentElement,setTriggerValue,setStateValue}) {
 const root=parentElement.querySelector('.board-storage');
 try {
  if(!data.ready && !root.dataset.loaded){
   root.dataset.loaded='1';let saved=null;
   try {saved=JSON.parse(localStorage.getItem('mat-v2-board-v1'));}catch(_){}
   setTriggerValue('loaded',{ids:Array.isArray(saved)?saved:null});
  } else if(data.ready) {
   const next=JSON.stringify(data.ids);
   if(localStorage.getItem('mat-v2-board-v1')!==next)localStorage.setItem('mat-v2-board-v1',next);
  }
 } catch(_) {if(!root.dataset.error){root.dataset.error='1';setStateValue('error',true);}}
}
