import {useEffect,useState} from 'react';
import {Link,useOutletContext} from 'react-router-dom';
import {Sprout,IndianRupee,Wallet,Plus,Leaf,RefreshCw,ArrowRight,MapPin,CloudSun,Droplets,Wind} from 'lucide-react';
import {BarChart,Bar,XAxis,YAxis,Tooltip,ResponsiveContainer,CartesianGrid,Cell} from 'recharts';
import {Panel,Badge,Note,Source,Empty,Busy} from '../components/ui';
import {useLanguage} from '../lib/i18n';
import {useApp} from '../lib/context';
import {currentWeather} from '../lib/api';
import {cities,rupee,dateLabel} from '../lib/domain';
import {cropKey,useSelectedCrop,useMarketOptions} from '../lib/marketFlow';

function priceText(value:unknown){
 const n=Number(value);
 return value==null||value===''||!Number.isFinite(n)?'-':rupee(n);
}

export function WeatherCard(){
 const{t}=useLanguage();
 const[location,setLocation]=useState('Surat');
 const[weather,setWeather]=useState<any>(null);

 useEffect(()=>{
  let active=true;
  setWeather(null);
  const coords=(cities as any)[location];
  if(!coords)return()=>{active=false};
  currentWeather(coords[0],coords[1]).then((data:any)=>{if(active)setWeather(data);});
  return()=>{active=false};
 },[location]);

 return <Panel className="weather-card">
  <div className="section-head"><h3>{t('Local weather')}</h3><CloudSun size={22}/></div>
  <label className="weather-location"><MapPin size={14}/><select value={location} onChange={e=>setLocation(e.target.value)}>{Object.keys(cities).map(city=><option key={city}>{city}</option>)}</select></label>
  <div className="weather-main"><strong>{weather?.current?Math.round(weather.current.temperature_2m)+'°':weather?'—':'…'}</strong><CloudSun size={62} strokeWidth={1.3}/></div>
  <p>{weather?.current?t(weather.current.precipitation>0?'Rainfall reported':'Current weather'):t(weather?'Weather unavailable':'Loading…')}</p>
  <div className="weather-stats">
   <div><Droplets size={16}/><span>{t('Humidity')}<b>{weather?.current?.relative_humidity_2m??'—'}%</b></span></div>
   <div><Wind size={16}/><span>{t('Wind')}<b>{weather?.current?.wind_speed_10m??'—'} km/h</b></span></div>
  </div>
  <Source name="Open-Meteo" url="https://open-meteo.com/" date={weather?.current?.time?.replace('T',' ')}/>
 </Panel>;
}

export default function Dashboard(){
 const{t}=useLanguage();
 const{profile,marketFlow}=useApp();
 const{base}=useOutletContext<any>();
 const{crops,crop,selectCrop}=useSelectedCrop();
 const{feed,loading,error,refresh}=useMarketOptions(crop);
 const rows:any[]=feed?.records||[];
 const recentCrops=[...crops.slice(-4)];
 if(crop&&!recentCrops.some(c=>c.id===crop.id)&&recentCrops.length)recentCrops[0]=crop;

 const bestPrice=rows.length?Math.max(...rows.map(r=>Number(r.price))):null;
 const marketFlowAny:any=marketFlow;
 const result=crop&&marketFlowAny?.key===cropKey(crop)&&Date.parse(marketFlowAny.result?.expires_at)>Date.now()?marketFlowAny.result:null;
 const bestNet=result?.ranking?.find((r:any)=>r.id===result.best_market_id);

 const stats=[
  [Sprout,t('Crops added'),String(crops.length),t('Your available produce')],
  [IndianRupee,t('Best listed price'),priceText(bestPrice),crop?`${t(crop.name)} · ${feed?.date?dateLabel(feed.date):t('Awaiting current market data')}`:t('Add your first crop')],
  [Wallet,t('Estimated net realization'),priceText(bestNet?.net_per_quintal),bestNet?.market||t('Select markets and service options')]
 ] as const;

 return <>
  <div className="page-heading">
   <div>
    <div className="eyeline">{new Date().toLocaleDateString('en-IN',{weekday:'long',day:'numeric',month:'long',timeZone:'Asia/Kolkata'})}</div>
    <h1>{t('Farmer dashboard')}</h1>
    <p>{t('Welcome back')}{profile?.name?', '+profile.name.split(' ')[0]:''}. {t('Let’s find your next opportunity.')}</p>
   </div>
   <Link className="btn" to={`${base}/crops/new`}><Plus size={18}/>{t('Add crop')}</Link>
  </div>

  <div className="hero-strip">
   <div>
    <span className="eyebrow"><Leaf size={14}/> THE BIGGER PICTURE</span>
    <h2>{t('Make every quintal count.')}</h2>
    <p>{t('Compare selling options after transport, storage and market costs.')}</p>
   </div>
   <div className="hero-photo"><img src="/farm.jpg" alt="Cultivated green fields"/></div>
   <span className="hero-caption">GROW MORE THAN CROPS.</span>
  </div>

  <div className="stat-grid three">
   {stats.map(([Icon,title,value,detail],i)=><Panel className="stat" key={i}>
    <div className="stat-top"><span>{String(title)}</span><span className={'stat-icon s'+i}><Icon size={18}/></span></div>
    <strong>{String(value)}{i>0&&String(value)!=='-'&&<small>/ qtl</small>}</strong>
    <p>{String(detail)}</p>
   </Panel>)}
  </div>

  <div className="dashboard-grid">
   <div className="stack">
    <Panel>
     <div className="section-head">
      <div>
       <h2>{t('Market snapshot')}</h2>
       <p>{crop?`${t(crop.name)} · ${crop.variety} · ${t('Grade')} ${crop.grade} · ${crop.location}`:t('Your saved crops will appear here.')}</p>
      </div>
      {crop&&<button className="icon-btn" aria-label={t('Refresh market snapshot')} disabled={loading} onClick={refresh}><RefreshCw size={17}/></button>}
     </div>

     <div className="crop-tabs" aria-label={t('Your added crops')}>
      {recentCrops.map(c=><button key={c.id} aria-pressed={crop?.id===c.id} onClick={()=>selectCrop(c.id)}>{t(c.name)}<small>{c.variety} · {c.quantity} qtl</small></button>)}
     </div>

     {loading?<div className="empty"><Busy/></div>:error?<Note tone="error">{error}</Note>:rows.length?<>
      <div className="chart-label"><span>₹ / {t('Quintal')}</span><span>{t('Latest available reports')}</span></div>
      <div className="market-chart">
       <ResponsiveContainer width="100%" height={235}>
        <BarChart data={rows.slice(0,6)} margin={{left:-15,right:10,top:15,bottom:0}}>
         <CartesianGrid vertical={false} stroke="#e8eeea" strokeDasharray="3 4"/>
         <XAxis dataKey="market" tickLine={false} axisLine={false} tick={{fontSize:12,fill:'#728177'}}/>
         <YAxis tickLine={false} axisLine={false} tick={{fontSize:12,fill:'#728177'}}/>
         <Tooltip formatter={(v:any)=>rupee(Number(v))} cursor={{fill:'#f2f7f3'}} contentStyle={{borderRadius:10,borderColor:'#e0e9e3'}}/>
         <Bar dataKey="price" name={t('Published modal price')} radius={[5,5,0,0]} maxBarSize={42}>
          {rows.slice(0,6).map((r:any)=><Cell key={r.id} fill={Number(r.price)===bestPrice?'#1d7650':'#cde4d5'}/>)}
         </Bar>
        </BarChart>
       </ResponsiveContainer>
      </div>
      <div className="snapshot-markets">
       {rows.slice(0,6).map((r:any)=><div key={r.id}>
        <strong>{r.market}</strong>
        <span>{rupee(r.price)}/q</span>
        <small>{r.district} · {r.variety||t('Variety not reported')} · {t('Reported grade')}: {r.grade||'—'} · {dateLabel(r.date)}</small>
       </div>)}
      </div>
      <p className="muted text-small mt">{t('Your quality grade is self-declared. Published mandi grades and modal prices are shown without a grade conversion.')}</p>
     </>:<Empty title={crop?'No matching live market data':'No crops added yet'} description={crop?feed?.message||'Current market data is unavailable.':'Add your crop to see relevant market prices.'} action={crop?undefined:<Link className="text-link" to={`${base}/crops/new`}><Plus size={16}/>{t('Add your first crop')}</Link>}/>}

     {crop&&<div className="panel-bottom">
      <Source name="AGMARKNET via data.gov.in" url="https://www.data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi" date={feed?.date}/>
      <Link className="text-link" to={`${base}/markets?crop=${encodeURIComponent(crop.id)}`}>{t('View all markets')}<ArrowRight size={14}/></Link>
     </div>}
    </Panel>

    <Panel>
     <div className="section-head"><h2>{t('Crop overview')}</h2><Link className="text-link" to={`${base}/crops`}>{t('View crops')}<ArrowRight size={14}/></Link></div>
     {crops.length?<div className="table-wrap"><table>
      <thead><tr><th>{t('Crop')}</th><th>{t('Quantity')}</th><th>{t('Grade')}</th><th>{t('Expected selling date')}</th></tr></thead>
      <tbody>{crops.slice(0,4).map(c=><tr key={c.id}>
       <td><Link className="text-link" to={`${base}/recommendations?crop=${encodeURIComponent(c.id)}`}>{t(c.name)}</Link><small>{c.variety}</small></td>
       <td>{c.quantity} qtl</td>
       <td><Badge>{c.grade}</Badge></td>
       <td>{dateLabel(c.sell_date)}</td>
      </tr>)}</tbody>
     </table></div>:<Empty title="No crops added yet" description="Start with your crop, quantity and grade." action={<Link className="text-link" to={`${base}/crops/new`}><Plus size={16}/>{t('Add your first crop')}</Link>}/>}
    </Panel>
   </div>

   <div className="stack">
    <WeatherCard/>
    <div className="trust-caption"><Sprout size={19}/><p>{t('Your crop. Your choice.')}<br/><span>{t('Clear information for better decisions.')}</span></p></div>
   </div>
  </div>
 </>;
}

