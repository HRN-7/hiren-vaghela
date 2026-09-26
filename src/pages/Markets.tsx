import {useEffect,useState} from 'react';
import {Link,useOutletContext} from 'react-router-dom';
import {RefreshCw,BarChart3,Plus} from 'lucide-react';
import {LineChart,Line,XAxis,YAxis,Tooltip,ResponsiveContainer,CartesianGrid,Legend} from 'recharts';
import {Panel,Field,Badge,Note,Source,Empty,Busy} from '../components/ui';
import {CropSelector} from '../components/CropSelector';
import {useLanguage} from '../lib/i18n';
import {api} from '../lib/api';
import {rupee,dateLabel} from '../lib/domain';
import {useSelectedCrop,useMarketOptions} from '../lib/marketFlow';
export default function Markets(){
 const{t}=useLanguage();const{base}=useOutletContext<any>();const{crops,crop,selectCrop}=useSelectedCrop();const{feed,loading,error,refresh}=useMarketOptions(crop);
 const[marketId,setMarketId]=useState('');
 const[history,setHistory]=useState<any[]>([]);
 const[historyMarkets,setHistoryMarkets]=useState<string[]>([]);
 const[historyBusy,setHistoryBusy]=useState(false);
 const rows=feed?.records||[];
 const market=rows.find(r=>r.id===marketId);
 const filtered=market?[market]:rows;
 const marketSignature=rows.map((r:any)=>`${r.market}|${r.variety||''}|${r.state||''}`).join('||');

 useEffect(()=>{setMarketId('');setHistory([]);setHistoryMarkets([]);},[crop?.id]);

 useEffect(()=>{
   setHistory([]);
   setHistoryMarkets([]);
   if(!crop||!rows.length)return;

   let active=true;
   setHistoryBusy(true);

   const markets=[...new Set(rows.map((r:any)=>String(r.market||'').trim()).filter(Boolean))] as string[];
   const allowed=new Set(markets);
   const varieties=new Map(rows.map((r:any)=>[
     String(r.market||'').trim(),
     String(r.variety||'').trim().toLowerCase()
   ]));

   setHistoryMarkets(markets);

   const state=String(rows.find((r:any)=>r.state)?.state||'Gujarat');
   const query=new URLSearchParams({crop:crop.name,state});

   api('/prices?'+query)
     .then(data=>{
       if(!active)return;

       const cutoff=new Date();
       cutoff.setHours(0,0,0,0);
       cutoff.setDate(cutoff.getDate()-29);

       const byDate=new Map<string,any>();

       for(const r of data.records||[]){
         const marketName=String(r.market||'').trim();
         if(!allowed.has(marketName))continue;

         const wantedVariety=varieties.get(marketName)||'';
         const actualVariety=String(r.variety||'').trim().toLowerCase();
         if(wantedVariety&&actualVariety&&wantedVariety!==actualVariety)continue;

         const rawDate=String(r.date||'');
         const d=new Date(rawDate+'T00:00:00');
         if(Number.isNaN(d.getTime())||d<cutoff)continue;

         const price=Number(r.price);
         if(!Number.isFinite(price)||price<=0)continue;

         const point=byDate.get(rawDate)||{date:rawDate,prices:{}};
         point.prices[marketName]=price;
         byDate.set(rawDate,point);
       }

       setHistory(
         [...byDate.values()].sort((a:any,b:any)=>a.date.localeCompare(b.date))
       );
     })
     .catch(()=>{if(active)setHistory([]);})
     .finally(()=>{if(active)setHistoryBusy(false);});

   return()=>{active=false};
 },[crop?.name,marketSignature]);
 return <><div className="page-heading"><div><span className="eyeline">KNOW YOUR OPTIONS</span><h1>{t('Market prices')}</h1><p>{t('Latest available mandi reports for your saved crop and location.')}</p></div>{crop&&<button className="btn secondary" onClick={refresh} disabled={loading}><RefreshCw size={16}/>{t('Refresh')}</button>}</div>
 {!crop?<Panel><Empty title="Add a crop to find your markets" description="Your crop, variety, grade, quantity and location will guide the suggestions." action={<Link className="btn" to={`${base}/crops/new`}><Plus size={17}/>{t('Add crop')}</Link>}/></Panel>:<><Panel className="filter-panel"><CropSelector crops={crops} selected={crop} onSelect={selectCrop} base={base}/><div className="mt"><Field label="Market"><select value={marketId} onChange={e=>setMarketId(e.target.value)}><option value="">{t('All matching markets')}</option>{rows.map(r=><option key={r.id} value={r.id}>{r.market} Â· {r.district}</option>)}</select></Field></div></Panel><Note tone="warm">{t('Latest available published observations may be delayed. Always check the reporting date.')} {t('Your A/B/C grade is self-declared; the mandi grade is shown as reported.')}</Note>
 {loading?<Busy/>:error?<Note tone="error">{error}</Note>:<><div className="stat-grid three"><Panel className="stat"><span>{t('Best listed price')}</span><strong>{rupee(filtered.length?Math.max(...filtered.map(r=>r.price)):null)}<small>/ qtl</small></strong><p>{feed?.date?dateLabel(feed.date):t('Unavailable')}</p></Panel><Panel className="stat"><span>{t('Nearby reporting markets')}</span><strong>{rows.length}</strong><p>{crop.location}</p></Panel><Panel className="stat"><span>{t('Your crop')}</span><strong>{t(crop.name)}</strong><p>{crop.variety} Â· {crop.quantity} qtl Â· {t('Grade')} {crop.grade}</p></Panel></div><Panel><div className="section-head"><h2>{t('Market comparison')}</h2><Badge tone="amber">{t('Published modal prices')}</Badge></div>{filtered.length?<div className="table-wrap"><table><thead><tr>{['Market','Variety','Reported grade','Min / max','Modal price','Distance','Data date'].map(h=><th key={h}>{t(h)}</th>)}</tr></thead><tbody>{filtered.map(r=><tr key={r.id}><td><button className="table-link" onClick={()=>setMarketId(r.id)}>{r.market}</button><small>{r.district}, {r.state}</small></td><td>{r.variety||'â€”'}<small>{t(r.variety_match)}</small></td><td><Badge>{r.grade||t('Not reported')}</Badge></td><td>{rupee(r.min)} / {rupee(r.max)}</td><td className="price-cell">{rupee(r.price)}</td><td>{r.distance_km==null?'â€”':r.distance_km+' km'}<small>{t('Estimated')}</small></td><td>{dateLabel(r.date)}</td></tr>)}</tbody></table></div>:<Empty title="No matching live market data" description={feed?.message}/>}<div className="panel-bottom"><Source name="AGMARKNET via data.gov.in" url={feed?.source_url} date={feed?.date}/><Link className="text-link" to={`${base}/recommendations?crop=${encodeURIComponent(crop.id)}`}>{t('Compare Net Realization')} â†’</Link></div></Panel>
 <Panel className="mt"><div className="section-head"><div><h2>{t('Last 30 days')}</h2><p>{historyMarkets.length?`${historyMarkets.length} matching markets ? Published modal price`:t('No matching market history')}</p></div><BarChart3 size={20}/></div>{historyBusy?<Busy/>:history.length>=2?<ResponsiveContainer width="100%" height={320}><LineChart data={history}><CartesianGrid vertical={false} stroke="#e6ece8"/><XAxis dataKey="date" tick={{fontSize:12}}/><YAxis tick={{fontSize:12}}/><Tooltip formatter={(v:any)=>rupee(Number(v))}/><Legend/>{historyMarkets.map((name,i)=><Line key={name} type="monotone" dataKey={(point:any)=>point.prices?.[name]} name={name} stroke={['#1c7650','#2563eb','#d97706','#9333ea','#dc2626','#0891b2','#65a30d','#c026d3'][i%8]} strokeWidth={2.5} dot={false} connectNulls={true}/>)}</LineChart></ResponsiveContainer>:<Empty title="No recent price history" description="No published AGMARKNET observations were found for these markets in the last 30 days."/>}</Panel></>}</> }</>;
}


