import {ArrowUpRight} from 'lucide-react';
import styles from './workspace.module.css';
export type OverviewItem={title:string;value:string|number;unit:string;detail:string;disabled?:boolean;onInspect:()=>void};
export default function SituationOverview({items}:{items:OverviewItem[]}){
  return <section aria-label="Situation overview"><p className={styles.guidance}>Thailand-wide source summary. Counts describe returned records, stations or messages; they are not impacted area or a danger level. Open a source to inspect the selected map area.</p>
    <div className={styles.overviewGrid}>{items.map(item=><button key={item.title} disabled={item.disabled} onClick={item.onInspect}><small>{item.title}</small><strong>{item.value}</strong><span>{item.unit}</span><p>{item.detail}</p><ArrowUpRight size={16}/></button>)}</div>
  </section>;
}
