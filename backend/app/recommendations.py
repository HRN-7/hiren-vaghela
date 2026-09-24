"""Crop-scoped market discovery and provider-costed comparisons. No sample fallback."""
import asyncio
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import math
import secrets
import time
from zoneinfo import ZoneInfo
import httpx
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, ValidationError
from . import providers
from .config import settings

SOURCE_URL='https://www.data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi'
SNAPSHOTS=OrderedDict()
GEO_LOCK=asyncio.Lock()
GEO_LAST=0.0
GEO_CACHE={}
MAX_PRICE_AGE_DAYS=7


def norm(value):return ''.join(c for c in str(value).casefold() if c.isalnum())
def now():return datetime.now(timezone.utc)
def day():return datetime.now(ZoneInfo('Asia/Kolkata')).date()
def digest(value):return sha256(json.dumps(value,sort_keys=True,default=str).encode()).hexdigest()
def crop_context(crop):
    return {k:getattr(crop,k) if not isinstance(crop,dict) else crop[k] for k in ['name','variety','grade','quantity','location','sell_date','parameters']}

def market_id(row):return digest({k:row.get(k,'') for k in ['state','district','market']})[:24]

async def geocode(location):
    """A cached, throttled forward lookup; never assumes Surat for an unknown location."""
    global GEO_LAST
    key=location.casefold().strip()
    if key in GEO_CACHE and time.monotonic()-GEO_CACHE[key][0]<86400:return GEO_CACHE[key][1]
    try:
        async with GEO_LOCK:
            await asyncio.sleep(max(0,1.1-(time.monotonic()-GEO_LAST)))
            GEO_LAST=time.monotonic()
            data=await providers.fetch_json(settings().nominatim_url.rstrip('/')+'/search',{'q':location+', India','format':'jsonv2','addressdetails':1,'countrycodes':'in','limit':1},ttl=86400)
        item=data[0];address=item.get('address',{})
        if address.get('country_code')!='in' or not address.get('state'):return None
        result={'lat':float(item['lat']),'lon':float(item['lon']),'state':address['state'],'district':address.get('state_district',address.get('county','')),'label':item['display_name'],'precision':'map location','source':'OpenStreetMap / Nominatim','source_url':'https://www.openstreetmap.org/'}
        if not (-90<=result['lat']<=90 and -180<=result['lon']<=180):return None
        if len(GEO_CACHE)>512:GEO_CACHE.clear()
        GEO_CACHE[key]=(time.monotonic(),result)
        return result
    except Exception:return None


async def geocode_market(row):
    """Map a mandi conservatively; district fallback is never treated as exact."""
    market = str(row.get("market", "")).strip()
    district = str(row.get("district", "")).strip()
    state = str(row.get("state", "")).strip()

    cleaned_market = market
    for token in [" APMC", "APMC ", " Market Yard", " Mandi"]:
        cleaned_market = cleaned_market.replace(token, " ").strip()

    queries = []
    for q in [
        ", ".join(filter(None, [market, district, state])),
        ", ".join(filter(None, [cleaned_market, district, state])),
        ", ".join(filter(None, [cleaned_market, state])),
    ]:
        if q and q not in queries:
            queries.append(q)

    for q in queries:
        point = await geocode(q)
        if point:
            return {
                **point,
                "market_location_verified": True,
                "market_location_precision": point.get("precision", "mapped market/locality"),
            }

    if district:
        point = await geocode(", ".join(filter(None, [district, state])))
        if point:
            return {
                **point,
                "market_location_verified": False,
                "market_location_precision": "district centroid fallback",
            }

    return None

def relevant_prices(feed,context):
    """Latest per real market; farmer A/B/C grade is carried explicitly."""
    selected={}
    requested_variety=norm(context['variety'])
    requested_grade=norm(context['grade'])
    unspecified=requested_variety in ['other','othernotlisted','']
    generic={'','other','others','local','faq',norm(context['name'])}

    for row in feed.get('records',[]):
        try:
            if norm(row['crop'])!=norm(context['name']):continue

            age=(day()-datetime.fromisoformat(row['date']).date()).days
            if age<0 or age>MAX_PRICE_AGE_DAYS:continue

            price=float(row['price'])
            if not math.isfinite(price) or price<=0:continue

            variety=norm(row.get('variety',''))
            reported_grade=norm(row.get('grade',''))

            if not unspecified and variety!=requested_variety and variety not in generic:
                continue

            if reported_grade in ['a','b','c'] and reported_grade!=requested_grade:
                continue

            grade_verified=(
                reported_grade in ['a','b','c']
                and reported_grade==requested_grade
            )
            exact=not unspecified and variety==requested_variety

            r={
                **row,
                'id':market_id(row),
                'age_days':age,
                'requested_grade':context['grade'],
                'reported_grade':row.get('grade',''),
                'grade_verified':grade_verified,
                'grade_compatibility':'verified' if grade_verified else 'unverified',
                'variety_match':'reported variety' if exact else 'variety not confirmed',
                'grade_match':(
                    f"Verified provider grade {context['grade']} match."
                    if grade_verified
                    else "Provider grade is not a verified match to the farmer's A/B/C grade. Keep this market unconfirmed for net-realization ranking."
                ),
                'source':feed['source'],
                'source_url':feed.get('source_url',SOURCE_URL),
                'fetched_at':feed.get('fetched_at'),
                'price_basis':'Published modal price; expected sale price is an estimate.'
            }

            current=selected.get(r['id'])
            order=(
                int(grade_verified),
                int(exact),
                r['date'],
                norm(r.get('variety','')),
                norm(r.get('grade',''))
            )
            if not current or order>current[0]:
                selected[r['id']]=(order,r)

        except (KeyError,ValueError,TypeError):
            continue

    return [item[1] for item in selected.values()]


def market_trend(context,row):
    """Attach validated AI timing trend when this exact market+variety model exists."""
    try:
        from .forecast import predict as predict_price

        result=predict_price(
            context['name'],
            row['market'],
            row.get('variety') or context['variety'],
            context['grade']
        )

        records=result.get('records') or []

        if result.get('status')!='estimated' or not records:
            return {
                'status':'unavailable',
                'signal':'unavailable',
                'grade_specific':False,
                'message':result.get(
                    'message',
                    'No validated AI trend is available for this market and variety.'
                )
            }

        first=float(records[0]['price'])
        last=float(records[-1]['price'])
        change_pct=((last-first)/first*100) if first else 0.0

        if change_pct>0.5:
            signal='rising'
        elif change_pct<-0.5:
            signal='falling'
        else:
            signal='stable'

        return {
            'status':'estimated',
            'signal':signal,
            'change_pct':round(change_pct,2),
            'first_estimate':round(first,2),
            'last_estimate':round(last,2),
            'trained_through':result.get('trained_through'),
            'validation_mae':result.get('validation_mae'),
            'baseline_mae':result.get('baseline_mae'),
            'grade_specific':bool(result.get('grade_specific')),
            'recommendation_use':result.get(
                'recommendation_use',
                'timing_trend_only'
            ),
            'message':result.get('grade_basis') or result.get('message')
        }

    except Exception:
        return {
            'status':'unavailable',
            'signal':'unavailable',
            'grade_specific':False,
            'message':'AI trend could not be loaded for this market.'
        }


async def discover(context):
    base={'source':'AGMARKNET via data.gov.in','source_url':SOURCE_URL,'records':[],'context':context,'fetched_at':providers.stamp()}
    if not settings().data_gov_api_key:return {**base,'status':'unavailable','message':'Live mandi prices are not connected yet. No example prices are used.'}
    origin=await geocode(context['location'])
    if not origin:return {**base,'status':'unavailable','message':'We could not locate this crop. Include village/town, district and state in Crop Details.'}
    feed=await providers.prices(context['name'],origin['state'])
    base.update({k:feed[k] for k in ['status','source','source_url','fetched_at','message','truncated'] if k in feed})
    candidates=relevant_prices(feed,context)
    if not candidates:return {**base,'origin':origin,'status':'unavailable','message':feed.get('message') or 'No matching variety/grade reports from the last 7 days. Other crops, varieties and old PDF prices are not substituted.'}
    from .price_history import record_snapshot
    await asyncio.to_thread(record_snapshot,feed,context['name'],origin['state'])
    # Look up the nearest administrative matches first, with a bounded public-geocoder workload.
    candidates.sort(key=lambda r:(norm(r.get('district','')) not in norm(context['location']),r['market']))
    found=[]
    for row in candidates[:12]:
        point=await geocode_market(row)
        if not point:continue
        straight=providers.distance(origin['lat'],origin['lon'],point['lat'],point['lon'])
        if straight>250:continue
        found.append({
            **row,
            'coordinates':point,
            'straight_distance_km':straight,
            'market_location_verified':bool(point.get('market_location_verified')),
            'market_location_precision':point.get('market_location_precision')
        })
    found.sort(key=lambda r:r['straight_distance_km']);found=found[:8]
    routes=await asyncio.gather(*(providers.route(origin['lat'],origin['lon'],r['coordinates']['lat'],r['coordinates']['lon']) for r in found))
    for row,route in zip(found,routes):
        row['distance_km']=route.get('distance_km');row['distance_source']='OSRM / OpenStreetMap';row['distance_note']='Estimated driving distance to the mapped market/locality; confirm the unloading point and truck route.'
        row['ai_trend']=market_trend(context,row)
    return {**base,'status':'available' if found else 'unavailable','origin':origin,'records':found,'search_limited':len(candidates)>12 or bool(feed.get('truncated')),'message':'Latest available matching reports in your state within 250 km straight-line. Road distances are estimates.' if found else 'No nearby reporting markets could be mapped for this crop. Try a more precise crop location.','date':max((r['date'] for r in found),default=None)}

class Quote(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    id:str=Field(min_length=1,max_length=100)
    name:str=Field(min_length=1,max_length=180)
    market_id:str
    source:str=Field(min_length=1,max_length=180)
    source_url:HttpUrl
    updated_at:datetime
    valid_until:datetime
    estimated:bool
    available:bool

class TransportQuote(Quote):
    vehicle:str=Field(min_length=1,max_length=120)
    storage_id:str|None=None
    capacity_quintals:float=Field(gt=0,le=1000)
    rate_per_km:float=Field(ge=0,le=100000)
    minimum_trip_cost:float=Field(ge=0,le=10000000)
    fixed_trip_cost:float=Field(ge=0,le=10000000)
    tolls_per_trip:float=Field(ge=0,le=10000000)
    loading_per_quintal:float=Field(ge=0,le=10000000)
    unloading_per_quintal:float=Field(ge=0,le=10000000)
    all_transport_costs_included:bool

class StorageQuote(Quote):
    crops:list[str]
    compatible:bool
    capacity_quintals:float=Field(gt=0,le=10000000)
    lat:float=Field(ge=-90,le=90)
    lon:float=Field(ge=-180,le=180)
    rate_per_quintal_day:float=Field(ge=0,le=10000000)
    handling_per_quintal:float=Field(ge=0,le=10000000)
    finance_per_quintal_day:float=Field(ge=0,le=10000000)
    loss_percent:float=Field(ge=0,le=100)
    minimum_days:int=Field(ge=1,le=365)
    all_storage_costs_included:bool

class ChargeQuote(Quote):
    market_fee_percent:float=Field(ge=0,le=100)
    commission_per_quintal:float=Field(ge=0,le=10000000)
    other_per_quintal:float=Field(ge=0,le=10000000)
    other_description:str=Field(min_length=1,max_length=500)
    all_selling_costs_included:bool


def valid_quote(q):
    current=now()
    return q.available and q.source_url.scheme=='https' and q.updated_at.tzinfo is not None and q.valid_until.tzinfo is not None and current-timedelta(hours=24)<=q.updated_at<=current+timedelta(minutes=1) and q.valid_until>current

async def service_options(context,feed,storage_days):
    cfg=settings();result={'transport':[],'storage':[],'charges':[],'message':'Transport quotes, storage tariffs and market charges are not connected. Missing costs stay unknown.'}
    if not cfg.partner_data_url or not cfg.partner_api_key or not feed['records']:return result
    payload={'crop':context,'origin':feed['origin'],'markets':[{k:r[k] for k in ['id','market','district','state','coordinates','date']} for r in feed['records']],'storage_days':storage_days}
    scope=digest(payload)
    try:
        async with httpx.AsyncClient(timeout=15,follow_redirects=False) as client:
            response=await client.post(cfg.partner_data_url.rstrip('/')+'/recommendation-options',json={**payload,'request_fingerprint':scope},headers={'Authorization':'Bearer '+cfg.partner_api_key})
            response.raise_for_status();data=response.json()
        if data.get('request_fingerprint')!=scope:raise ValueError('Wrong quote context')
        market_ids={r['id'] for r in feed['records']}
        for key,model in [('transport',TransportQuote),('storage',StorageQuote),('charges',ChargeQuote)]:
            seen=set()
            for record in sorted(data.get(key,[])[:100],key=lambda r:str(r.get('updated_at','')),reverse=True):
                try:
                    q=model.model_validate(record)
                    identity=q.market_id if key=='charges' else (q.market_id,q.id)
                    if not valid_quote(q) or q.market_id not in market_ids or identity in seen:continue
                    if key=='storage' and (not q.compatible or context['name'] not in q.crops or q.capacity_quintals<context['quantity'] or providers.distance(feed['origin']['lat'],feed['origin']['lon'],q.lat,q.lon)>50):continue
                    seen.add(identity);result[key].append(q.model_dump(mode='json'))
                except (ValidationError,TypeError,ValueError):continue
        result['message']='Provider-reported quotes for this crop, quantity, location and route. Check source dates and validity.'
        return result
    except Exception:return {**result,'message':'Service quotes could not be confirmed for this crop. Prices remain visible; incomplete options are not recommended.'}

async def create_options(context,owner=None,storage_days=0):
    feed=await discover(context)
    services=await service_options(context,feed,storage_days)
    # Store road distance through each eligible facility; no straight-line substitute in costs.
    if storage_days and feed.get('origin'):
        for facility in services['storage']:
            market=next(r for r in feed['records'] if r['id']==facility['market_id']);origin=feed['origin'];dest=market['coordinates']
            a,b=await asyncio.gather(providers.route(origin['lat'],origin['lon'],facility['lat'],facility['lon']),providers.route(facility['lat'],facility['lon'],dest['lat'],dest['lon']))
            facility['route_distance_km']=round(a['distance_km']+b['distance_km'],1) if a.get('distance_km') is not None and b.get('distance_km') is not None else None
    ident=secrets.token_urlsafe(24);expires=now()+timedelta(minutes=10)
    result={**feed,'services':services,'snapshot_id':ident,'expires_at':expires.isoformat(),'storage_days':storage_days}
    result['suggested_selections']=suggest_choices(result)
    SNAPSHOTS[ident]={'owner':owner,'fingerprint':digest(context),'result':result,'expires':expires}
    while len(SNAPSHOTS)>256:SNAPSHOTS.popitem(last=False)
    return result


def get_snapshot(ident,context,owner):
    saved=SNAPSHOTS.get(ident)
    if not saved or saved['owner']!=owner:raise HTTPException(409,'Market options expired. Refresh suggestions.')
    if saved['expires']<=now() or saved['fingerprint']!=digest(context):raise HTTPException(409,'Crop details or quote validity changed. Refresh suggestions.')
    return saved['result']


def compute_option(market,transport,storage,charges,quantity,storage_days):
    missing=[];price=market['price'];transport_cost=None;storage_cost=0 if storage_days==0 else None;market_cost=None;other_cost=None;details=[]
    if not market.get('grade_verified'):missing.append('Verified A/B/C grade compatibility')
    distance=storage.get('route_distance_km') if storage else market.get('distance_km')
    if distance is None or not math.isfinite(distance) or distance<0:distance=None;missing.append('Road distance')
    if not market.get('market_location_verified',True):missing.append('Exact market unloading location')
    if (day()-datetime.fromisoformat(market['date']).date()).days>MAX_PRICE_AGE_DAYS:missing.append('Recent market report')
    def usable(raw,model,coverage):
        try:q=model.model_validate({k:v for k,v in raw.items() if k!='route_distance_km'})
        except (ValidationError,TypeError,AttributeError):return False
        return valid_quote(q) and getattr(q,coverage)
    if not transport or not usable(transport,TransportQuote,'all_transport_costs_included'):missing.append('Complete transport quote')
    elif distance is not None:
        trips=math.ceil(quantity/transport['capacity_quintals'])
        trip=max(transport['minimum_trip_cost'],transport['fixed_trip_cost']+distance*transport['rate_per_km'])+transport['tolls_per_trip']
        transport_cost=trip*trips/quantity+transport['loading_per_quintal']+transport['unloading_per_quintal']
        details.append({'label':'Transport (fuel/driver/base rate + tolls + loading/unloading)','per_quintal':round(transport_cost,2),'trips':trips,'distance_km':distance,'source':transport['source'],'source_url':transport['source_url'],'date':transport['updated_at']})
    if storage_days:
        if not storage or not usable(storage,StorageQuote,'all_storage_costs_included') or storage['capacity_quintals']<quantity:missing.append('Compatible storage with complete tariff')
        else:
            billed_days=max(storage_days,storage['minimum_days'])
            storage_cost=billed_days*(storage['rate_per_quintal_day']+storage['finance_per_quintal_day'])+storage['handling_per_quintal']+price*storage['loss_percent']/100
            details.append({'label':'Storage rent, handling, finance and estimated loss','per_quintal':round(storage_cost,2),'billed_days':billed_days,'source':storage['source'],'source_url':storage['source_url'],'date':storage['updated_at']})
    if not charges or not usable(charges,ChargeQuote,'all_selling_costs_included'):missing.append('Market charges and other applicable costs')
    else:
        market_cost=price*charges['market_fee_percent']/100+charges['commission_per_quintal'];other_cost=charges['other_per_quintal']
        details.extend([{'label':'Market fee and commission','per_quintal':round(market_cost,2),'source':charges['source'],'source_url':charges['source_url'],'date':charges['updated_at']},{'label':charges['other_description'],'per_quintal':round(other_cost,2),'source':charges['source'],'source_url':charges['source_url'],'date':charges['updated_at']}])
    costs=[transport_cost,storage_cost,market_cost,other_cost]
    total_cost=None if missing else sum(costs)
    net=None if total_cost is None else price-total_cost
    return {**market,'transport':transport,'storage':storage,'distance_km':distance,'transport_cost':round(transport_cost,2) if transport_cost is not None else None,'storage_cost':round(storage_cost,2) if storage_cost is not None else None,'market_charges':round(market_cost,2) if market_cost is not None else None,'other_costs':round(other_cost,2) if other_cost is not None else None,'net_per_quintal':round(net,2) if net is not None else None,'total_expected':round(net*quantity,2) if net is not None else None,'total_selling_cost':round(total_cost*quantity,2) if total_cost is not None else None,'missing':missing,'breakdown':details,'estimated':True}


def compare_options(snapshot,selections):
    if len(selections) not in [2,3] or len({s.market_id for s in selections})!=len(selections):raise HTTPException(422,'Choose 2 or 3 different markets.')
    output=[];services=snapshot['services'];quantity=snapshot['context']['quantity'];days=snapshot['storage_days']
    for choice in selections:
        market=next((r for r in snapshot['records'] if r['id']==choice.market_id),None)
        if not market:raise HTTPException(422,'Selected market is not in these crop suggestions.')
        if not days and choice.storage_id:raise HTTPException(422,'Storage was not requested.')
        storage=next((s for s in services['storage'] if s['market_id']==choice.market_id and s['id']==choice.storage_id),None) if choice.storage_id else None
        if choice.storage_id and not storage:raise HTTPException(422,'Selected storage is not suitable for this crop and market.')
        transport=next((s for s in services['transport'] if s['market_id']==choice.market_id and s['id']==choice.transport_id and s['storage_id']==choice.storage_id),None) if choice.transport_id else None
        if choice.transport_id and not transport:raise HTTPException(422,'Transport quote does not cover the selected route and storage.')
        charges=next((s for s in services['charges'] if s['market_id']==choice.market_id),None)
        output.append(compute_option(market,transport,storage,charges,quantity,days))
    ranked=sorted([r for r in output if not r['missing']],key=lambda r:(-r['net_per_quintal'],r['distance_km'],r['id']))
    for index,row in enumerate(ranked):row['rank']=index+1
    complete=len(ranked)==len(output)
    valid_until=[datetime.fromisoformat(snapshot['expires_at'])]
    for selected_row in output:
        for quote in [selected_row.get('transport'),selected_row.get('storage')]:
            if quote:valid_until.append(datetime.fromisoformat(quote['valid_until']))
        for quote in services['charges']:
            if quote['market_id']==selected_row['id']:valid_until.append(datetime.fromisoformat(quote['valid_until']))
    # A priced subset cannot establish the winner over markets with unknown costs.
    best=ranked[0] if complete else None
    return {'status':'estimated' if complete else 'incomplete','context':snapshot['context'],'ranking':ranked+[r for r in output if r['missing']],'best_market_id':best['id'] if best else None,'source':snapshot['source'],'source_url':snapshot['source_url'],'calculated_at':providers.stamp(),'expires_at':min(valid_until).isoformat(),'storage_days':days,'message':'Highest expected net realization among your selected markets, using reported prices and sourced cost estimates.' if best else 'A best market cannot be confirmed until every selected option has complete costs. Unknown costs are not treated as zero.','price_warning':'Farmer A/B/C grade is mandatory. Markets with unverified grade compatibility are not confirmed or ranked for net realization. Modal prices are indicative, not sale guarantees.','timing_warning':'Storage costs use the latest reported price, not a prediction of the selling-date price.' if days else None}


def suggest_choices(snapshot):
    suggestions=[];services=snapshot['services'];days=snapshot['storage_days'];quantity=snapshot['context']['quantity']
    for market in snapshot['records']:
        if not market.get('grade_verified'):
            continue
        charges=next((s for s in services['charges'] if s['market_id']==market['id']),None)
        storages=[s for s in services['storage'] if s['market_id']==market['id']] if days else [None]
        options=[]
        for storage in storages:
            sid=storage['id'] if storage else None
            for transport in services['transport']:
                if transport['market_id']!=market['id'] or transport['storage_id']!=sid:continue
                costed=compute_option(market,transport,storage,charges,quantity,days)
                if not costed['missing']:options.append(costed)
        best=max(options,key=lambda x:x['net_per_quintal']) if options else None
        suggestions.append({'market_id':market['id'],'transport_id':best['transport']['id'] if best else None,'storage_id':best['storage']['id'] if best and best['storage'] else None,'expected_net':best['net_per_quintal'] if best else None})
    suggestions.sort(key=lambda x:(x['expected_net'] is None,-(x['expected_net'] or 0)))
    return [{k:v for k,v in r.items() if k!='expected_net'} for r in suggestions[:3]]
