export default function({data,parentElement,setTriggerValue}) {
 const root=parentElement.querySelector('.market-table');
 const t=data.tokens;
 root.style.cssText=`--bg:${t.surface};--fg:${t.text_primary};--muted:${t.text_secondary};--line:${t.border};--up:${t.positive};--down:${t.negative};--accent:${t.accent};--hover:${t.surface_secondary}`;
 const table=document.createElement('table');const head=document.createElement('thead');const header=document.createElement('tr');
 for(const title of data.headers){const th=document.createElement('th');th.textContent=title;header.append(th)}head.append(header);table.append(head);
 const body=document.createElement('tbody');
 for(const row of data.rows){
  const tr=document.createElement('tr');
  row.cells.forEach((value,i)=>{const td=document.createElement('td');
   if(i===0){const button=document.createElement('button');button.type='button';button.textContent=value;button.onclick=()=>setTriggerValue('selected',row.id);td.append(button)}
   else if(i===3 && row.spark && row.spark.length>1){
    const ns='http://www.w3.org/2000/svg';const svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 100 24');svg.setAttribute('width','100');svg.setAttribute('height','24');svg.setAttribute('role','img');svg.setAttribute('aria-label',data.sparkLabel);
    const lo=Math.min(...row.spark),hi=Math.max(...row.spark),range=hi-lo||1;
    const path=document.createElementNS(ns,'polyline');path.setAttribute('points',row.spark.map((v,j)=>`${j*98/(row.spark.length-1)+1},${23-(v-lo)*22/range}`).join(' '));path.setAttribute('fill','none');path.setAttribute('stroke','var(--accent)');path.setAttribute('stroke-width','1.4');svg.append(path);td.append(svg);
   }else {td.textContent=value??'—';if(i===2)td.className=row.sign;}
   tr.append(td);
  });body.append(tr);
 }
 table.append(body);root.replaceChildren(table);
}
