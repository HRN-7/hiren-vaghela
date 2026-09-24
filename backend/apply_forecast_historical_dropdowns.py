from pathlib import Path

ROOT = Path.cwd()
main_path = ROOT / "backend" / "app" / "main.py"
options_path = ROOT / "backend" / "app" / "forecast_options.py"
misc_path = ROOT / "src" / "pages" / "Misc.tsx"

options_code = r"""import csv
from pathlib import Path

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api", tags=["forecast"])

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "gujarat_discovery"
ELIGIBLE = DATA_DIR / "eligible_120_plus.csv"
VALIDATED = DATA_DIR / "validated_price_trend_models.csv"
ALLOWED_CROPS = {"Cotton", "Wheat", "Groundnut", "Rice"}


def _read_csv(path: Path):
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


@router.get("/forecast/options")
def forecast_options(crop: str = Query(...)):
    if crop not in ALLOWED_CROPS:
        return {
            "status": "unavailable",
            "crop": crop,
            "records": [],
            "message": "Unsupported crop.",
        }

    eligible = _read_csv(ELIGIBLE)
    validated_rows = _read_csv(VALIDATED)

    validated = {
        (
            row.get("crop", "").strip(),
            row.get("market", "").strip(),
            row.get("variety", "").strip(),
        )
        for row in validated_rows
    }

    records = []
    seen = set()

    for row in eligible:
        if row.get("crop", "").strip() != crop:
            continue

        market = row.get("market", "").strip()
        variety = row.get("variety", "").strip()

        if not market or not variety:
            continue

        key = (crop, market, variety)
        if key in seen:
            continue
        seen.add(key)

        try:
            observed_days = int(row.get("observed_days") or 0)
        except ValueError:
            observed_days = 0

        records.append({
            "market": market,
            "variety": variety,
            "observed_days": observed_days,
            "oldest_date": row.get("oldest_date"),
            "newest_date": row.get("newest_date"),
            "validated": key in validated,
        })

    records.sort(
        key=lambda r: (
            not r["validated"],
            -r["observed_days"],
            r["market"].casefold(),
            r["variety"].casefold(),
        )
    )

    return {
        "status": "available" if records else "unavailable",
        "crop": crop,
        "records": records,
        "market_count": len({r["market"] for r in records}),
        "scope_count": len(records),
        "message": (
            "Markets and varieties come from verified Gujarat historical mandi "
            "coverage with at least 120 observed reporting days. AI forecast is "
            "shown only for combinations whose model passed chronological validation."
            if records
            else "No eligible historical market and variety coverage is available."
        ),
    }
"""

forecast_component = r"""export function Forecasts(){
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

"""

options_path.write_text(options_code, encoding="utf-8")

main = main_path.read_text(encoding="utf-8")
import_line = "from .forecast_options import router as forecast_options_router"
include_line = "app.include_router(forecast_options_router)"

if import_line not in main:
    main = main.rstrip() + "\n\n" + import_line + "\n"

if include_line not in main:
    main = main.rstrip() + "\n" + include_line + "\n"

main_path.write_text(main, encoding="utf-8")

misc = misc_path.read_text(encoding="utf-8")
start = misc.find("export function Forecasts()")
end = misc.find("type AccountNotification")

if start == -1 or end == -1 or end <= start:
    raise RuntimeError("Could not locate Forecasts() block in Misc.tsx")

misc = misc[:start] + forecast_component + "\n" + misc[end:]
misc_path.write_text(misc, encoding="utf-8")

print("Forecast dropdown patch applied.")
print("Backend options endpoint: /api/forecast/options")
print("Uses eligible_120_plus.csv for all four crops.")
print("AI-validated combinations are marked from validated_price_trend_models.csv.")
