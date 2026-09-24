import {initializeApp} from 'firebase/app';
import {getAuth,browserLocalPersistence,setPersistence} from 'firebase/auth';
const e=import.meta.env;
export const firebaseConfig={apiKey:e.VITE_FIREBASE_API_KEY,authDomain:e.VITE_FIREBASE_AUTH_DOMAIN,projectId:e.VITE_FIREBASE_PROJECT_ID,storageBucket:e.VITE_FIREBASE_STORAGE_BUCKET,messagingSenderId:e.VITE_FIREBASE_MESSAGING_SENDER_ID,appId:e.VITE_FIREBASE_APP_ID};
export const authReady=Boolean(firebaseConfig.apiKey&&firebaseConfig.authDomain&&firebaseConfig.projectId&&firebaseConfig.appId);
export const firebaseApp=authReady?initializeApp(firebaseConfig):null;
export const auth=firebaseApp?getAuth(firebaseApp):null;
if(auth)setPersistence(auth,browserLocalPersistence).catch(()=>{});
