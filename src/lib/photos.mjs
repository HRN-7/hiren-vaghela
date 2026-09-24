export const MAX_PHOTOS = 3;
export const MAX_PHOTO_BYTES = 5 * 1024 * 1024;
export function photoMode({userAgent='',maxTouchPoints=0,coarse=false,width=1200}={}) {
  return /Android|iPhone|iPad|iPod|Mobile/i.test(userAgent) || (maxTouchPoints>0 && (coarse || width<768)) ? 'camera' : 'upload';
}
export async function validatePhoto(file) {
  if (!['image/jpeg','image/png','image/webp'].includes(file.type)) throw Error('Choose a JPG, PNG or WebP photo.');
  if (!file.size || file.size>MAX_PHOTO_BYTES) throw Error('Each photo must be non-empty and no larger than 5 MB.');
  const bytes=new Uint8Array(await file.slice(0,12).arrayBuffer());
  const jpg=bytes[0]===255 && bytes[1]===216 && bytes[2]===255;
  const png=[137,80,78,71,13,10,26,10].every((n,i)=>bytes[i]===n);
  const webp=String.fromCharCode(...bytes.slice(0,4))==='RIFF' && String.fromCharCode(...bytes.slice(8,12))==='WEBP';
  if (!({ 'image/jpeg':jpg,'image/png':png,'image/webp':webp }[file.type])) throw Error('This file is not a valid photo of the selected type.');
}
export function stopCamera(stream) {stream?.getTracks().forEach(track=>track.stop());}
