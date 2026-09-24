// A data-only FCM push handler. It never opens a URL supplied by an untrusted message.
self.addEventListener('push',event=>{
 let data={};try{data=event.data?.json()||{}}catch{return}
 const content=data.notification||data.data||{};
 const id=String(content.notificationId||'update').replace(/[^a-zA-Z0-9-]/g,'').slice(0,50);
 event.waitUntil(self.registration.showNotification(String(content.title||'KrishiLink AI').slice(0,100),{body:String(content.body||'You have a new update.').slice(0,300),icon:'/favicon.svg',tag:'krishilink-'+id}));
});
self.addEventListener('notificationclick',event=>{
 event.notification.close();
 event.waitUntil((async()=>{
  const windows=await clients.matchAll({type:'window',includeUncontrolled:true});
  const existing=windows.find(client=>new URL(client.url).origin===self.location.origin);
  if(existing){await existing.navigate('/app/profile');return existing.focus();}
  return clients.openWindow('/app/profile');
 })());
});
