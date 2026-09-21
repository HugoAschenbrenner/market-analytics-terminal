export default function({data,parentElement,setTriggerValue}) {
 const root=parentElement.querySelector('.ticker');
 root.style.cssText=`--bg:${data.tokens.surface};--fg:${data.tokens.text_primary};--muted:${data.tokens.text_secondary};--line:${data.tokens.border};--up:${data.tokens.positive};--down:${data.tokens.negative};--accent:${data.tokens.accent}`;
 const strip=document.createElement('div'); strip.className='strip';
 for(let repeat=0;repeat<2;repeat++){
  const group=document.createElement('div');group.className='group';
  if(repeat)group.setAttribute('aria-hidden','true');
  for(const item of data.items){
   const button=document.createElement('button');button.type='button';button.title=item.detail;button.setAttribute('aria-label',item.detail);
   if(repeat)button.tabIndex=-1;
   const name=document.createElement('b');name.textContent=item.name;
   const level=document.createElement('span');level.textContent=item.level;
   const move=document.createElement('span');move.textContent=item.move;move.className=item.sign;
   button.append(name,level,move);button.onclick=()=>setTriggerValue('clicked',item.id);group.append(button);
  }
  strip.append(group);
 }
 root.replaceChildren(strip);
}
