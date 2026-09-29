import assert from 'node:assert/strict';
import render from '../../components/monitor/ticker.mjs';

class Element {
 constructor(){this.children=[];this.dataset={};this.style={};this.attributes={};}
 append(...children){this.children.push(...children);}
 replaceChildren(...children){this.children=children;}
 setAttribute(k,v){this.attributes[k]=v;}
 querySelector(selector){return selector==='.ticker'?this:this.children.find(c=>c.className==='strip');}
}
globalThis.document={createElement:()=>new Element()};
const root=new Element();
const tokens={};let clicked;
const data={tokens,items:[{id:'SPX',name:'S&P 500',level:'—',move:'—',detail:'Loading',sign:''}]};
render({data,parentElement:root,setTriggerValue:(_,id)=>clicked=id});
const strip=root.children[0],button=strip.children[0].children[0];
render({data:{...data,items:[{...data.items[0],level:'100',move:'+1%',detail:'Dated public observation',sign:'positive'}]},parentElement:root,setTriggerValue:(_,id)=>clicked=id});
assert.equal(root.children[0],strip);
assert.equal(strip.children[0].children[0],button);
assert.equal(button.children[1].textContent,'100');
assert.equal(button.attributes['aria-label'],'Dated public observation');
assert.equal(strip.children[1].attributes['aria-hidden'],'true');
assert.equal(strip.children[1].children[0].tabIndex,-1);
button.onclick();assert.equal(clicked,'SPX');
