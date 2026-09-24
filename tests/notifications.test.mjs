import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';

function worker(){
 const listeners={},shown=[],opened=[];
 vm.runInNewContext(readFileSync(new URL('../public/firebase-messaging-sw.js',import.meta.url),'utf8'),{
  self:{addEventListener:(type,fn)=>listeners[type]=fn,location:{origin:'https://test.example'},
   registration:{showNotification:async(title,options)=>shown.push({title,...options})}},
  clients:{matchAll:async()=>[],openWindow:async(url)=>opened.push(url)},URL,
 });
 return {listeners,shown,opened};
}

test('push tags identify distinct events and reuse a tag for retry',async()=>{
 const {listeners,shown}=worker();
 for(const notificationId of ['event-a','event-b','event-a']){
  let pending;
  listeners.push({data:{json:()=>({data:{notificationId,body:'Account update'}})},waitUntil:value=>pending=value});
  await pending;
 }
 assert.deepEqual(shown.map(row=>row.tag),['krishilink-event-a','krishilink-event-b','krishilink-event-a']);
});

test('notification clicks only open the fixed authenticated profile route',async()=>{
 const {listeners,opened}=worker();let pending,closed=false;
 listeners.notificationclick({notification:{data:{url:'https://untrusted.example'},close:()=>closed=true},waitUntil:value=>pending=value});
 await pending;
 assert.equal(closed,true);
 assert.deepEqual(opened,['/app/profile']);
});
