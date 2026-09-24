"""Synthetic fixtures test logic only; none are served as live market data."""
import sys
from pathlib import Path
from datetime import datetime,timedelta,timezone
from copy import deepcopy
import asyncio
import pytest
from fastapi import HTTPException
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import recommendations as rec
from app.schemas import MarketSelection


def context(**kw):return {'name':'Wheat','variety':'Lokwan','grade':'A','quantity':50.0,'location':'Surat, Gujarat','sell_date':str(rec.day()+timedelta(days=3)),'parameters':{},**kw}
def market(name='Surat',price=2400,**kw):return {'id':name,'market':name,'district':'Surat','state':'Gujarat','crop':'Wheat','variety':'Lokwan','grade':'FAQ','price':price,'date':str(rec.day()),'distance_km':40,'distance_note':'Estimated route','source':'AGMARKNET via data.gov.in','source_url':rec.SOURCE_URL,**kw}
def meta(ident='quote',mid='Surat'):return {'id':ident,'name':'Test-only provider fixture','market_id':mid,'source':'Test-only provider fixture','source_url':'https://example.test/quote','updated_at':rec.now().isoformat(),'valid_until':(rec.now()+timedelta(hours=1)).isoformat(),'available':True,'estimated':True}
def transport(mid='Surat',sid=None):return {**meta('vehicle',mid),'vehicle':'Test fixture truck','storage_id':sid,'capacity_quintals':30,'rate_per_km':20,'minimum_trip_cost':500,'fixed_trip_cost':200,'tolls_per_trip':100,'loading_per_quintal':10,'unloading_per_quintal':5,'all_transport_costs_included':True}
def storage(mid='Surat'):return {**meta('store',mid),'crops':['Wheat'],'compatible':True,'capacity_quintals':100,'lat':21.2,'lon':72.9,'rate_per_quintal_day':2,'handling_per_quintal':3,'finance_per_quintal_day':1,'loss_percent':1,'minimum_days':7,'all_storage_costs_included':True,'route_distance_km':60}
def charges(mid='Surat'):return {**meta('charges',mid),'market_fee_percent':1,'commission_per_quintal':10,'other_per_quintal':5,'other_description':'All remaining applicable charges','all_selling_costs_included':True}
def snapshot():return {'context':context(),'records':[market(),market('Bardoli',2500)],'services':{'transport':[transport(),transport('Bardoli')],'storage':[],'charges':[charges(),charges('Bardoli')]},'storage_days':0,'source':'AGMARKNET via data.gov.in','source_url':rec.SOURCE_URL,'expires_at':(rec.now()+timedelta(minutes=10)).isoformat()}
def selections():return [MarketSelection(market_id=m,transport_id='vehicle') for m in ['Surat','Bardoli']]


def test_complete_calculation_uses_vehicle_trips_and_all_costs():
    r=rec.compute_option(market(),transport(),None,charges(),50,0)
    # ceil(50/30)=2 trips: ((200+40*20)+100)*2/50 +10+5 =59/q.
    assert r['transport_cost']==59
    assert r['market_charges']==34
    assert r['other_costs']==5
    assert r['net_per_quintal']==2302
    assert r['total_expected']==115100
    assert not r['missing']


def test_storage_detour_minimum_days_finance_and_loss_included():
    r=rec.compute_option(market(),transport(sid='store'),storage(),charges(),50,3)
    assert r['distance_km']==60
    assert r['transport_cost']==75
    assert r['storage_cost']==48  # 7*(2+1)+3+1%*2400
    assert r['net_per_quintal']==2238


def test_unknown_cost_is_not_zero_and_incomplete_set_has_no_winner():
    s=snapshot();s['services']['charges']=s['services']['charges'][:1]
    r=rec.compare_options(s,selections())
    assert r['status']=='incomplete' and r['best_market_id'] is None
    missing=next(x for x in r['ranking'] if x['market']=='Bardoli')
    assert missing['net_per_quintal'] is None and missing['market_charges'] is None


def test_rank_net_not_headline_price():
    s=snapshot();s['services']['transport'][1]['fixed_trip_cost']=10000
    r=rec.compare_options(s,selections())
    assert r['best_market_id']=='Surat'
    assert r['ranking'][0]['rank']==1


def test_expired_quote_missing_route_and_wrong_storage_do_not_rank():
    t=transport();t['valid_until']=(rec.now()-timedelta(seconds=1)).isoformat()
    assert rec.compute_option(market(),t,None,charges(),50,0)['net_per_quintal'] is None
    assert rec.compute_option(market(distance_km=None),transport(),None,charges(),50,0)['net_per_quintal'] is None
    s=snapshot();s['storage_days']=3;s['services']['storage']=[storage()]
    wrong=[MarketSelection(market_id='Surat',transport_id='vehicle',storage_id='store'),selections()[1]]
    with pytest.raises(HTTPException):rec.compare_options(s,wrong)


def test_crop_quantity_owner_and_expiry_invalidate_snapshot():
    rec.SNAPSHOTS['test']={'owner':'farmer-a','fingerprint':rec.digest(context()),'expires':rec.now()+timedelta(minutes=1),'result':snapshot()}
    assert rec.get_snapshot('test',context(),'farmer-a')['context']['quantity']==50
    for ctx,owner in [(context(quantity=51),'farmer-a'),(context(grade='B'),'farmer-a'),(context(),'farmer-b'),(context(location='Navsari'),'farmer-a')]:
        with pytest.raises(HTTPException):rec.get_snapshot('test',ctx,owner)
    rec.SNAPSHOTS['test']['expires']=rec.now()-timedelta(seconds=1)
    with pytest.raises(HTTPException):rec.get_snapshot('test',context(),'farmer-a')


def test_latest_scope_variety_grade_and_rice_paddy_separation():
    feed={'source':'AGMARKNET via data.gov.in','records':[market(),market(price=2000,date=str(rec.day()-timedelta(days=1))),market('Wrong variety',variety='Sharbati'),market('Wrong grade',grade='B'),market('Old',date=str(rec.day()-timedelta(days=8))),market('Future',date=str(rec.day()+timedelta(days=1))),market('Bad',price=float('nan'))]}
    rows=rec.relevant_prices(feed,context());assert len(rows)==1 and rows[0]['price']==2400
    feed['records']=[market('Rice market',crop='Rice',variety='Basmati'),market('Paddy market',crop='Paddy',variety='Basmati')]
    rows=rec.relevant_prices(feed,context(name='Rice',variety='Basmati'));assert len(rows)==1 and rows[0]['market']=='Rice market'


def test_selection_tampering_and_duplicates_rejected():
    with pytest.raises(HTTPException):rec.compare_options(snapshot(),[selections()[0],selections()[0]])
    with pytest.raises(HTTPException):rec.compare_options(snapshot(),[MarketSelection(market_id='injected',transport_id='vehicle'),selections()[1]])


def test_unconfigured_market_service_has_no_generated_records(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(rec,'settings',lambda:SimpleNamespace(data_gov_api_key=''))
    r=asyncio.run(rec.discover(context()));assert r['records']==[] and r['status']=='unavailable'
