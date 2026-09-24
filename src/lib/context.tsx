import {createContext,useContext,useEffect,useRef,useState,type ReactNode} from 'react';
import {useLocation} from 'react-router-dom';
import {onAuthStateChanged,signOut,type User} from 'firebase/auth';
import {auth} from './firebase';
import {api} from './api';
import {disableBrowserPush} from './push';
import type {Crop,Role} from './domain';
export type Profile={id:string;name:string;role:Role;location:string;language:string};
const Context=createContext<any>(null);
export function AppProvider({children}:{children:ReactNode}){
 const {pathname}=useLocation();const preview=pathname.startsWith('/preview');
 const[user,setUser]=useState<User|null>(null);const[profile,setProfile]=useState<Profile|null>(null);const[loading,setLoading]=useState(true);
 const[accountCrops,setAccountCrops]=useState<Crop[]>([]);const[previewCrops,setPreviewCrops]=useState<Crop[]>([]);
 const[previewDemands,setPreviewDemands]=useState<any[]>([]);const[previewFpo,setPreviewFpo]=useState<any>(null);const[previewContributions,setPreviewContributions]=useState<any[]>([]);const[previewPurchases,setPreviewPurchases]=useState<any[]>([]);
 const[selectedCropId,setSelectedCropId]=useState('');const[marketFlow,setMarketFlow]=useState<any>(null);
 const[demoRole,setDemoRole]=useState<Role>('farmer');const[notice,setNotice]=useState('');const epoch=useRef(0);
 useEffect(()=>{if(!auth){setLoading(false);return;}return onAuthStateChanged(auth,async u=>{const version=++epoch.current;setLoading(true);setUser(u);setProfile(null);setAccountCrops([]);if(u&&!needsEmailVerification(u)){try{const[p,c]=await Promise.all([api<Profile>('/auth/me'),api<Crop[]>('/crops')]);if(version===epoch.current){setProfile(p);setAccountCrops(c);}}catch{}}if(version===epoch.current)setLoading(false);});},[]);
 useEffect(()=>{if(!notice)return;const timer=setTimeout(()=>setNotice(''),6000);return()=>clearTimeout(timer);},[notice]);
 const reload=async()=>{const version=epoch.current;const[p,c]=await Promise.all([api<Profile>('/auth/me'),api<Crop[]>('/crops')]);if(version===epoch.current){setProfile(p);setAccountCrops(c);}return p;};
 return <Context.Provider value={{user,profile:preview?null:profile,setProfile,loading,selectedCropId,setSelectedCropId,marketFlow,setMarketFlow,crops:preview?previewCrops:accountCrops,setCrops:preview?setPreviewCrops:setAccountCrops,previewCrops,previewDemands,setPreviewDemands,previewFpo,setPreviewFpo,previewContributions,setPreviewContributions,previewPurchases,setPreviewPurchases,demoRole,setDemoRole,notice,setNotice,reload,logout:async()=>{++epoch.current;setMarketFlow(null);setSelectedCropId('');await disableBrowserPush().catch(()=>{});if(auth)await signOut(auth);setProfile(null);setAccountCrops([]);}}}>{children}</Context.Provider>
}
export const needsEmailVerification=(u:User)=>u.providerData.some(p=>p.providerId==='password')&&!u.emailVerified;
export const useApp=()=>useContext(Context);
