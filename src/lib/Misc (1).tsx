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
export function Forecasts(){const{t}=useLanguage();const[crop,setCrop]=useState<CropName>('Rice');const[market,setMarket]=useState('');const[variety,setVariety]=useState('Basmati');const[grade,setGrade]=useState('A');const[busy,setBusy]=useState(false);const[forecast,setForecast]=useState<any>(null);const[weather,setWeather]=useState<any>(null);useEffect(()=>{currentWeather(...cities.Surat).then(setWeather);},[]);async function load(e:FormEvent){e.preventDefault();setBusy(true);setForecast(null);try{setForecast(await api(`/forecast?crop=${crop}&market=${encodeURIComponent(market)}&variety=${encodeURIComponent(variety)}&grade=${grade}`));}catch{setForecast({status:'unavailable',message:'No validated model is available for this market, variety and grade.'});}finally{setBusy(false);}}const days=weather?.daily?.time?.map((d:string,i:number)=>({date:d.slice(5),temperature:weather.daily.temperature_2m_max[i],rain:weather.daily.precipitation_probability_max[i]}))||[];return <><div className="page-heading"><div><span className="eyeline">AHEAD OF THE HARVEST</span><h1>{t('Forecasts')}</h1><p>{t('Estimates need sufficient recent data. They are not guaranteed prices.')}</p></div><Badge tone="amber">{t('AI estimated')}</Badge></div><form onSubmit={load}><Panel className="filter-panel"><div className="form-grid filters"><Field label="Crop"><select disabled={busy} value={crop} onChange={e=>{setCrop(e.target.value as CropName);setForecast(null);}}>{crops.map(c=><option value={c} key={c}>{t(c)}</option>)}</select></Field><Field label="Market"><input disabled={busy} required maxLength={150} value={market} onChange={e=>{setMarket(e.target.value);setForecast(null);}}/></Field><Field label="Variety"><input disabled={busy} required maxLength={100} value={variety} onChange={e=>{setVariety(e.target.value);setForecast(null);}}/></Field><Field label="Grade"><select disabled={busy} value={grade} onChange={e=>{setGrade(e.target.value);setForecast(null);}}>{['A','B','C'].map(g=><option key={g}>{g}</option>)}</select></Field></div><button className="btn" disabled={busy}>{busy?<Busy/>:<><Sparkles size={17}/>{t('View forecast')}</>}</button></Panel></form><div className="forecast-grid mt"><Panel><div className="section-head"><h2>{t('Price forecast')}</h2><BarChart3 size={20}/></div>{forecast?.status==='estimated'?<><Note>{t('AI estimated')} · MAE {rupee(forecast.validation_mae)}</Note><ResponsiveContainer width="100%" height={250}><LineChart data={forecast.records}><CartesianGrid vertical={false}/><XAxis dataKey="date" tick={{fontSize:12}}/><YAxis tick={{fontSize:12}}/><Tooltip/><Line dataKey="price" stroke="#2f7a4f" strokeWidth={3}/></LineChart></ResponsiveContainer><Source name="XGBoost · chronological holdout validation" date={forecast.trained_through}/></>:<Empty title="No forecast available" description={forecast?.message||'Select a market to check whether a validated model is available.'}/>}</Panel><DemandForecastPanel forecast={forecast?.demand_details}/></div><Panel className="mt"><div className="section-head"><div><h2>{t('Weather outlook')}</h2><p>Surat · {t('Next 7 days')}</p></div><CloudSun size={24}/></div>{days.length?<><ResponsiveContainer width="100%" height={240}><LineChart data={days}><CartesianGrid vertical={false} stroke="#e4eddd"/><XAxis dataKey="date" tick={{fontSize:12}}/><YAxis tick={{fontSize:12}} unit="°"/><Tooltip formatter={(v:any)=>v+' °C'}/><Line dataKey="temperature" stroke="#658c45" strokeWidth={3} dot={{r:3}}/></LineChart></ResponsiveContainer><Source name="Open-Meteo · daily maximum temperature" url="https://open-meteo.com/"/></>:<Empty title="Weather unavailable"/>}<Note>{t('Use the weather outlook for handling and travel planning. No crop-price impact is inferred without a validated model.')}</Note></Panel></>}
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
     <Field label="Email"><input disabled value={user?.email||'—'}/></Field>
     <Field label="Account role"><input disabled value={t(role==='farmer'?'Farmer':role==='buyer'?'Buyer':'FPO')}/></Field>
     <Field label="Language"><select value={lang} onChange={e=>setLang(e.target.value as typeof lang)}><option value="en">English</option><option value="gu">ગુજરાતી</option><option value="hi">हिन्दी</option><option value="mr">मराठी</option></select></Field>
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
['FR8','Published full-truck prices on the Surat–Mumbai route.','https://www.fr8.in/transport-service/surat-transport-service/surat-to-mumbai/'],
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
 ].map(([q,a])=><details key={q}><summary>{t(q)}</summary><p>{t(a)}</p></details>)}<Source name="The Green Field by Abhijeet Sawant · CC BY-SA 3.0 · displayed with a crop" url="https://commons.wikimedia.org/wiki/File:The_Green_Field.jpg"/><Source name="Creative Commons Attribution-ShareAlike 3.0" url="https://creativecommons.org/licenses/by-sa/3.0/"/></Panel></>}
