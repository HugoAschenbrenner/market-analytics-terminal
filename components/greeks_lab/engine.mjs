// Browser port of engines/options_pricing_engine.py, checked against Python.
// No DOM, chart or market-data dependency. Inputs: decimals and remaining years.
export function normalCDF(x) {
  if (Number.isNaN(x)) throw new RangeError('Normal argument must be a number');
  if (x === 0) return 0.5;
  if (Math.abs(x) > 38.5) return x < 0 ? 0 : 1; // IEEE-754 tail underflow
  const z = x*x/2;
  const factor = Math.exp(-z + 0.5*Math.log(z) - 0.5*Math.log(Math.PI));
  let tail;
  if (z < 1.5) {
    // Regularized lower gamma, a=1/2; DLMF 8.7.1.
    let term = 2, sum = term;
    for (let n = 1; n <= 200; n++) {
      term *= z/(n+0.5); sum += term;
      if (Math.abs(term) < Math.abs(sum)*2e-16) break;
    }
    tail = 0.5*(1-factor*sum);
  } else {
    // Upper gamma continued fraction (DLMF 8.9), modified Lentz evaluation.
    let b = z+0.5, c = 1e300, d = 1/b, h = d;
    for (let n = 1; n <= 200; n++) {
      const a = -n*(n-0.5);
      b += 2; d = a*d+b; c = b+a/c;
      if (Math.abs(d) < 1e-300) d = 1e-300;
      if (Math.abs(c) < 1e-300) c = 1e-300;
      d = 1/d; const step = c*d; h *= step;
      if (Math.abs(step-1) < 4e-16) break;
    }
    tail = 0.5*factor*h;
  }
  return x < 0 ? tail : 1-tail;
}

export const normalPDF = x => Math.exp(-x*x/2)/Math.sqrt(2*Math.PI);

export function validateInputs(p) {
  if (!['S','K','T','sigma','r','q'].every(k => Number.isFinite(p[k])) ||
      p.S <= 0 || p.K <= 0 || p.T <= 0 || p.sigma <= 0) {
    throw new RangeError('Finite inputs and positive S, K, T, sigma are required');
  }
}

export function evaluateBSM(p) {
  validateInputs(p);
  const {S,K,T,sigma:v,r,q} = p, root = Math.sqrt(T);
  const d1 = (Math.log(S/K)+(r-q+v*v/2)*T)/(v*root), d2 = d1-v*root;
  const dq = Math.exp(-q*T), dr = Math.exp(-r*T), density = dq*normalPDF(d1);
  const vega = S*density*root, d1dT = (2*(r-q)*T-d2*v*root)/(2*T*v*root);
  const common = {gamma:density/(S*v*root), vega, vanna:-density*d2/v,
    vomma:vega*d1*d2/v, veta:vega*(q+d1*d1dT-1/(2*T))};
  const side = sign => {
    const n1 = normalCDF(sign*d1), n2 = normalCDF(sign*d2), delta = sign*dq*n1;
    return {...common, price:sign*(S*dq*n1-K*dr*n2), delta,
      theta:-S*density*v/(2*root)-sign*r*K*dr*n2+q*S*delta,
      rho:sign*K*T*dr*n2, dual_delta:-sign*dr*n2, charm:q*delta-density*d1dT};
  };
  return {d1,d2,nd1:normalCDF(d1),nd2:normalCDF(d2),call:side(1),put:side(-1)};
}

export function marketUnits(raw, daysPerYear=365) {
  if (![252,365].includes(daysPerYear)) throw new RangeError('Use 252 or 365 days');
  return {vega_1pct:raw.vega*.01, rho_1bp:raw.rho*.0001,
    theta_annual:raw.theta, theta_daily:raw.theta/daysPerYear};
}
