export const damGatePath='M10 22V13H26V22M15 13V22M21 13V22M9 25Q12 22 15 25T21 25T27 25';
export function damStorageSymbol(value:number|null){
  const percent=value!==null&&Number.isFinite(value)&&value>=0?value:null;
  return {percent,fraction:percent===null?null:Math.min(percent,100)/100,
    overNormal:percent!==null&&percent>100,
    label:percent===null?'Percentage unavailable':`${percent.toFixed(2)}% of normal storage capacity`};
}
export function damMarkerSvg(value:number|null){
  const symbol=damStorageSymbol(value),circumference=2*Math.PI*15;
  return `<svg viewBox="0 0 36 36" aria-hidden="true" focusable="false"><circle class="dam-ring-track" cx="18" cy="18" r="15" fill="none"/>
    ${symbol.fraction!==null&&symbol.fraction>0?`<circle class="dam-ring-value" cx="18" cy="18" r="15" fill="none" stroke-dasharray="${circumference}" stroke-dashoffset="${circumference*(1-symbol.fraction)}" transform="rotate(-90 18 18)"/>`:''}
    <path class="dam-gate" d="${damGatePath}" fill="none"/>${symbol.percent===null?'<text class="dam-symbol-badge" x="27" y="12">?</text>':''}${symbol.overNormal?'<text class="dam-symbol-badge" x="27" y="12">+</text>':''}</svg>`;
}
