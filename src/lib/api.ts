import {auth} from './firebase';
export const API=import.meta.env.VITE_API_BASE_URL?.replace(/\/$/,'')||'/api';
export class ApiError extends Error {constructor(message:string,public status:number){super(message);}}
export async function api<T=any>(path:string,options:RequestInit={}):Promise<T>{
 const headers=new Headers(options.headers);
 if(!(options.body instanceof FormData))headers.set('Content-Type','application/json');
 const token=await auth?.currentUser?.getIdToken();if(token)headers.set('Authorization',`Bearer ${token}`);
 const response=await fetch(API+path,{...options,headers,signal:options.signal||AbortSignal.timeout(20000)});
 if(response.status===204)return undefined as T;
 const data=await response.json().catch(()=>({detail:'Account services are not available yet. Please try again later.'}));
 if(!response.ok)throw new ApiError(typeof data.detail==='string'?data.detail:'Please check your information and try again.',response.status);
 if(response.headers.get('content-type')?.includes('text/html'))throw new Error('Account services are not connected yet.');
 return data as T;
}
export async function currentWeather(lat:number,lon:number){
 try{return await api(`/weather?lat=${lat}&lon=${lon}`);}catch{
 try{const r=await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&forecast_days=7&timezone=Asia%2FKolkata`,{signal:AbortSignal.timeout(12000)});if(!r.ok)throw Error();return {...await r.json(),status:'current',source:'Open-Meteo'};}catch{return {status:'unavailable'};}}
}

