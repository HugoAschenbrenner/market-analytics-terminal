export const DEFAULTS = Object.freeze({S:100,K:80,T:2,sigma:.25,r:.03,q:0});
// scale converts the canonical decimal into the editable percent display.
export const CONTROLS = Object.freeze([
  {key:'S',min:1,max:250,step:.1,scale:1},
  {key:'K',min:1,max:250,step:.1,scale:1},
  {key:'T',min:.01,max:10,step:.01,scale:1},
  {key:'sigma',min:1,max:150,step:.1,scale:100},
  {key:'r',min:-5,max:20,step:.01,scale:100},
  {key:'q',min:0,max:20,step:.01,scale:100},
]);

export function validState(candidate) {
  return candidate && CONTROLS.every(c => Number.isFinite(candidate[c.key]) &&
    candidate[c.key]*c.scale >= c.min-1e-10 && candidate[c.key]*c.scale <= c.max+1e-10);
}

// Stateless parsing keeps incomplete/invalid text out of the financial engine.
export function parseInput(control, text) {
  if (text.trim() === '') return null;
  const value = Number(text);
  return Number.isFinite(value) && value >= control.min && value <= control.max
    ? value/control.scale : null;
}
