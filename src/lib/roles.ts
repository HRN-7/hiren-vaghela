import type {Role} from './domain';
export const rolePaths:Record<Role,string[]>={
 farmer:['dashboard','crops','crops/new','markets','buyers','fpos','transport','storage','calculator','recommendations','forecasts','purchases','profile','support'],
 buyer:['dashboard','buyers','supply','purchases','profile','support'],
 fpo:['dashboard','fpos','requests','profile','support']
};
export function roleHome(role:Role,preview=false){return `${preview?'/preview':'/app'}/${role}/dashboard`;}
export const validRole=(value:string|null|undefined):value is Role=>['farmer','fpo','buyer'].includes(value||'');
