import {DEFAULTS,CONTROLS,validState,parseInput} from './state.mjs';
import {CHARTS,buildCurves,domains,tangentLine} from './curves.mjs';
import {marketUnits} from './engine.mjs';
import {formatNumber,GREEK_NAMES} from './format.mjs';

// Streamlit v2 component: DOM instances survive every live update. No callbacks
// to Python; sessionStorage retains this tab's scenario across component mounts.
export default function mount({parentElement,data}) {
  const root=parentElement.querySelector('.lab'), text=data.copy;
  for (const [key,value] of Object.entries(data.tokens)) root.style.setProperty('--'+key.replaceAll('_','-'),value);
  root.style.colorScheme=data.theme;
  root.lang=data.language;
  const fmt=(v,d=4)=>formatNumber(v,d,data.language);
  const storageKey='mat.interactive-greeks.v1';
  let state={...DEFAULTS};
  try {const saved=JSON.parse(sessionStorage.getItem(storageKey));if(validState(saved)) state=saved;} catch { /* storage may be disabled */ }
  let ranges=domains(state), yRanges=[], frame=0, dragging=false, frames=0, dragFrames=0, inputEvents=0;
  let curveClipped=false;
  const frameCosts=[];
  const ns='http://www.w3.org/2000/svg';
  const el=(tag,cls,content,parent=root)=>{
    const node=document.createElement(tag);if(cls)node.className=cls;
    if(content!=null)node.textContent=content;if(parent)parent.append(node);return node;
  };
  const svgEl=(tag,attrs,parent)=>{
    const node=document.createElementNS(ns,tag);
    for(const [k,v] of Object.entries(attrs))node.setAttribute(k,String(v));
    parent.append(node);return node;
  };
  root.replaceChildren();
  const heading=el('div','heading',null), titles=el('div','',null,heading);
  el('p','eyebrow',text.source,titles);el('h2','',text.title,titles);el('p','intro',text.intro,titles);
  const actions=el('div','actions',null,heading);
  const reset=el('button','',text.reset,actions), fit=el('button','',text.fit,actions);
  reset.type=fit.type='button';
  const controlBar=el('div','controls',null), widgets={};
  const error=el('p','error','');error.id='lab-input-error';error.setAttribute('role','status');
  for (const control of CONTROLS) {
    const key=control.key, box=el('div','control',null,controlBar), top=el('div','control-top',null,box);
    const label=el('label','',text[key],top);label.htmlFor='lab-range-'+key;
    const output=el('output','',null,top);output.setAttribute('for','lab-range-'+key+' lab-number-'+key);
    const slider=el('input','',null,box);slider.type='range';slider.id='lab-range-'+key;
    slider.setAttribute('aria-label',text[key]+' · '+text.slider);
    const entry=el('div','entry',null,box), number=el('input','',null,entry);
    number.type='number';number.id='lab-number-'+key;
    number.setAttribute('aria-label',text[key]+' · '+text.number);
    number.setAttribute('aria-describedby',error.id);
    for(const node of [slider,number]) {
      node.min=control.min;node.max=control.max;node.step=control.step;
      node.value=state[key]*control.scale;
    }
    el('span','bounds',fmt(control.min,2)+' → '+fmt(control.max,2),entry);
    widgets[key]={slider,number,output,control};
    const input=e=>{
      inputEvents++;
      const value=parseInput(control,e.target.value);
      number.setAttribute('aria-invalid',value===null?'true':'false');
      error.textContent=value===null?text.invalid:'';
      if(value===null)return;
      state={...state,[key]:value};
      if(e.target===number)yRanges=[];
      // Synchronize controls immediately; all financial values/paths share one RAF.
      slider.value=value*control.scale;
      if(e.target!==number)number.value=value*control.scale;
      schedule();
    };
    slider.addEventListener('input',input);number.addEventListener('input',input);
    slider.addEventListener('pointerdown',()=>{dragging=true;});
    number.addEventListener('blur',()=>{
      if(parseInput(control,number.value)===null){number.value=state[key]*control.scale;number.setAttribute('aria-invalid','false');error.textContent='';}
    });
  }
  const pricing=el('div','pricing',null), prices=el('div','prices',null,pricing), priceOutputs={};
  for(const side of ['call','put']) {
    const block=el('div','price',null,prices);el('label','',text[side+'_value'],block);
    priceOutputs[side]=el('output','',null,block);priceOutputs[side].dataset.metric=side+'-price';
  }
  const formulas=el('div','formulas',null,pricing);
  // Static mathematical markup is ours, not input-dependent HTML. Native MathML
  // avoids remote font/math dependencies while preserving accessible notation.
  formulas.innerHTML=`<div class="math">C = S e<sup>−qT</sup> N(d₁) − K e<sup>−rT</sup> N(d₂)</div>
    <div class="math">P = K e<sup>−rT</sup> N(−d₂) − S e<sup>−qT</sup> N(−d₁)</div>
    <div class="math"><math><mrow><msub><mi>d</mi><mn>1</mn></msub><mo>=</mo><mfrac><mrow><mi>ln</mi><mo>(</mo><mi>S</mi><mo>/</mo><mi>K</mi><mo>)</mo><mo>+</mo><mo>(</mo><mi>r</mi><mo>−</mo><mi>q</mi><mo>+</mo><msup><mi>σ</mi><mn>2</mn></msup><mo>/</mo><mn>2</mn><mo>)</mo><mi>T</mi></mrow><mrow><mi>σ</mi><msqrt><mi>T</mi></msqrt></mrow></mfrac></mrow></math> &nbsp; d₂ = d₁ − σ√T</div>`;
  const ds=el('div','d-values',null,formulas), dOutputs={};
  for(const [key,label] of [['d1','d₁'],['d2','d₂'],['nd1','N(d₁)'],['nd2','N(d₂)']]) {
    const wrap=el('span','',label+' = ',ds);dOutputs[key]=el('output','',null,wrap);
  }
  el('p','muted',text.distribution+' · '+text.value_unit,formulas);
  el('p','muted',text.origin);
  const legend=el('div','legend',null);
  for(const key of ['curve','tangent','point']){const item=el('span','',null,legend);el('i','swatch '+key,null,item);el('span','',text[key],item);}
  el('p','muted',text.time);
  const charts=[];
  for(const side of ['call','put']) {
    const section=el('section','side',null);el('h3','',text[side],section);
    for(let order=0;order<2;order++){
      el('p','order',text[order?'second':'first'],section);
      const grid=el('div','matrix',null,section);
      for(let j=0;j<5;j++){
        const index=charts.length, spec=CHARTS[order*5+j];
        const card=el('article','chart',null,grid);card.dataset.chart=side+'-'+spec.greek;
        el('h4','',text[spec.y]+' / '+text['axis_'+spec.x],card);
        const line=el('div','greek-line',null,card);
        const name=el('button','greek-name',GREEK_NAMES[spec.greek]+' ⓘ',line);name.type='button';
        const value=el('output','greek-value',null,line);
        const tip=el('div','tooltip',text['help_'+spec.greek],card);tip.hidden=true;tip.id='lab-help-'+index;tip.setAttribute('role','tooltip');
        name.setAttribute('aria-describedby',tip.id);name.setAttribute('aria-expanded','false');
        const show=visible=>{tip.hidden=!visible;name.setAttribute('aria-expanded',String(visible));};
        name.addEventListener('mouseenter',()=>show(true));name.addEventListener('mouseleave',()=>show(false));
        name.addEventListener('focus',()=>show(true));name.addEventListener('blur',()=>show(false));
        name.addEventListener('click',()=>show(tip.hidden));name.addEventListener('keydown',e=>{if(e.key==='Escape')show(false);});
        const slope=el('p','slope','',card);
        const svg=svgEl('svg',{viewBox:'0 0 300 202',role:'img'},card);
        const title=svgEl('title',{},svg);
        const defs=svgEl('defs',{},svg), clip=svgEl('clipPath',{id:'lab-clip-'+index},defs);
        svgEl('rect',{x:49,y:14,width:237,height:148},clip);
        const yTicks=[],xTicks=[];
        for(let i=0;i<3;i++){
          const y=14+74*i;
          svgEl('line',{x1:49,y1:y,x2:286,y2:y,class:'grid'},svg);
          yTicks.push(svgEl('text',{x:44,y:y+4,'text-anchor':'end'},svg));
          xTicks.push(svgEl('text',{x:49+118.5*i,y:180,'text-anchor':i===0?'start':i===2?'end':'middle'},svg));
        }
        svgEl('line',{x1:49,y1:14,x2:49,y2:162,class:'axis'},svg);
        const clipped=svgEl('g',{'clip-path':'url(#lab-clip-'+index+')'},svg);
        const path=svgEl('path',{class:'curve'},clipped);
        const tangent=svgEl('line',{class:'tangent-line'},clipped);
        const point=svgEl('circle',{class:'current-point',r:4.5},clipped);
        const note=el('p','clipped','',card);
        charts.push({card,spec,value,slope,path,tangent,point,title,xTicks,yTicks,note});
      }
    }
  }
  const help=el('details','help',null);el('summary','',text.help,help);
  for(const key of ['read','units','time','axes','assumptions'])el('p','',text[key],help);
  el('strong','',text.market,help);
  const market=el('div','market-values',null,help), marketOutputs={};
  for(const side of ['call','put']) {
    const block=el('div','',null,market);el('strong','',text[side+'_value'],block);
    const dl=el('dl','',null,block);marketOutputs[side]={};
    for(const [key,label] of [['vega_1pct','per_vol'],['rho_1bp','per_bp'],['theta_daily','per_day']]) {
      el('dt','',text[label],dl);marketOutputs[side][key]=el('dd','',null,dl);
    }
  }
  el('p','footer',text.live+' · '+text.axes);

  function schedule(){if(!frame)frame=requestAnimationFrame(paint);}
  function fitAll(){ranges=domains(state);yRanges=[];schedule();}
  reset.addEventListener('click',()=>{
    state={...DEFAULTS};error.textContent='';
    for(const {slider,number,control} of Object.values(widgets)){
      slider.value=number.value=state[control.key]*control.scale;number.setAttribute('aria-invalid','false');
    }
    fitAll();
  });
  fit.addEventListener('click',fitAll);
  const pointerUp=()=>{
    if(dragging && curveClipped){yRanges=[];schedule();}
    dragging=false;
  };
  window.addEventListener('pointerup',pointerUp);window.addEventListener('pointercancel',pointerUp);

  function paint(){
    frame=0;const started=performance.now();
    // Expand only at an actual boundary crossing, with a generous margin.
    for(const key of Object.keys(ranges)){
      const [lo,hi]=ranges[key],at=state[key],span=hi-lo;
      if(at<lo || at>hi){ranges[key]=[key==='r'?Math.min(lo,at-span*.5):Math.max(.001,Math.min(lo,at-span*.5)),Math.max(hi,at+span*.5)];yRanges=[];}
    }
    const result=buildCurves(state,ranges);
    for(const {output,control} of Object.values(widgets))output.textContent=fmt(state[control.key]*control.scale,2);
    for(const side of ['call','put']) {
      priceOutputs[side].textContent=fmt(result.current[side].price);
      const values=marketUnits(result.current[side]);
      for(const [key,node] of Object.entries(marketOutputs[side]))node.textContent=fmt(values[key],6);
    }
    for(const [key,node] of Object.entries(dOutputs))node.textContent=fmt(result.current[key]);
    curveClipped=false;
    result.charts.forEach((chart,i)=>{
      const view=charts[i], [x0,y0]=chart.current, [xmin,xmax]=ranges[chart.x];
      const ys=chart.points.map(p=>p[1]), low=Math.min(...ys),high=Math.max(...ys);
      if(!yRanges[i]){
        const margin=Math.max((high-low)*.12,Math.abs(y0)*.05,1e-8);
        yRanges[i]=[low-margin,high+margin];
      } else if(y0<yRanges[i][0] || y0>yRanges[i][1]){
        const [a,b]=yRanges[i],span=Math.max(b-a,Math.abs(y0)*.5,1e-8);
        yRanges[i]=[Math.min(a,y0-span*.5),Math.max(b,y0+span*.5)];
      }
      const [ymin,ymax]=yRanges[i], X=x=>49+237*(x-xmin)/(xmax-xmin), Y=y=>162-148*(y-ymin)/(ymax-ymin);
      view.value.textContent=fmt(chart.greekValue);
      view.slope.textContent=text.slope+' = '+(chart.sign===-1?'−'+GREEK_NAMES[chart.greek]+' = ':'')+fmt(chart.slope);
      // Reuse all SVG nodes; updating attributes is cheaper than twenty plot lifecycles.
      view.path.setAttribute('d',chart.points.map(([x,y],n)=>(n?'L':'M')+X(x).toFixed(2)+','+Y(y).toFixed(2)).join(' '));
      const half=(xmax-xmin)*.18;
      for(const [key,value] of Object.entries({x1:X(x0-half),y1:Y(tangentLine(x0,y0,chart.slope,x0-half)),x2:X(x0+half),y2:Y(tangentLine(x0,y0,chart.slope,x0+half))}))view.tangent.setAttribute(key,value);
      view.point.setAttribute('cx',X(x0));view.point.setAttribute('cy',Y(y0));
      view.title.textContent=text[chart.side]+' · '+text[chart.y]+' '+fmt(y0)+' · '+text['axis_'+chart.x]+' '+fmt(x0)+' · '+text.slope+' '+fmt(chart.slope);
      for(let tick=0;tick<3;tick++){
        view.xTicks[tick].textContent=fmt(xmin+(xmax-xmin)*tick/2,2);
        view.yTicks[tick].textContent=fmt(ymax-(ymax-ymin)*tick/2,2);
      }
      const clipped=low<ymin || high>ymax;
      curveClipped ||= clipped;
      view.note.textContent=clipped ? text.clipped : '';
    });
    try {sessionStorage.setItem(storageKey,JSON.stringify(state));} catch { /* live use does not require storage */ }
    frames++;if(dragging)dragFrames++;
    if(dragging)root.dataset.dragSnapshot=JSON.stringify({sigma:state.sigma,...result.current.call});
    frameCosts.push(performance.now()-started);if(frameCosts.length>120)frameCosts.shift();
    const sorted=[...frameCosts].sort((a,b)=>a-b);
    // DOM diagnostics for acceptance tests, no telemetry or network transmission.
    Object.assign(root.dataset,{frames:String(frames),dragFrames:String(dragFrames),inputEvents:String(inputEvents),
      renderMs:frameCosts.at(-1).toFixed(2),p95Ms:sorted[Math.floor((sorted.length-1)*.95)].toFixed(2),state:JSON.stringify(state)});
  }
  paint();
  return ()=>{cancelAnimationFrame(frame);window.removeEventListener('pointerup',pointerUp);window.removeEventListener('pointercancel',pointerUp);};
}
