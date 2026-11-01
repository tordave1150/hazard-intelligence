import type {ExpressionSpecification} from 'maplibre-gl';

export const stationColors={water:'#758997',rain:'#508faf'};

// A station may publish both products at the same coordinate. Count product
// records separately instead of presenting their sum as unique stations.
export const stationClusterProperties={
  water_count:['+',['case',['==',['get','kind'],'river'],1,0]],
  rain_count:['+',['case',['==',['get','kind'],'rain'],1,0]],
};
export const stationClusterLabel:ExpressionSpecification=['case',
  ['all',['>',['get','water_count'],0],['>',['get','rain_count'],0]],
  ['concat','น้ำ ',['to-string',['get','water_count']],'\nฝน ',['to-string',['get','rain_count']]],
  ['>',['get','water_count'],0],['concat','น้ำ\n',['to-string',['get','water_count']]],
  ['concat','ฝน\n',['to-string',['get','rain_count']]],
];
export const stationClusterColor:ExpressionSpecification=['case',
  ['all',['>',['get','water_count'],0],['>',['get','rain_count'],0]],'#426c6a',
  ['>',['get','rain_count'],0],'#286b96','#526b80',
];
export function stationClusterSummary(water:number,rain:number){
  return [water>0?`ระดับน้ำ ${water.toLocaleString('th-TH')} รายการ`:null,
    rain>0?`ฝน ${rain.toLocaleString('th-TH')} รายการ`:null].filter(Boolean).join(' · ');
}
