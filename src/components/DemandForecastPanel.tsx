import {LineChart,Line,XAxis,YAxis,CartesianGrid,Tooltip,ResponsiveContainer} from 'recharts';
import {Sparkles} from 'lucide-react';
import {Panel,Note,Source,Empty} from './ui';
import {useLanguage} from '../lib/i18n';

export type DemandForecast={
 status:'estimated'|'unavailable';
 records:{date:string;quantity:number}[];
 message?:string;
 validation_mae?:number;
 trained_through?:string;
 source?:string;
};

export function DemandForecastPanel({forecast}:{forecast?:DemandForecast}){
 const{t}=useLanguage();
 return <Panel>
  <div className="section-head"><h2>{t('Demand forecast')}</h2><Sparkles size={20}/></div>
  {forecast?.status==='estimated'&&forecast.records.length>0?<>
   <Note>{t('Estimated buyer requests')} · {t('Quintals per day')}</Note>
   <ResponsiveContainer width="100%" height={250}>
    <LineChart data={forecast.records}>
     <CartesianGrid vertical={false}/><XAxis dataKey="date" tick={{fontSize:12}}/>
     <YAxis tick={{fontSize:12}} domain={[0,'auto']}/>
     <Tooltip formatter={(value)=>[`${Number(value).toLocaleString(undefined,{maximumFractionDigits:2})} ${t('quintals')}`,t('Estimated buyer requests')]}/>
     <Line dataKey="quantity" stroke="#739751" strokeWidth={3}/>
    </LineChart>
   </ResponsiveContainer>
   <p className="muted">{t('Validation error')} · {forecast.validation_mae?.toFixed(2)} {t('quintals')}</p>
   <p className="muted">{t('Estimates cover recorded buyer requests, not completed sales or the entire market.')}</p>
   <Source name={forecast.source||'XGBoost'} date={forecast.trained_through}/>
  </>:<Empty title="No forecast available" description={forecast?.message||'Verified daily buyer-demand history is required. Arrivals alone do not establish demand.'}/>}
 </Panel>;
}
