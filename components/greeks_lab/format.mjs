export const GREEK_NAMES = Object.freeze({delta:'Delta',dual_delta:'Dual Delta',theta:'Theta',
  vega:'Vega',rho:'Rho',gamma:'Gamma',vanna:'Vanna',charm:'Charm',vomma:'Vomma / Volga',veta:'Veta'});
const formatters=new Map();
export function formatNumber(value, digits=4, language='en') {
  if (!Number.isFinite(value)) return '—';
  if (value === 0 || Object.is(value,-0)) return '0';
  const tiny=Math.abs(value)<10**(-digits);
  const scientific=tiny || Math.abs(value)>=1e6, key=language+':'+digits+':'+scientific;
  if(!formatters.has(key))formatters.set(key,new Intl.NumberFormat(language==='fr'?'fr-FR':'en-GB',scientific
    ? {notation:'scientific',maximumFractionDigits:2}
    : {minimumFractionDigits:0,maximumFractionDigits:digits}));
  return formatters.get(key).format(value);
}
