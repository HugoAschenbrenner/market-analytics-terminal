import test from 'node:test';
import assert from 'node:assert/strict';
import {DEFAULTS,CONTROLS,validState,parseInput} from '../../components/greeks_lab/state.mjs';
import {evaluateBSM,marketUnits} from '../../components/greeks_lab/engine.mjs';
import {domains,buildCurves,tangentLine} from '../../components/greeks_lab/curves.mjs';
import {formatNumber} from '../../components/greeks_lab/format.mjs';

test('numeric editing rejects incomplete, nonfinite and out-of-range values',()=>{
  for(const c of CONTROLS){
    assert.equal(parseInput(c,''),null);assert.equal(parseInput(c,'NaN'),null);
    assert.equal(parseInput(c,'Infinity'),null);assert.equal(parseInput(c,String(c.min-.1)),null);
    assert.equal(parseInput(c,String(c.max+.1)),null);
    assert.equal(parseInput(c,String(c.min)),c.min/c.scale);
    assert.equal(parseInput(c,String(c.max)),c.max/c.scale);
  }
  assert.equal(validState(DEFAULTS),true);
  assert.equal(validState({...DEFAULTS,T:0}),false);
  assert.equal(validState({...DEFAULTS,q:Infinity}),false);
  assert.equal(validState({...DEFAULTS,sigma:.25,r:-.05}),true);
});

test('raw units and elapsed time remain explicit',()=>{
  const raw=evaluateBSM(DEFAULTS).call,m=marketUnits(raw);
  assert.equal(m.vega_1pct,raw.vega*.01);assert.equal(m.rho_1bp,raw.rho*.0001);
  assert.equal(m.theta_daily,raw.theta/365);assert.throws(()=>marketUnits(raw,360));
  assert.equal(tangentLine(3,8,-2,3),8);assert.equal(tangentLine(3,8,-2,4),6);
  assert.throws(()=>evaluateBSM({...DEFAULTS,T:0}));
  assert.throws(()=>evaluateBSM({...DEFAULTS,sigma:NaN}));
});

test('all extreme UI scenarios produce finite curves and tangents',()=>{
  for(const p of [DEFAULTS,{S:1,K:250,T:.01,sigma:.01,r:-.05,q:.2},
    {S:250,K:1,T:10,sigma:1.5,r:.2,q:0},{S:100,K:100,T:.01,sigma:.01,r:0,q:0}]){
    const r=buildCurves(p,domains(p));
    for(const chart of r.charts){
      assert.equal(chart.points.every(point=>point.every(Number.isFinite)),true);
      assert.equal(Number.isFinite(chart.slope),true);
      assert.ok(chart.points.length<=150);
    }
  }
});

test('formatting preserves small risks and never prints nonfinite values',()=>{
  assert.equal(formatNumber(NaN),'—');assert.equal(formatNumber(Infinity),'—');
  assert.equal(formatNumber(-0),'0');assert.match(formatNumber(1e-12),/E-12/);
  assert.match(formatNumber(.25,4,'fr'),/0,25/);
});
