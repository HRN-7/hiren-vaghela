import {useEffect} from 'react';
import {flushSync} from 'react-dom';
import {calculateNet} from './calculations.mjs';
export function useCalculatorTool(update:(input:any)=>void){useEffect(()=>{
 const context=(document as any).modelContext;if(!context?.registerTool)return;
 const controller=new AbortController();
 const keys=['price','transport','storage','charges','quantity'];
 try{Promise.resolve(context.registerTool({name:'calculate_net_realization',title:'Calculate net realization',description:'Calculate a selling scenario from explicit INR-per-quintal costs and quantity in quintals; updates the visible calculator. Does not save a sale or make a payment.',inputSchema:{type:'object',properties:Object.fromEntries(keys.map(k=>[k,{type:'number',minimum:k==='quantity'?0.01:0,maximum:10000000}])),required:keys,additionalProperties:false},annotations:{readOnlyHint:false,untrustedContentHint:false},execute(input:unknown){if(!input||typeof input!=='object'||Array.isArray(input))throw Error('Provide the five numeric inputs.');const value=input as Record<string,unknown>;if(Object.keys(value).length!==5||keys.some(k=>typeof value[k]!=='number'||!Number.isFinite(value[k])||Number(value[k])>10000000))throw Error('Provide the five numeric inputs.');const result=calculateNet(value as any);flushSync(()=>update(value));return {net_per_quintal:result.net,total_income:result.total,currency:'INR'};}},{signal:controller.signal})).catch(()=>{});}catch{}
 return()=>controller.abort();
},[]);}
