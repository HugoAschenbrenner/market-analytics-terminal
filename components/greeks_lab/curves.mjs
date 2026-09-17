import {evaluateBSM} from './engine.mjs';

// Exact reference matrix, repeated for call and put. Time charts plot remaining T.
export const CHARTS = Object.freeze([
  {x:'S',y:'price',greek:'delta'}, {x:'K',y:'price',greek:'dual_delta'},
  {x:'T',y:'price',greek:'theta',sign:-1}, {x:'sigma',y:'price',greek:'vega'},
  {x:'r',y:'price',greek:'rho'}, {x:'S',y:'delta',greek:'gamma'},
  {x:'sigma',y:'delta',greek:'vanna'}, {x:'T',y:'delta',greek:'charm',sign:-1},
  {x:'sigma',y:'vega',greek:'vomma'}, {x:'T',y:'vega',greek:'veta',sign:-1},
]);

export function domains(p) {
  return {S:[Math.max(.01,p.S*.3),p.S*1.7],
    K:[Math.max(.01,Math.min(p.S,p.K)*.3),Math.max(p.S,p.K)*1.7],
    T:[Math.max(.001,p.T*.05),p.T*2],
    sigma:[Math.max(.001,p.sigma*.1),Math.max(.1,p.sigma*2)],
    r:[Math.min(-.05,p.r-.08),Math.max(.1,p.r+.08)]};
}

export function tangentLine(x0,y0,slope,x) { return y0+slope*(x-x0); }

export function buildCurves(p, ranges, samples=101) {
  if (!Number.isInteger(samples) || samples < 3) throw new RangeError('Need at least 3 samples');
  const current = evaluateBSM(p), grids = {};
  // Reuse the five sampled states across both sides and all Greek plots.
  for (const x of ['S','K','T','sigma','r']) {
    const [lo,hi] = ranges[x];
    const xs = Array.from({length:samples},(_,i) => lo+(hi-lo)*i/(samples-1));
    // Resolve steep near-expiry transitions without exceeding 150 samples.
    const transition = x==='S' ? p.K*Math.exp(-(p.r-p.q)*p.T) :
      x==='K' ? p.S*Math.exp((p.r-p.q)*p.T) : null;
    if (transition) {
      const width = transition*p.sigma*Math.sqrt(p.T);
      for (let i=-12;i<=12;i++) {
        const at=transition+i*width/4;
        if (at>lo && at<hi) xs.push(at);
      }
    }
    xs.push(p[x]); xs.sort((a,b)=>a-b);
    grids[x] = xs.map(at => ({x:at,values:evaluateBSM({...p,[x]:at})}));
  }
  const charts = ['call','put'].flatMap(side => CHARTS.map(spec => ({
    ...spec,side,points:grids[spec.x].map(at=>[at.x,at.values[side][spec.y]]),
    current:[p[spec.x],current[side][spec.y]],
    greekValue:current[side][spec.greek],
    slope:(spec.sign || 1)*current[side][spec.greek],
  })));
  return {current,charts};
}
