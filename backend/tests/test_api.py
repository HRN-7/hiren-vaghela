import sys
from pathlib import Path
from datetime import date,timedelta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db import Base,User,Crop,get_db
from app.auth import current_user,identity

@pytest.fixture
def client():
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([User(id='a',name='Farmer A',role='farmer'),User(id='b',name='Farmer B',role='farmer')]);db.commit()
    def session():
        with Session(engine) as db:yield db
    app.dependency_overrides[get_db]=session
    with TestClient(app) as c:yield c
    app.dependency_overrides.clear()

@pytest.fixture
def signed(client):
    from fastapi import Depends
    def user(db=Depends(get_db)):return db.get(User,'a')
    app.dependency_overrides[current_user]=user
    return client

def crop_body():return {'name':'Cotton','variety':'Shankar-6','quantity':50,'grade':'A','parameters':{},'location':'Surat','sell_date':str(date.today()+timedelta(days=3)),'acknowledged':True}

def test_protected_routes_require_identity(client):
    assert client.get('/api/crops').status_code==401
    assert client.post('/api/crops',json=crop_body()).status_code==401
    assert client.get('/api/admin/review').status_code==401

def test_cost_math_and_reject_zero_quantity(client):
    data={'price':2250,'transport':80,'storage':25,'charges':75,'quantity':50}
    result=client.post('/api/net-realization',json=data)
    assert result.status_code==200
    assert result.json()['total_income']==103500
    assert client.post('/api/net-realization',json={**data,'quantity':0}).status_code==422
    assert client.post('/api/net-realization',json={**data,'storage':-1}).status_code==422

def test_crop_isolation_and_no_owner_injection(signed):
    r=signed.post('/api/crops',json=crop_body());assert r.status_code==201
    crop_id=r.json()['id']
    assert signed.get('/api/crops').json()[0]['owner_id']=='a'
    assert signed.post('/api/crops',json={**crop_body(),'owner_id':'b'}).status_code==422
    from fastapi import Depends
    def other(db=Depends(get_db)):return db.get(User,'b')
    app.dependency_overrides[current_user]=other
    assert signed.get('/api/crops').json()==[]
    assert signed.put('/api/crops/'+crop_id,json=crop_body()).status_code==404
    assert signed.delete('/api/crops/'+crop_id).status_code==404

def test_role_and_input_validation(signed):
    assert signed.post('/api/crops',json={**crop_body(),'quantity':-3}).status_code==422
    assert signed.post('/api/crops',json={**crop_body(),'acknowledged':False}).status_code==422
    assert signed.post('/api/crops',json={**crop_body(),'parameters':{'moisture_pct':130}}).status_code==422
    assert signed.post('/api/crops',json={**crop_body(),'sell_date':'2000-01-01'}).status_code==422
    demand={'company':'Test Buyer','crop':'Cotton','grade':'A','quantity':100,'price':5000,'location':'Surat','required_by':str(date.today()+timedelta(days=5)),'contact':'contact@example.test'}
    assert signed.post('/api/buyers',json=demand).status_code==403

def test_no_fake_forecast(client):
    response=client.get('/api/forecast',params={'crop':'Rice','market':'Unobserved market'})
    assert response.status_code==200
    assert response.json()['status']=='unavailable'
    assert response.json()['records']==[]
    assert response.json()['demand']==[]
    assert response.json()['demand_details']['status']=='unavailable'

def test_notification_ownership_and_unsubscribe(signed):
    from app.db import Notification,PushToken,PushDelivery
    from app.notifications import notify_user
    from sqlalchemy import select
    token='owned-device-token-for-testing'
    assert signed.post('/api/notifications/token',json={'token':token}).status_code==200
    with next(app.dependency_overrides[get_db]()) as db:
        row=notify_user(db,'a','A private notification.');db.commit();ident=row.id
    switch_user('b','buyer')
    assert signed.get('/api/notifications').json()==[]
    assert signed.put('/api/notifications/'+ident+'/read').status_code==404
    assert signed.request('DELETE','/api/notifications/token',json={'token':token}).status_code==404
    switch_user('a','farmer')
    assert signed.put('/api/notifications/'+ident+'/read').json()['read'] is True
    assert signed.request('DELETE','/api/notifications/token',json={'token':token}).status_code==204
    with next(app.dependency_overrides[get_db]()) as db:
        assert db.get(PushToken,token) is None
        assert db.scalars(select(PushDelivery)).all()==[]

def test_history_exact_state_district_and_legacy_compatibility(client):
    from app.db import PriceObservation,MarketPrice
    with next(app.dependency_overrides[get_db]()) as db:
        common={'market':'Test market','crop':'Wheat','variety':'Test variety','grade':'FAQ','date':date.today(),'source':'Test fixture'}
        db.add_all([PriceObservation(**common,state='Gujarat',district='Surat',price=2500,source_url='https://example.test'),
                    PriceObservation(**common,state='Gujarat',district='Other district',price=2600,source_url='https://example.test'),
                    MarketPrice(**common,price=2400)])
        db.commit()
    query={'crop':'Wheat','market':'Test market','variety':'Test variety','grade':'FAQ'}
    assert client.get('/api/prices/history',params=query).json()['records'][0]['price']==2400
    scoped=client.get('/api/prices/history',params={**query,'state':'Gujarat','district':'Surat'}).json()['records']
    assert len(scoped)==1 and scoped[0]['price']==2500
    assert client.get('/api/prices/history',params={**query,'state':'Other state','district':'Surat'}).json()['records']==[]

def test_published_prices_survive_history_storage_outage(client,monkeypatch):
    from app import providers,price_history
    expected={'status':'current','source':price_history.SOURCE,'records':[{'market':'Test market','price':2500}]}
    async def provider(*args):return expected
    monkeypatch.setattr(providers,'prices',provider)
    monkeypatch.setattr(price_history,'record_snapshot',lambda *args:{'status':'unavailable','stored':0})
    response=client.get('/api/prices',params={'crop':'Wheat','state':'Gujarat'})
    assert response.status_code==200 and response.json()['records']==expected['records']

def test_private_crop_absent_from_supply(signed):
    signed.post('/api/crops',json=crop_body())
    from fastapi import Depends
    def buyer(db=Depends(get_db)):
        user=db.get(User,'b');user.role='buyer';return user
    app.dependency_overrides[current_user]=buyer
    assert signed.get('/api/supply?crop=Cotton').json()==[]

def switch_user(user_id,role_name):
    from fastapi import Depends
    def user(db=Depends(get_db)):
        row=db.get(User,user_id)
        if not row:
            row=User(id=user_id,name='Test '+user_id,role=role_name);db.add(row);db.commit()
        row.role=role_name
        return row
    app.dependency_overrides[current_user]=user

def test_role_dashboards_restrict_api_data(signed):
    assert signed.get('/api/buyer/summary').status_code==403
    assert signed.get('/api/fpos/mine').status_code==403
    switch_user('b','buyer')
    assert signed.get('/api/buyer/summary').json()['completed']==0
    assert signed.post('/api/crops',json=crop_body()).status_code==403
    assert signed.get('/api/fpos/mine').status_code==403

def test_purchase_ownership_and_quantity_reservation(signed):
    crop=signed.post('/api/crops',json={**crop_body(),'public':True}).json()
    switch_user('b','buyer')
    body={'crop_id':crop['id'],'quantity':40,'price':5000,'buyer_contact':'buyer@example.test'}
    first=signed.post('/api/purchases',json=body);assert first.status_code==201
    pid=first.json()['id']
    assert signed.put('/api/purchases/'+pid,json={'status':'accepted','seller_contact':'buyer@example.test'}).status_code==403
    switch_user('c','buyer')
    assert signed.get('/api/purchases').json()==[]
    assert signed.put('/api/purchases/'+pid,json={'status':'cancelled'}).status_code==404
    second=signed.post('/api/purchases',json={**body,'quantity':30}).json()
    switch_user('a','farmer')
    assert signed.put('/api/purchases/'+pid,json={'status':'accepted','seller_contact':'farmer@example.test'}).status_code==200
    assert signed.put('/api/purchases/'+second['id'],json={'status':'accepted','seller_contact':'farmer@example.test'}).status_code==409
    assert signed.delete('/api/crops/'+crop['id']).status_code==409
    assert signed.put('/api/purchases/'+pid,json={'status':'completed'}).status_code==200
    switch_user('b','buyer')
    assert signed.get('/api/buyer/summary').json()['completed']==1

def test_fpo_request_capacity_and_owner_guard(signed):
    crop=signed.post('/api/crops',json=crop_body()).json()
    switch_user('b','fpo')
    body={'name':'Test FPO','location':'Surat','members':12,'capacity':20,'services':['Storage'],'contact':'fpo@example.test'}
    fpo=signed.post('/api/fpos',json=body).json()
    switch_user('a','farmer')
    req=signed.post('/api/fpos/'+fpo['id']+'/contribute/'+crop['id']).json()
    assert signed.put('/api/fpos/contributions/'+req['id']+'/accept').status_code==404
    switch_user('b','fpo')
    assert signed.get('/api/fpos/mine').json()['name']=='Test FPO'
    assert signed.put('/api/fpos/contributions/'+req['id']+'/accept').status_code==409
    assert signed.post('/api/fpos',json={**body,'capacity':100}).status_code==200
    assert signed.put('/api/fpos/contributions/'+req['id']+'/accept').status_code==200


def test_crop_photo_roundtrip_retry_remove_and_ownership(signed):
    from io import BytesIO
    from PIL import Image
    crop=signed.post('/api/crops',json=crop_body()).json();path='/api/crops/'+crop['id']+'/photos'
    out=BytesIO();Image.new('RGB',(20,20),'green').save(out,'PNG');image=out.getvalue()
    upload=signed.post(path,files={'file':('crop.png',image,'image/png')});assert upload.status_code==200
    ident=upload.json()['id']
    assert signed.post(path,files={'file':('crop.png',image,'image/png')}).json()['id']==ident
    assert signed.get('/api/crops').json()[0]['photos']==[ident]
    assert signed.get(path+'/'+ident).headers['content-type']=='image/jpeg'
    assert signed.post(path,files={'file':('fake.png',b'not an image','image/png')}).status_code==400
    assert signed.post(path,files={'file':('crop.gif',image,'image/gif')}).status_code==400
    switch_user('b','farmer')
    assert signed.get(path+'/'+ident).status_code==404
    assert signed.delete(path+'/'+ident).status_code==404
    switch_user('a','farmer')
    assert signed.delete(path+'/'+ident).status_code==204
    assert signed.get('/api/crops').json()[0]['photos']==[]


def test_all_four_saved_crops_preserve_recommendation_details(signed):
    for crop,variety,params in [('Cotton','Shankar-6',{'staple_mm':28}),('Wheat','Lokwan',{'test_weight':74}),('Groundnut','G20',{'shelling_pct':70}),('Rice','Basmati',{'broken_pct':4})]:
        body={**crop_body(),'name':crop,'variety':variety,'parameters':params,'notes':'Harvested this week','location':'Olpad, Surat, Gujarat'}
        r=signed.post('/api/crops',json=body);assert r.status_code==201
        saved=r.json();assert saved['name']==crop and saved['variety']==variety and saved['parameters']==params
        assert saved['notes']==body['notes'] and saved['location']==body['location'] and saved['quantity']==50
        assert saved['preferred_market']==''


def test_saved_crop_recommendation_endpoint_uses_server_prices_and_owner(signed,monkeypatch):
    from app import recommendations as rec
    from test_recommendations import snapshot
    async def discover(ctx):return {**snapshot(),'context':ctx,'status':'available','origin':{'lat':21.1,'lon':72.8},'fetched_at':rec.providers.stamp()}
    async def services(ctx,feed,days):return snapshot()['services']
    monkeypatch.setattr(rec,'discover',discover);monkeypatch.setattr(rec,'service_options',services)
    crop=signed.post('/api/crops',json=crop_body()).json();url='/api/crops/'+crop['id']
    options=signed.get(url+'/market-options').json();selections=options['suggested_selections']
    body={'snapshot_id':options['snapshot_id'],'selections':selections}
    response=signed.post(url+'/recommendation',json=body)
    assert response.status_code==200 and response.json()['best_market_id']=='Bardoli'
    assert signed.post(url+'/recommendation',json={**body,'price':100000}).status_code==422
    signed.put(url,json={**crop_body(),'quantity':51})
    assert signed.post(url+'/recommendation',json=body).status_code==409
    switch_user('b','farmer')
    assert signed.get(url+'/market-options').status_code==404
    assert signed.post(url+'/recommendation',json=body).status_code==404

