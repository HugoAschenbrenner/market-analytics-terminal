import {readFileSync} from 'node:fs';
import {evaluateBSM,normalCDF,marketUnits} from '../../components/greeks_lab/engine.mjs';
import {buildCurves,domains} from '../../components/greeks_lab/curves.mjs';
const request=JSON.parse(readFileSync(0,'utf8'));
const result=request.mode==='cdf' ? request.values.map(normalCDF) :
  request.mode==='curves' ? buildCurves(request.state,domains(request.state)) :
  request.states.map(p=>{
    const value=evaluateBSM(p);
    return {...value,market:marketUnits(value.call)};
  });
process.stdout.write(JSON.stringify(result));
