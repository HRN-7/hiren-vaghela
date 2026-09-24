from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from io import BytesIO
from pathlib import Path
import hashlib, json, asyncio
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, delete, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from PIL import Image, ImageOps, UnidentifiedImageError
from .config import settings
from .db import User, Crop, Demand, FPO, Photo, FPOContribution, MarketPrice, PriceObservation, Record, Connection, Notification, PushToken, Purchase, get_db
from .auth import identity, current_user, admin
from .schemas import ProfileIn, CropIn, DemandIn, FPOIn, NetIn, CompareIn, InterestIn, TokenIn, CropName, PurchaseIn, PurchaseUpdate
from .schemas import MarketOptionsIn, MarketCompareIn, PreviewCompareIn
from . import recommendations as market_recommendations
from .engine import net_realization, rank
from . import providers
from .notifications import notify_user, remove_token, lifespan

app=FastAPI(title='KrishiLink AI',version='1.0.0',docs_url='/api/docs',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in settings().cors_origins.split(',') if x.strip()],allow_credentials=False,allow_methods=['GET','POST','PUT','DELETE','OPTIONS'],allow_headers=['Authorization','Content-Type'])

def serialize_crop(row,db):
    return {**serialize(row),'photos':list(db.scalars(select(Photo.id).where(Photo.crop_id==row.id)))}

def current_date():return datetime.now(ZoneInfo('Asia/Kolkata')).date()

def serialize(row, omit=()):
    return {c.name:getattr(row,c.name) for c in row.__table__.columns if c.name not in omit}
def own_crop(crop_id,user,db):
    row=db.scalar(select(Crop).where(Crop.id==crop_id,Crop.owner_id==user.id))
    if not row: raise HTTPException(404,'Crop not found.')
    return row

def role(user,*roles):
    if user.role not in roles: raise HTTPException(403,'This action is not available for your account role.')

@app.get('/api/health')
def health(): return {'status':'ok','accounts_configured':bool(settings().database_url and settings().firebase_project_id)}

@app.get('/api/status')
def status():
    s=settings()
    return {'auth':bool(s.firebase_project_id),'database':bool(s.database_url),'market':bool(s.data_gov_api_key),'service_partners':bool(s.partner_data_url and s.partner_api_key),'forecast':False}

@app.post('/api/auth/profile')
def create_profile(data:ProfileIn,claims=Depends(identity),db:Session=Depends(get_db)):
    if db.get(User,claims['uid']): raise HTTPException(409,'Profile already exists.')
    user=User(id=claims['uid'],**data.model_dump());db.add(user);db.commit()
    return serialize(user)

@app.get('/api/auth/me')
def me(user=Depends(current_user)): return serialize(user)

@app.put('/api/auth/me')
def update_profile(data:ProfileIn,user=Depends(current_user),db:Session=Depends(get_db)):
    if data.role!=user.role: raise HTTPException(400,'Contact support to change account role.')
    for k,v in data.model_dump().items(): setattr(user,k,v)
    db.commit();return serialize(user)

@app.get('/api/crops')
def crops(user=Depends(current_user),db:Session=Depends(get_db)):
    return [serialize_crop(r,db) for r in db.scalars(select(Crop).where(Crop.owner_id==user.id).order_by(Crop.created_at.desc()).limit(500))]

@app.post('/api/crops',status_code=201)
def add_crop(data:CropIn,user=Depends(current_user),db:Session=Depends(get_db)):
    role(user,'farmer','fpo')
    row=Crop(owner_id=user.id,**data.model_dump(exclude={'acknowledged'}));db.add(row);db.commit();return serialize_crop(row,db)

@app.put('/api/crops/{crop_id}')
def edit_crop(crop_id:str,data:CropIn,user=Depends(current_user),db:Session=Depends(get_db)):
    row=own_crop(crop_id,user,db)
    if db.scalar(select(Purchase.id).where(Purchase.crop_id==row.id,Purchase.status.in_(['accepted','completed'])).limit(1)):raise HTTPException(409,'This crop has agreed sales. Create a separate listing for additional produce.')
    for k,v in data.model_dump(exclude={'acknowledged'}).items(): setattr(row,k,v)
    db.commit();return serialize_crop(row,db)

@app.delete('/api/crops/{crop_id}',status_code=204)
def remove_crop(crop_id:str,user=Depends(current_user),db:Session=Depends(get_db)):
    row=own_crop(crop_id,user,db)
    if db.scalar(select(Purchase.id).where(Purchase.crop_id==row.id).limit(1)):raise HTTPException(409,'This crop has purchase records. Keep it for your transaction history.')
    db.execute(delete(Photo).where(Photo.crop_id==row.id));db.execute(delete(FPOContribution).where(FPOContribution.crop_id==row.id));db.delete(row);db.commit()

@app.post('/api/crops/{crop_id}/photos')
async def upload_photo(crop_id:str,file:UploadFile=File(...),user=Depends(current_user),db:Session=Depends(get_db)):
    row=db.scalar(select(Crop).where(Crop.id==crop_id,Crop.owner_id==user.id).with_for_update())
    if not row:raise HTTPException(404,'Crop not found.')
    if file.content_type not in ['image/jpeg','image/png','image/webp']:raise HTTPException(400,'Upload a JPG, PNG or WebP image.')
    content=await file.read(5*1024*1024+1)
    if not content or len(content)>5*1024*1024:raise HTTPException(413,'Photo must be non-empty and no larger than 5 MB.')
    # The same retry has the same id, including after a lost upload response.
    ident=hashlib.sha256(crop_id.encode()+content).hexdigest()[:36]
    existing=db.get(Photo,ident)
    if existing:return {'id':existing.id}
    if db.scalar(select(func.count()).select_from(Photo).where(Photo.crop_id==crop_id))>=3:raise HTTPException(400,'Maximum three photos per crop.')
    try:
        Image.MAX_IMAGE_PIXELS=20000000
        img=Image.open(BytesIO(content))
        if img.format not in ['JPEG','PNG','WEBP'] or img.width*img.height>20000000:raise ValueError()
        img.load();img=ImageOps.exif_transpose(img).convert('RGB');img.thumbnail((1600,1600))
        stream=BytesIO();img.save(stream,'JPEG',quality=85)
    except Exception:raise HTTPException(400,'Upload a valid JPG, PNG or WebP image below 20 megapixels.')
    photo=Photo(id=ident,crop_id=crop_id,content=stream.getvalue());db.add(photo);db.commit();return {'id':photo.id}

@app.delete('/api/crops/{crop_id}/photos/{photo_id}',status_code=204)
def remove_photo(crop_id:str,photo_id:str,user=Depends(current_user),db:Session=Depends(get_db)):
    own_crop(crop_id,user,db)
    photo=db.scalar(select(Photo).where(Photo.id==photo_id,Photo.crop_id==crop_id))
    if not photo:raise HTTPException(404,'Photo not found.')
    db.delete(photo);db.commit()

@app.get('/api/crops/{crop_id}/photos/{photo_id}')
def get_photo(crop_id:str,photo_id:str,user=Depends(current_user),db:Session=Depends(get_db)):
    own_crop(crop_id,user,db)
    photo=db.scalar(select(Photo).where(Photo.id==photo_id,Photo.crop_id==crop_id))
    if not photo: raise HTTPException(404)
    return Response(photo.content,media_type=photo.mime,headers={'Cache-Control':'private, no-store'})

@app.get('/api/supply')
def supply(crop:CropName='Cotton',user=Depends(current_user),db:Session=Depends(get_db)):
    role(user,'buyer','fpo')
    return [serialize(r,('owner_id','notes','parameters')) for r in db.scalars(select(Crop).where(Crop.public==True,Crop.name==crop,Crop.sell_date>=current_date()).limit(100))]

@app.get('/api/buyers')
def buyers(crop:CropName | None=None,db:Session=Depends(get_db)):
    q=select(Demand).where(Demand.required_by>=current_date())
    if crop:q=q.where(Demand.crop==crop)
    return [serialize(r,('owner_id',)) for r in db.scalars(q.limit(100))]

@app.get('/api/buyers/mine')
def own_demands(user=Depends(current_user),db:Session=Depends(get_db)):
    return [serialize(r) for r in db.scalars(select(Demand).where(Demand.owner_id==user.id))]

@app.post('/api/buyers',status_code=201)
def add_demand(data:DemandIn,user=Depends(current_user),db:Session=Depends(get_db)):
    role(user,'buyer');row=Demand(owner_id=user.id,**data.model_dump());db.add(row);db.commit();return serialize(row)

@app.delete('/api/buyers/{id}',status_code=204)
def remove_demand(id:str,user=Depends(current_user),db:Session=Depends(get_db)):
    row=db.scalar(select(Demand).where(Demand.id==id,Demand.owner_id==user.id))
    if not row:raise HTTPException(404)
    db.execute(delete(Connection).where(Connection.demand_id==id));db.delete(row);db.commit()

@app.post('/api/buyers/{id}/interest')
def interest(id:str,data:InterestIn,user=Depends(current_user),db:Session=Depends(get_db)):
    role(user,'farmer','fpo');d=db.get(Demand,id)
    if not d or d.required_by<current_date():raise HTTPException(404,'Requirement has expired.')
    db.add(Connection(owner_id=user.id,demand_id=id,message=data.message))
    notify_user(db,d.owner_id,f'{user.name} expressed interest in your {d.crop} requirement.')
    try:db.commit()
    except IntegrityError:db.rollback();raise HTTPException(409,'Interest already recorded.')
    return {'status':'recorded'}

@app.get('/api/connections')
def connections(user=Depends(current_user),db:Session=Depends(get_db)):
    q=select(Connection).join(Demand).where((Connection.owner_id==user.id)|(Demand.owner_id==user.id))
    return [serialize(c) for c in db.scalars(q)]

@app.get('/api/fpos')
def fpos(db:Session=Depends(get_db)):return [serialize(x,('owner_id',)) for x in db.scalars(select(FPO).limit(100))]

@app.post('/api/fpos')
def save_fpo(data:FPOIn,user=Depends(current_user),db:Session=Depends(get_db)):
    role(user,'fpo');row=db.scalar(select(FPO).where(FPO.owner_id==user.id))
    if not row:row=FPO(owner_id=user.id,**data.model_dump());db.add(row)
    else:
        used=db.scalar(select(func.coalesce(func.sum(Crop.quantity),0)).select_from(FPOContribution).join(Crop).where(FPOContribution.fpo_id==row.id,FPOContribution.accepted==True))
        if data.capacity<used:raise HTTPException(409,'Capacity cannot be lower than already accepted produce.')
        for k,v in data.model_dump().items():setattr(row,k,v)
        row.verified=False
    db.commit();return serialize(row)

@app.post('/api/fpos/{id}/contribute/{crop_id}')
def contribute(id:str,crop_id:str,user=Depends(current_user),db:Session=Depends(get_db)):
    own_crop(crop_id,user,db)
    fpo=db.get(FPO,id)
    if not fpo:raise HTTPException(404)
    row=FPOContribution(fpo_id=id,crop_id=crop_id,owner_id=user.id);db.add(row)
    notify_user(db,fpo.owner_id,'A farmer submitted produce for your FPO to review.')
    try:db.commit()
    except IntegrityError:db.rollback();raise HTTPException(409,'This crop was already submitted.')
    return serialize(row)

@app.get('/api/fpos/mine/contributions')
def contributions(user=Depends(current_user),db:Session=Depends(get_db)):
    q=select(FPOContribution,Crop).join(Crop,Crop.id==FPOContribution.crop_id).join(FPO,FPO.id==FPOContribution.fpo_id).where(FPO.owner_id==user.id)
    return [{**serialize(c),'crop':serialize(p,('owner_id','notes','parameters'))} for c,p in db.execute(q)]

@app.put('/api/fpos/contributions/{id}/accept')
def accept_contribution(id:str,user=Depends(current_user),db:Session=Depends(get_db)):
    row=db.scalar(select(FPOContribution).join(FPO).where(FPOContribution.id==id,FPO.owner_id==user.id))
    if not row:raise HTTPException(404)
    fpo=db.scalar(select(FPO).where(FPO.id==row.fpo_id).with_for_update())
    used=db.scalar(select(func.coalesce(func.sum(Crop.quantity),0)).select_from(FPOContribution).join(Crop).where(FPOContribution.fpo_id==fpo.id,FPOContribution.accepted==True))
    crop=db.get(Crop,row.crop_id)
    if not row.accepted and used+crop.quantity>fpo.capacity:raise HTTPException(409,'This request exceeds your remaining capacity.')
    if not row.accepted:notify_user(db,row.owner_id,f'{fpo.name} accepted your {crop.name} contribution.')
    row.accepted=True;db.commit();return serialize(row)

@app.get('/api/markets')
def markets():return {'states':['Gujarat','Jammu and Kashmir'],'source':'Select a state and fetch market prices to discover reporting mandis.'}

@app.get('/api/prices')
async def prices(crop:CropName='Cotton',state:str=Query('Gujarat',max_length=60),market:str=Query('',max_length=150)):
    from .price_history import record_snapshot
    feed=await providers.prices(crop,state,market)
    if feed.get('records'):
        stored=await asyncio.to_thread(record_snapshot,feed,crop,state,market)
        return {**feed,'history_storage':stored}
    return feed

@app.get('/api/prices/history')
def history(crop:CropName,market:str=Query(...,min_length=1,max_length=180),variety:str=Query('',max_length=100),grade:str=Query('',max_length=30),days:int=Query(30,ge=7,le=365),state:str=Query('',max_length=60),district:str=Query('',max_length=100),db:Session=Depends(get_db)):
    if state:
        rows=db.scalars(select(PriceObservation).where(PriceObservation.state==state,PriceObservation.district==district,PriceObservation.crop==crop,PriceObservation.market==market,PriceObservation.variety==variety,PriceObservation.grade==grade,PriceObservation.date>=current_date()-timedelta(days=days-1),PriceObservation.date<=current_date()).order_by(PriceObservation.date)).all()
        return {'status':'historical' if rows else 'unavailable','records':[serialize(r) for r in rows],'message':'Observed prices for this exact state, district, market, variety and grade. Missing days remain unknown.'}
    rows=db.scalars(select(MarketPrice).where(MarketPrice.crop==crop,MarketPrice.market==market,MarketPrice.variety==variety,MarketPrice.grade==grade,MarketPrice.date>=current_date()-timedelta(days=days),MarketPrice.date<=current_date()).order_by(MarketPrice.date)).all()
    return {'status':'historical' if rows else 'unavailable','records':[serialize(r) for r in rows],'message':'Only stored observations for this exact market, variety and grade are shown. Missing dates are not fabricated.'}

@app.get('/api/weather')
async def weather(lat:float=Query(21.1702,ge=-90,le=90),lon:float=Query(72.8311,ge=-180,le=180)):return await providers.weather(lat,lon)

@app.get('/api/route')
async def route(lat:float=Query(...,ge=-90,le=90),lon:float=Query(...,ge=-180,le=180),to_lat:float=Query(...,ge=-90,le=90),to_lon:float=Query(...,ge=-180,le=180)):return await providers.route(lat,lon,to_lat,to_lon)

@app.get('/api/storage')
async def storage(lat:float=Query(21.1702,ge=-90,le=90),lon:float=Query(72.8311,ge=-180,le=180),radius:int=Query(25,ge=1,le=50)):
    return await providers.partner_services('storage',lat,lon) or await providers.storage(lat,lon,radius)

@app.get('/api/transport')
async def transport():return await providers.transport()

@app.post('/api/net-realization')
def calculate(data:NetIn):return net_realization(**data.model_dump())

@app.post('/api/recommendation')
def recommendation(data:CompareIn,user=Depends(current_user),db:Session=Depends(get_db)):
    result={'status':'scenario','ranking':rank(data.opportunities),'timing':'Insufficient verified price history to recommend a selling date.','basis':'Your entered quotes and costs; not a live AI prediction.'}
    db.add(Record(owner_id=user.id,data=result));db.commit();return result

@app.get('/api/forecast')
def forecast(crop:CropName,market:str=Query(...,max_length=180),variety:str=Query('',max_length=100),grade:str=Query('',max_length=30)):
    from .forecast import predict
    from .demand_forecast import predict_demand
    price=predict(crop,market,variety,grade)
    demand=predict_demand(crop,market,variety,grade)
    return {**price,'demand':demand['records'],'demand_details':demand}

@app.get('/api/notifications')
def notifications(user=Depends(current_user),db:Session=Depends(get_db)):
    return [serialize(n,('owner_id',)) for n in db.scalars(select(Notification).where(Notification.owner_id==user.id).limit(100))]

@app.put('/api/notifications/{id}/read')
def read_notification(id:str,user=Depends(current_user),db:Session=Depends(get_db)):
    row=db.scalar(select(Notification).where(Notification.id==id,Notification.owner_id==user.id))
    if not row:raise HTTPException(404,'Notification not found.')
    row.read=True;db.commit();return serialize(row,('owner_id',))

@app.post('/api/notifications/token')
def push_token(data:TokenIn,user=Depends(current_user),db:Session=Depends(get_db)):
    existing=db.get(PushToken,data.token)
    if existing and existing.owner_id!=user.id:raise HTTPException(409,'Push subscription belongs to another account.')
    if not existing:db.add(PushToken(token=data.token,owner_id=user.id));db.commit()
    return {'status':'subscribed'}

@app.delete('/api/notifications/token',status_code=204)
def unsubscribe_token(data:TokenIn,user=Depends(current_user),db:Session=Depends(get_db)):
    existing=db.get(PushToken,data.token)
    if existing and existing.owner_id!=user.id:raise HTTPException(404,'Subscription not found.')
    if existing:remove_token(db,data.token);db.commit()

@app.get('/api/admin/review')
def review(claims=Depends(admin),db:Session=Depends(get_db)):
    return {'buyers':[serialize(r) for r in db.scalars(select(Demand).where(Demand.verified==False))],'fpos':[serialize(r) for r in db.scalars(select(FPO).where(FPO.verified==False))]}

@app.post('/api/admin/verify/{kind}/{id}')
def verify(kind:str,id:str,claims=Depends(admin),db:Session=Depends(get_db)):
    model={'buyer':Demand,'fpo':FPO}.get(kind)
    if not model:raise HTTPException(400)
    row=db.get(model,id)
    if not row:raise HTTPException(404)
    row.verified=True;db.commit();return {'status':'verified'}


@app.get('/api/fpos/mine')
def own_fpo(user=Depends(current_user),db:Session=Depends(get_db)):
    role(user,'fpo')
    row=db.scalar(select(FPO).where(FPO.owner_id==user.id))
    return serialize(row) if row else None

@app.get('/api/buyer/summary')
def buyer_summary(user=Depends(current_user),db:Session=Depends(get_db)):
    role(user,'buyer')
    return {'demands':[serialize(d) for d in db.scalars(select(Demand).where(Demand.owner_id==user.id).order_by(Demand.created_at.desc()))],
      'available':db.scalar(select(func.count()).select_from(Crop).where(Crop.public==True,Crop.sell_date>=current_date())),
      'completed':db.scalar(select(func.count()).select_from(Purchase).where(Purchase.buyer_id==user.id,Purchase.status=='completed'))}

@app.get('/api/purchases')
def purchases(user=Depends(current_user),db:Session=Depends(get_db)):
    role(user,'farmer','buyer')
    rows=db.execute(select(Purchase,Crop).join(Crop).where((Purchase.buyer_id==user.id)|(Purchase.seller_id==user.id)).order_by(Purchase.created_at.desc()))
    return [{**serialize(p),'crop_name':c.name,'variety':c.variety,'location':c.location} for p,c in rows]

@app.post('/api/purchases',status_code=201)
def request_purchase(data:PurchaseIn,user=Depends(current_user),db:Session=Depends(get_db)):
    role(user,'buyer')
    crop=db.scalar(select(Crop).where(Crop.id==data.crop_id,Crop.public==True,Crop.sell_date>=current_date()).with_for_update())
    if not crop or crop.owner_id==user.id:raise HTTPException(404,'Shared crop not found.')
    used=db.scalar(select(func.coalesce(func.sum(Purchase.quantity),0)).where(Purchase.crop_id==crop.id,Purchase.status.in_(['accepted','completed'])))
    if data.quantity>crop.quantity-used:raise HTTPException(409,'Requested quantity exceeds remaining produce.')
    if db.scalar(select(Purchase.id).where(Purchase.crop_id==crop.id,Purchase.buyer_id==user.id,Purchase.status=='pending').limit(1)):raise HTTPException(409,'You already have a pending request for this crop.')
    p=Purchase(buyer_id=user.id,seller_id=crop.owner_id,**data.model_dump());db.add(p)
    notify_user(db,crop.owner_id,f'New purchase request for {data.quantity} quintals of {crop.name}.')
    db.commit();return {**serialize(p),'crop_name':crop.name,'variety':crop.variety,'location':crop.location}

@app.put('/api/purchases/{id}')
def update_purchase(id:str,data:PurchaseUpdate,user=Depends(current_user),db:Session=Depends(get_db)):
    row=db.scalar(select(Purchase).where(Purchase.id==id,((Purchase.buyer_id==user.id)|(Purchase.seller_id==user.id))).with_for_update())
    if not row:raise HTTPException(404)
    if data.status=='cancelled':
        if row.buyer_id!=user.id or row.status!='pending':raise HTTPException(409,'Only your pending requests can be cancelled.')
    else:
        if row.seller_id!=user.id:raise HTTPException(403)
        expected='accepted' if data.status=='completed' else 'pending'
        if row.status!=expected:raise HTTPException(409,'This request is no longer in the required state.')
        if data.status=='accepted':
            if len(data.seller_contact)<5:raise HTTPException(422,'Provide your contact for this buyer.')
            crop=db.scalar(select(Crop).where(Crop.id==row.crop_id).with_for_update())
            used=db.scalar(select(func.coalesce(func.sum(Purchase.quantity),0)).where(Purchase.crop_id==row.crop_id,Purchase.status.in_(['accepted','completed'])))
            if row.quantity>crop.quantity-used:raise HTTPException(409,'Other agreed sales leave insufficient quantity.')
            row.seller_contact=data.seller_contact
    row.status=data.status
    notify_user(db,row.buyer_id if user.id==row.seller_id else row.seller_id,f'Purchase request updated: {data.status}.')
    db.commit();return serialize(row)


@app.post('/api/market-options/preview')
async def preview_market_options(data:MarketOptionsIn):
    return await market_recommendations.create_options(data.crop.model_dump(mode='json'),storage_days=data.storage_days)

@app.post('/api/market-options/preview/compare')
def preview_market_comparison(data:PreviewCompareIn):
    snapshot=market_recommendations.get_snapshot(data.snapshot_id,data.crop.model_dump(mode='json'),None)
    return market_recommendations.compare_options(snapshot,data.selections)

@app.get('/api/crops/{crop_id}/market-options')
async def crop_market_options(crop_id:str,storage_days:int=Query(0,ge=0,le=90),user=Depends(current_user),db:Session=Depends(get_db)):
    role(user,'farmer')
    context=jsonable_encoder(market_recommendations.crop_context(own_crop(crop_id,user,db)))
    return await market_recommendations.create_options(context,owner=user.id,storage_days=storage_days)

@app.post('/api/crops/{crop_id}/recommendation')
def crop_market_comparison(crop_id:str,data:MarketCompareIn,user=Depends(current_user),db:Session=Depends(get_db)):
    role(user,'farmer')
    context=jsonable_encoder(market_recommendations.crop_context(own_crop(crop_id,user,db)))
    snapshot=market_recommendations.get_snapshot(data.snapshot_id,context,user.id)
    result=market_recommendations.compare_options(snapshot,data.selections)
    if result['status']=='estimated':db.add(Record(owner_id=user.id,data=result));db.commit()
    return result

from .forecast_options import router as forecast_options_router
app.include_router(forecast_options_router)
