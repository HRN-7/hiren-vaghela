import {useEffect,useState,type FormEvent} from 'react';
import {useOutletContext,useNavigate} from 'react-router-dom';
import {LineChart,Line,XAxis,YAxis,CartesianGrid,Tooltip,ResponsiveContainer} from 'recharts';
import {UserRound,ShieldCheck,Bell,Sparkles,CloudSun,BarChart3,ArrowUpRight,LogOut} from 'lucide-react';
import {Panel,Field,Note,Badge,Empty,Source,Busy} from '../components/ui';
import {useLanguage} from '../lib/i18n';
import {useApp} from '../lib/context';
import {api,currentWeather} from '../lib/api';
import {enableBrowserPush,disableBrowserPush,savedPushToken} from '../lib/push';
import {DemandForecastPanel} from '../components/DemandForecastPanel';
import {crops,cities,rupee,type CropName} from '../lib/domain';
export function Forecasts(){
 const{t}=useLanguage();

 type ForecastOption={
  market:string;
  variety:string;
  observed_days:number;
  oldest_date?:string;
  newest_date?:string;
  validated:boolean;
 };

 const[crop,setCrop]=useState<CropName>('Wheat');
 const[market,setMarket]=useState('');
 const[variety,setVariety]=useState('');
 const[grade,setGrade]=useState('A');
 const[busy,setBusy]=useState(false);
 const[optionsBusy,setOptionsBusy]=useState(false);
 const[options,setOptions]=useState<ForecastOption[]>([]);
 const[optionsMessage,setOptionsMessage]=useState('');
 const[forecast,setForecast]=useState<any>(null);
 const[weather,setWeather]=useState<any>(null);

 const marketNames=Array.from(new Set(options.map(o=>o.market)));
 const varieties=options.filter(o=>o.market===market);
 const selectedOption=options.find(
  o=>o.market===market&&o.variety===variety
 );

 useEffect(()=>{
  currentWeather(...cities.Surat).then(setWeather);
 },[]);

 useEffect(()=>{
  let active=true;
  setOptionsBusy(true);
  setOptions([]);
  setMarket('');
  setVariety('');
  setForecast(null);
  setOptionsMessage('');

  api(`/forecast/options?crop=${encodeURIComponent(crop)}`)
   .then((data:any)=>{
    if(!active)return;
    const rows:ForecastOption[]=data?.records||[];
    setOptions(rows);
    setOptionsMessage(data?.message||'');

    const first=rows[0];
    if(first){
     setMarket(first.market);
     setVariety(first.variety);

     if(first.validated){
      const query=new URLSearchParams({
       crop,
       market:first.market,
       variety:first.variety,
       grade
      });

      api('/forecast?'+query.toString())
       .then(result=>{if(active)setForecast(result);})
       .catch(()=>{
        if(active)setForecast({
         status:'unavailable',
         message:'Validated AI trend is currently unavailable.'
        });
       });
     }
    }
   })
   .catch(()=>{
    if(!active)return;
    setOptionsMessage(
     'Historical market and variety options could not be loaded.'
    );
   })
   .finally(()=>{
    if(active)setOptionsBusy(false);
   });

  return()=>{active=false};
 },[crop]);

 async function load(e:FormEvent){
  e.preventDefault();

  if(!market||!variety){
   setForecast({
    status:'unavailable',
    message:'Select a historical market and variety.'
   });
   return;
  }

  setBusy(true);
  setForecast(null);

  try{
   const query=new URLSearchParams({
    crop,
    market,
    variety,
    grade
   });

   setForecast(await api('/forecast?'+query.toString()));
  }catch{
   setForecast({
    status:'unavailable',
    message:'No validated AI trend is available for this market and variety.'
   });
  }finally{
   setBusy(false);
  }
 }

 const days=weather?.daily?.time?.map((d:string,i:number)=>({
  date:d.slice(5),
  temperature:weather.daily.temperature_2m_max[i],
  rain:weather.daily.precipitation_probability_max[i]
 }))||[];

 return <>
  <div className="page-heading">
   <div>
    <span className="eyeline">AHEAD OF THE HARVEST</span>
    <h1>{t('Forecasts')}</h1>
    <p>
     Gujarat historical mandi markets and varieties are suggested crop-wise.
     AI forecasts appear only where the model passed chronological validation.
    </p>
   </div>
   <Badge tone="amber">{t('AI estimated')}</Badge>
  </div>

  <form onSubmit={load}>
   <Panel className="filter-panel">
    <div className="form-grid filters">

     <Field label="Crop">
      <select
       disabled={busy||optionsBusy}
       value={crop}
       onChange={e=>setCrop(e.target.value as CropName)}
      >
       {crops.map(c=>
        <option value={c} key={c}>{t(c)}</option>
       )}
      </select>
     </Field>

     <Field label="Market / location">
      <select
       disabled={busy||optionsBusy||marketNames.length===0}
       value={market}
       onChange={e=>{
        const selected=e.target.value;
        const first=options.find(o=>o.market===selected);

        setMarket(selected);
        setVariety(first?.variety||'');
        setForecast(null);
       }}
      >
       {optionsBusy?
        <option value="">Loading historical markets...</option>
        :
        marketNames.length===0?
        <option value="">No historical market available</option>
        :
        marketNames.map(name=>{
         const hasAI=options.some(
          o=>o.market===name&&o.validated
         );
         return <option key={name} value={name}>
          {name}{hasAI?' · AI validated':''}
         </option>;
        })
       }
      </select>
     </Field>

     <Field label="Variety">
      <select
       disabled={busy||optionsBusy||varieties.length===0}
       value={variety}
       onChange={e=>{
        setVariety(e.target.value);
        setForecast(null);
       }}
      >
       {optionsBusy?
        <option value="">Loading varieties...</option>
        :
        varieties.length===0?
        <option value="">No historical variety available</option>
        :
        varieties.map(v=>
         <option
          key={`${v.market}-${v.variety}`}
          value={v.variety}
         >
          {v.variety}
          {v.validated?' · AI validated':''}
          {` · ${v.observed_days} days`}
         </option>
        )
       }
      </select>
     </Field>

     <Field label="Grade">
      <select
       disabled={busy}
       value={grade}
       onChange={e=>{
        setGrade(e.target.value);
        setForecast(null);
       }}
      >
       {['A','B','C'].map(g=>
        <option key={g}>{g}</option>
       )}
      </select>
     </Field>

    </div>

    <button
     className="btn"
     disabled={busy||optionsBusy||!market||!variety}
    >
     {busy?
      <Busy/>
      :
      <>
       <Sparkles size={17}/>
       {t('View forecast')}
      </>
     }
    </button>
   </Panel>
  </form>

  <Note tone="warm">
   {optionsMessage||
    'Markets and varieties are loaded from verified Gujarat historical mandi coverage.'}
   {selectedOption&&!selectedOption.validated?
    ' This selected combination has historical data, but its AI model has not passed validation yet.'
    :
    selectedOption?.validated?
    ' This selected combination has a validated AI trend model.'
    :
    ''
   }
  </Note>

  <div className="forecast-grid mt">

   <Panel>
    <div className="section-head">
     <div>
      <h2>{t('Price forecast')}</h2>
      <p>
       {market&&variety?
        `${crop} · ${market} · ${variety} · Grade ${grade}`
        :
        `${crop} · Select market and variety`
       }
      </p>
     </div>
     <BarChart3 size={20}/>
    </div>

    {forecast?.status==='estimated'?
     <>
      <Note>
       Validated AI trend · MAE {rupee(forecast.validation_mae)}
       {' · '}Baseline {rupee(forecast.baseline_mae)}
      </Note>

      {!forecast.grade_specific&&
       <Note tone="warm">
        Grade {grade} remains mandatory for recommendation and buyer matching.
        This forecast is a market + variety timing trend, not a grade-specific
        selling-price guarantee.
       </Note>
      }

      <ResponsiveContainer width="100%" height={250}>
       <LineChart data={forecast.records}>
        <CartesianGrid vertical={false}/>
        <XAxis dataKey="date" tick={{fontSize:12}}/>
        <YAxis tick={{fontSize:12}}/>
        <Tooltip formatter={(v:any)=>rupee(Number(v))}/>
        <Line
         dataKey="price"
         stroke="#2f7a4f"
         strokeWidth={3}
        />
       </LineChart>
      </ResponsiveContainer>

      <Source
       name="XGBoost · chronological holdout validation"
       date={forecast.trained_through}
      />
     </>
     :
     <Empty
      title={
       selectedOption&&!selectedOption.validated?
       'Historical data available · AI not validated'
       :
       'No validated forecast available'
      }
      description={
       forecast?.message||
       (
        selectedOption&&!selectedOption.validated?
        'This market and variety are available from historical mandi data, but KrishiLink will not show an AI forecast until the model beats its baseline.'
        :
        'Select a market and variety to check AI availability.'
       )
      }
     />
    }
   </Panel>

   <DemandForecastPanel forecast={forecast?.demand_details}/>

  </div>

  <Panel className="mt">
   <div className="section-head">
    <div>
     <h2>{t('Weather outlook')}</h2>
     <p>Surat · {t('Next 7 days')}</p>
    </div>
    <CloudSun size={24}/>
   </div>

   {days.length?
    <>
     <ResponsiveContainer width="100%" height={240}>
      <LineChart data={days}>
       <CartesianGrid vertical={false} stroke="#e4eddd"/>
       <XAxis dataKey="date" tick={{fontSize:12}}/>
       <YAxis tick={{fontSize:12}} unit="°"/>
       <Tooltip formatter={(v:any)=>v+' °C'}/>
       <Line
        dataKey="temperature"
        stroke="#658c45"
        strokeWidth={3}
        dot={{r:3}}
       />
      </LineChart>
     </ResponsiveContainer>

     <Source
      name="Open-Meteo · daily maximum temperature"
      url="https://open-meteo.com/"
     />
    </>
    :
    <Empty title="Weather unavailable"/>
   }

   <Note>
    Weather is shown for handling and travel planning.
    No crop-price effect is inferred without a validated model.
   </Note>
  </Panel>
 </>
}


type AccountNotification={id:string;text:string;read:boolean};
export function Profile(){
 const{t,lang,setLang}=useLanguage();const{profile,user,logout,setNotice,reload}=useApp();
 const{preview,role}=useOutletContext<{preview:boolean;role:string}>();const nav=useNavigate();
 const[name,setName]=useState(profile?.name||'');const[location,setLocation]=useState(profile?.location||'Surat');
 const[error,setError]=useState('');const[notificationError,setNotificationError]=useState('');
 const[notifications,setNotifications]=useState<AccountNotification[]>([]);
 const[notificationBusy,setNotificationBusy]=useState(false);
 const[enabled,setEnabled]=useState(()=>Boolean(!preview&&savedPushToken(user?.uid)));
 const[reading,setReading]=useState<string|null>(null);
 useEffect(()=>{
  if(preview)return;
  const controller=new AbortController();
  api<AccountNotification[]>('/notifications',{signal:controller.signal}).then(setNotifications).catch(()=>{
   if(!controller.signal.aborted)setNotificationError('Notifications could not be loaded.');
  });
  return()=>controller.abort();
 },[preview,user?.uid]);
 async function save(e:FormEvent){
  e.preventDefault();setError('');
  if(preview){setNotice(t('Profile changes require an account.'));return;}
  try{await api('/auth/me',{method:'PUT',body:JSON.stringify({name,role,location,language:lang})});await reload();setNotice(t('Profile saved.'));}
  catch(e){setError(e instanceof Error?e.message:'Profile could not be saved.');}
 }
 async function toggleNotifications(){
  setNotificationError('');setNotificationBusy(true);
  try{
   if(preview)throw Error('Sign in to enable account notifications.');
   if(enabled)await disableBrowserPush();else await enableBrowserPush();
   setEnabled(!enabled);setNotice(t(enabled?'Notifications disabled on this device.':'Notifications enabled.'));
  }catch(e){setNotificationError(e instanceof Error?e.message:'Notifications were not enabled.');}
  finally{setNotificationBusy(false);}
 }
 async function markRead(id:string){
  setNotificationError('');setReading(id);
  try{
   const updated=await api<AccountNotification>(`/notifications/${encodeURIComponent(id)}/read`,{method:'PUT'});
   setNotifications(rows=>rows.map(row=>row.id===id?updated:row));
  }catch{setNotificationError('This notification could not be marked as read.');}
  finally{setReading(null);}
 }
 return <>
  <div className="page-heading"><div><h1>{t('Profile')}</h1><p>{t('Your account and preferences.')}</p></div><Badge>{t(preview?'Preview workspace':'Verified account')}</Badge></div>
  <div className="profile-grid stack">
   <Panel><div className="section-head"><h2><UserRound size={20}/>{t('Your details')}</h2></div>
    <form onSubmit={save} className="stack"><div className="form-grid">
     <Field label="Full name"><input required minLength={2} maxLength={120} value={name} onChange={e=>setName(e.target.value)}/></Field>
     <Field label="Location"><input required minLength={2} maxLength={150} value={location} onChange={e=>setLocation(e.target.value)}/></Field>
     <Field label="Email"><input disabled value={user?.email||'â€”'}/></Field>
     <Field label="Account role"><input disabled value={t(role==='farmer'?'Farmer':role==='buyer'?'Buyer':'FPO')}/></Field>
     <Field label="Language"><select value={lang} onChange={e=>setLang(e.target.value as typeof lang)}><option value="en">English</option><option value="gu">àª—à«àªœàª°àª¾àª¤à«€</option><option value="hi">à¤¹à¤¿à¤¨à¥à¤¦à¥€</option><option value="mr">à¤®à¤°à¤¾à¤ à¥€</option></select></Field>
    </div>{error&&<Note tone="error">{t(error)}</Note>}<button className="btn" disabled={preview}>{t('Save profile')}</button></form>
   </Panel>
   <Panel>
    <div className="section-head notification-heading"><h2><Bell size={20}/>{t('Notifications')}</h2>
     <button className="btn secondary" onClick={toggleNotifications} disabled={notificationBusy}>{notificationBusy?<Busy/>:t(enabled?'Disable notifications':'Enable notifications')}</button>
    </div>
    {notificationError&&<Note tone="error">{t(notificationError)}</Note>}
    {notifications.length>0?notifications.map(n=><div className="notification-item" key={n.id}>
     <p>{n.text}</p>{n.read?<Badge>{t('Read')}</Badge>:<button className="text-link" onClick={()=>markRead(n.id)} disabled={reading!==null}>{reading===n.id?<Busy/>:t('Mark as read')}</button>}
    </div>):<p className="muted">{t('No notifications yet.')}</p>}
   </Panel>
   <button className="btn secondary" onClick={async()=>{await logout();nav('/login')}}><LogOut size={17}/>{t('Sign out')}</button>
  </div>
 </>;
}
const sources=[
['AGMARKNET / data.gov.in','Published mandi prices; observation dates are retained.','https://agmarknet.gov.in/daily-price-and-arrival-report'],
['eNAM','Trading information reference. A public page is not a guaranteed integration API.','https://enam.gov.in/web/dashboard/trade-data'],
['Open-Meteo','Current weather and daily weather forecasts.','https://open-meteo.com/'],
['OpenStreetMap / OSRM','Community map locations and driving route estimates.','https://www.openstreetmap.org/copyright'],
['FR8','Published full-truck prices on the Suratâ€“Mumbai route.','https://www.fr8.in/transport-service/surat-transport-service/surat-to-mumbai/'],
['VRC Mobility','Fleet, rate structure and API-access reference; live access requires provider integration.','https://www.vrcmobility.in/platform'],
['GoMyTruck','Freight benchmark reference, not confirmed vehicle availability.','https://gomytruck.com/freight-rate-index/'],
['SFAC','Public FPO directory; current services and contact details need confirmation.','https://sfacindia.com/List-of-FPO-Statewise.aspx'],
['CWC / WDRA','Storage directory references; current vacancy and tariffs require confirmation.','https://wdra.gov.in/']
];
export function Support(){const{t}=useLanguage();return <><div className="page-heading"><div><span className="eyeline">KNOW WHAT IS BEHIND THE NUMBER</span><h1>{t('Support & sources')}</h1><p>{t('Understand the data before making a selling decision.')}</p></div></div><Panel><div className="section-head"><h2>{t('How KrishiLink helps')}</h2><ShieldCheck size={21}/></div><p>{t('Add your crop, compare market opportunities, subtract transport and storage costs, and connect with a buyer or FPO. You make the final selling decision.')}</p><div className="cards-grid mt">{[['01','Add your crop','Enter crop, grade, quantity and selling date.'],['02','Compare your return','Subtract every relevant selling cost.'],['03','Connect and confirm','Confirm terms directly with the buyer or service provider.']].map(([n,h,p])=><div key={n}><span className="step-number">{n}</span><h3 className="mt">{t(h)}</h3><p className="muted">{t(p)}</p></div>)}</div></Panel><Panel className="mt"><div className="section-head"><h2>{t('Data sources')}</h2><Badge>{t('Source transparency')}</Badge></div><div className="table-wrap"><table className="info-table"><thead><tr><th>{t('Source')}</th><th>{t('Use in KrishiLink')}</th><th>{t('Reference')}</th></tr></thead><tbody>{sources.map(([name,desc,url])=><tr key={name}><td>{name}</td><td>{t(desc)}</td><td><a className="text-link" href={url} target="_blank" rel="noreferrer">{t('View source')}<ArrowUpRight size={14}/></a></td></tr>)}</tbody></table></div></Panel><Panel className="mt support-copy"><h2>{t('Questions, answered')}</h2>{[
 ['What is net realization?','Your selling price minus transport, storage and market charges. Multiply the result per quintal by your quantity to estimate total income.'],
 ['Why are some fields unavailable?','A missing price, tariff, capacity or arrival observation is left unknown. KrishiLink does not create live-looking numbers to fill gaps.'],
 ['Are Grade A, B and C official grades?','These prototype descriptions are self-declared quality categories, not official certification. Record measurements and agree specifications with the buyer.'],
 ['Is a directory listing a verified provider?','No. A directory entry only identifies a listed organization. Confirm current registration, services, availability and contact details.'],
 ['What makes KrishiLink different?','Price portals show market rates and logistics platforms show service options. KrishiLink brings price and selling costs into one net-return comparison.'],
 ['Can I pay or book here?','This prototype supports discovery, comparison and connections. Payment and confirmed booking are not available.']
 ].map(([q,a])=><details key={q}><summary>{t(q)}</summary><p>{t(a)}</p></details>)}<Source name="The Green Field by Abhijeet Sawant Â· CC BY-SA 3.0 Â· displayed with a crop" url="https://commons.wikimedia.org/wiki/File:The_Green_Field.jpg"/><Source name="Creative Commons Attribution-ShareAlike 3.0" url="https://creativecommons.org/licenses/by-sa/3.0/"/></Panel></>}




