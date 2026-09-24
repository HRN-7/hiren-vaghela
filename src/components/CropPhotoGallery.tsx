import {useEffect,useState} from 'react';
import {auth} from '../lib/firebase';
import {API} from '../lib/api';
import type {Crop} from '../lib/domain';
export function CropPhotoGallery({crop,preview}:{crop:Crop;preview:boolean}){
 const[urls,setUrls]=useState<string[]>([]),[error,setError]=useState(false);const signature=(crop.photos||[]).join('|');
 useEffect(()=>{let active=true;const controller=new AbortController();const owned:string[]=[];setUrls([]);setError(false);if(preview){setUrls(crop.photos||[]);return;}
 (async()=>{try{const token=await auth?.currentUser?.getIdToken();if(!token)return;const loaded=await Promise.all((crop.photos||[]).map(async id=>{const r=await fetch(`${API}/crops/${crop.id}/photos/${id}`,{headers:{Authorization:`Bearer ${token}`},signal:controller.signal});if(!r.ok)throw Error();const u=URL.createObjectURL(await r.blob());owned.push(u);if(!active)URL.revokeObjectURL(u);return u;}));if(active)setUrls(loaded);}catch{if(active)setError(true);}})();return()=>{active=false;controller.abort();owned.forEach(u=>URL.revokeObjectURL(u));};
 },[crop.id,signature,preview]);
 return <>{urls.length>0&&<div className="saved-crop-photos">{urls.map((u,i)=><img key={i} src={u} alt={`${crop.name} photo ${i+1}`}/>)}</div>}{error&&<p className="muted">Photos could not load. Refresh to retry.</p>}</>;
}
