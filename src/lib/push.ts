import {auth,firebaseApp} from './firebase';
import {api} from './api';

const storageKey=(uid:string)=>`krishilink-push-v1:${uid}`;
export function savedPushToken(uid?:string):string|null {
 if(!uid)return null;
 try{return localStorage.getItem(storageKey(uid));}catch{return null;}
}

export async function enableBrowserPush(){
 const user=auth?.currentUser;
 if(!user||!firebaseApp||!import.meta.env.VITE_FIREBASE_VAPID_KEY)throw Error('Push notifications are being prepared.');
 const {getMessaging,getToken,deleteToken,isSupported}=await import('firebase/messaging');
 if(!await isSupported())throw Error('This browser does not support push notifications.');
 if(await Notification.requestPermission()!=='granted')throw Error('Notifications were not enabled.');
 const registration=await navigator.serviceWorker.register('/firebase-messaging-sw.js');
 const messaging=getMessaging(firebaseApp);
 const token=await getToken(messaging,{vapidKey:import.meta.env.VITE_FIREBASE_VAPID_KEY,serviceWorkerRegistration:registration});
 if(!token)throw Error('Notifications were not enabled.');
 try{
  await api('/notifications/token',{method:'POST',body:JSON.stringify({token})});
  localStorage.setItem(storageKey(user.uid),token);
 }catch(error){await deleteToken(messaging).catch(()=>{});throw error;}
}

export async function disableBrowserPush(){
 const user=auth?.currentUser;
 const token=savedPushToken(user?.uid);
 if(!user||!token)return;
 let failure:unknown;
 try{await api('/notifications/token',{method:'DELETE',body:JSON.stringify({token})});}catch(error){failure=error;}
 // Revoke the browser registration even if the account API is temporarily offline.
 if(firebaseApp){
  try{
   const {getMessaging,deleteToken,isSupported}=await import('firebase/messaging');
   if(await isSupported())await deleteToken(getMessaging(firebaseApp));
  }catch(error){failure ||= error;}
 }
 if(failure)throw failure;
 localStorage.removeItem(storageKey(user.uid));
}
