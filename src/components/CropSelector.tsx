import {Link} from 'react-router-dom';
import type {Crop} from '../lib/domain';
import {useLanguage} from '../lib/i18n';
import {Field} from './ui';
export function CropSelector({crops,selected,onSelect,base}:{crops:Crop[];selected?:Crop;onSelect:(id:string)=>void;base:string}){const{t}=useLanguage();return <div className="selected-crop"><Field label="Your saved crop"><select value={selected?.id||''} onChange={e=>onSelect(e.target.value)}>{crops.map(c=><option key={c.id} value={c.id}>{t(c.name)} · {c.variety} · {c.quantity} qtl · {c.location}</option>)}</select></Field><Link className="text-link" to={`${base}/crops/new`}>{t('Add crop')} →</Link>{selected&&<p className="muted">{t('Grade')} {selected.grade} ({t('Self-declared')}) · {selected.variety} · {selected.quantity} qtl · {selected.location}</p>}</div>}
