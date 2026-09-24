import test from 'node:test';
import assert from 'node:assert/strict';
import {photoMode,validatePhoto,stopCamera,MAX_PHOTO_BYTES} from '../src/lib/photos.mjs';
test('phones and tablets have camera-only mode; desktop allows upload',()=>{
 assert.equal(photoMode({userAgent:'Android Mobile'}),'camera');assert.equal(photoMode({userAgent:'iPhone'}),'camera');assert.equal(photoMode({userAgent:'Macintosh',maxTouchPoints:5,coarse:true}),'camera');assert.equal(photoMode({userAgent:'Windows NT',width:1440}),'upload');
});
test('accepts image signatures and rejects empty, disguised and oversized files',async()=>{
 await validatePhoto(new File([new Uint8Array([255,216,255,224,0,1,2,3,4,5,6,7])],'crop.jpg',{type:'image/jpeg'}));
 await assert.rejects(()=>validatePhoto(new File(['not-an-image'],'crop.jpg',{type:'image/jpeg'})),/not a valid/);
 await assert.rejects(()=>validatePhoto(new File([],'crop.jpg',{type:'image/jpeg'})),/non-empty/);
 await assert.rejects(()=>validatePhoto(new File(['x'],'crop.svg',{type:'image/svg+xml'})),/JPG/);
 await assert.rejects(()=>validatePhoto({type:'image/png',size:MAX_PHOTO_BYTES+1}),/5 MB/);
});
test('camera tracks are all stopped on cleanup',()=>{let stopped=0;stopCamera({getTracks:()=>[{stop:()=>stopped++},{stop:()=>stopped++}]});assert.equal(stopped,2);stopCamera(null);});
