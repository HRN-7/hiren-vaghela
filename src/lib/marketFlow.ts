import {useEffect,useState} from 'react';
import {useOutletContext,useSearchParams} from 'react-router-dom';
import {useApp} from './context';
import {buildStaticMarketFeed} from './staticRecommendations';
import type {Crop} from './domain';
export type MarketChoice={market_id:string;transport_id:string|null;storage_id:string|null};
export type MarketOption={id:string;market:string;district:string;state:string;variety:string;grade:string;price:number;date:string;distance_km:number|null;straight_distance_km:number;variety_match:string;source:string;source_url:string;distance_note:string;[key:string]:any};
export type MarketFeed={status:string;records:MarketOption[];context:any;services:{transport:any[];storage:any[];charges:any[];message:string};snapshot_id:string;expires_at:string;message:string;source:string;source_url:string;storage_days:number;search_limited?:boolean;date?:string};
export function cropContext(crop:Crop){return {name:crop.name,variety:crop.variety,grade:crop.grade,quantity:crop.quantity,location:crop.location,sell_date:crop.sell_date,parameters:crop.parameters||{}};}
export function cropKey(crop:Crop){return JSON.stringify([crop.id,cropContext(crop)]);}
export function useSelectedCrop(){const{crops,selectedCropId,setSelectedCropId}=useApp();const[params,setParams]=useSearchParams();const requested=params.get('crop');const crop:Crop|undefined=crops.find((c:Crop)=>c.id===(requested||selectedCropId))||crops[0];return {crops:crops as Crop[],crop,selectCrop:(id:string)=>{setSelectedCropId(id);setParams(old=>{const next=new URLSearchParams(old);next.set('crop',id);return next;},{replace:true});}};}
const cache=new Map<string,{at:number;value:MarketFeed}>();
export function useMarketOptions(crop:Crop|undefined,storageDays=0){
 const{preview}=useOutletContext<any>();const {user}=useApp();const[keyRevision,setKeyRevision]=useState(0);const[state,setState]=useState<{key:string;feed:MarketFeed|null;error:string;loading:boolean}>({key:'',feed:null,error:'',loading:false});
 const key=crop?JSON.stringify([preview? 'preview':user?.uid,cropKey(crop),storageDays]):'';
 useEffect(()=>{if(!crop){setState({key,feed:null,error:'',loading:false});return;}let active=true;const controller=new AbortController();setState({key,feed:null,error:'',loading:true});
 const cached=cache.get(key);if(!keyRevision&&cached&&Date.now()-cached.at<3*60*1000){setState({key,feed:cached.value,error:'',loading:false});return;}
 const request=Promise.resolve(buildStaticMarketFeed(crop,storageDays));
 const timeout=setTimeout(()=>controller.abort(),90000);
 request.then(feed=>{if(!active)return;if(cache.size>20)cache.clear();cache.set(key,{at:Date.now(),value:feed});setState({key,feed,error:'',loading:false});}).catch(e=>{if(active)setState({key,feed:null,error:e?.name==='AbortError'?'Market lookup took too long. Please refresh suggestions.':e.message,loading:false});}).finally(()=>clearTimeout(timeout));
 return()=>{active=false;controller.abort();clearTimeout(timeout);};
 },[key,keyRevision]);
 return {...(state.key===key?state:{key,feed:null,error:'',loading:!!crop}),refresh:()=>{cache.delete(key);setKeyRevision(v=>v+1);}};
}
