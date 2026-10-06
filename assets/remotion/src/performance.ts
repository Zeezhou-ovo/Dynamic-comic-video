export type Key = {frame:number;x:number;y:number;rotation:number;opacity:number};
export type Speech = {speaker:string;closed_asset:string;open_asset:string;shape_assets?:Partial<Record<'small'|'round'|'wide',string>>};
export type Cue = {speaker:string;text:string;start_frame:number;end_frame:number;audio?:string;mouth_open_frames?:number[];mouth_shape_frames?:string[]};
export type MouthEvent = {speaker:string;shape:string;start_frame:number;end_frame:number};

export function partValue(frame:number,keys:Key[],key:'x'|'y'|'rotation'|'opacity',easing='linear') {
  if (frame<=keys[0].frame) return keys[0][key];
  for (let i=1;i<keys.length;i++) {
    if (frame<=keys[i].frame) {
      const a=keys[i-1], b=keys[i]; let t=(frame-a.frame)/(b.frame-a.frame);
      if(easing==='ease-in-out') t=t<.5?4*t*t*t:1-Math.pow(-2*t+2,3)/2;
      if(easing==='ease-out') t=1-Math.pow(1-t,3);
      return a[key]+(b[key]-a[key])*t;
    }
  }
  return keys[keys.length-1][key];
}

export function mouthAsset(frame:number,speech:Speech,cues:Cue[],events:MouthEvent[]=[]) {
  const cue=cues.find(c=>c.speaker===speech.speaker && frame>=c.start_frame && frame<c.end_frame);
  if(!cue) return speech.closed_asset;
  const manual=events.find(e=>e.speaker===speech.speaker && frame>=e.start_frame && frame<e.end_frame);
  let shape=manual?.shape;
  if(!shape) shape=speech.shape_assets && cue.mouth_shape_frames
    ? cue.mouth_shape_frames[frame-cue.start_frame] ?? 'closed'
    : cue.mouth_open_frames?.includes(frame-cue.start_frame)?'open':'closed';
  if(shape==='closed') return speech.closed_asset;
  if(shape==='open') return speech.open_asset;
  return speech.shape_assets?.[shape as 'small'|'round'|'wide'] ?? speech.open_asset;
}

export function expressionAsset(frame:number,layer:string,events:{layer_id?:string;pose_asset?:string;start_frame:number;end_frame:number}[]) {
  return events.find(e=>e.layer_id===layer && frame>=e.start_frame && frame<e.end_frame)?.pose_asset;
}
