import React from 'react';
import {AbsoluteFill,interpolate} from 'remotion';
export type VisualEvent={event_id:string;effect_type:string;start_frame:number;end_frame:number;position?:[number,number];intensity?:number;color?:string;keyword?:string;asset?:string};

export const ComicEffects=({events,frame,width,height}:{events:VisualEvent[];frame:number;width:number;height:number})=> <AbsoluteFill style={{pointerEvents:'none'}}>{events.filter(e=>frame>=e.start_frame && frame<e.end_frame).map(e=>{
  const [x,y]=e.position??[.88,.18]; const size=height*.13; const strength=e.intensity??1;
  const age=frame-e.start_frame, length=e.end_frame-e.start_frame;
  const opacity=Math.min(1,(age+1)/3,(length-age)/3)*strength;
  const common={position:'absolute' as const,left:x*width-size/2,top:y*height-size/2,width:size,height:size,opacity};
  const stroke=e.color??'#20272b';
  if(['screen_shake','subtitle_emphasis','background_simplify'].includes(e.effect_type)) return null;
  if(['flash','background_tint'].includes(e.effect_type)) return <AbsoluteFill key={e.event_id} style={{background:e.color??'#fff3c3',opacity:e.effect_type==='flash'?Math.max(0,1-age/Math.max(1,length))*.24*strength:.10*strength}}/>;
  if(['question','exclamation','ellipsis'].includes(e.effect_type)) return <div key={e.event_id} style={{...common,textAlign:'center',fontFamily:'sans-serif',fontSize:size*.88,fontWeight:900,color:stroke,WebkitTextStroke:'1px #fff5d8'}}>{e.effect_type==='question'?'?':e.effect_type==='exclamation'?'!':'…'}</div>;
  return <svg key={e.event_id} style={common} viewBox="0 0 100 100" fill="none" stroke={stroke} strokeWidth="4" strokeLinecap="round">
    {e.effect_type==='sweat_drop' && <path d="M50 10 C46 29 28 43 28 61 C28 89 72 89 72 61 C72 43 54 29 50 10 Z" fill="#a9deec"/>}
    {e.effect_type==='black_line' && [30,50,70].map(a=><path key={a} d={`M${a} 15 L${a+3} 65`}/>)}
    {e.effect_type==='vein' && <path d="M28 20 Q50 28 47 44 M72 20 Q50 28 53 44 M28 80 Q50 72 47 56 M72 80 Q50 72 53 56" stroke="#d15a42"/>}
    {e.effect_type==='sparkle' && <path d="M50 10 L59 41 L90 50 L59 59 L50 90 L41 59 L10 50 L41 41 Z" fill="#f4c969"/>}
    {['shock_lines','speed_lines','focus_lines'].includes(e.effect_type) && [0,45,90,135,180,225,270,315].map(angle=><path key={angle} d="M50 3 L50 25" transform={`rotate(${angle} 50 50)`}/>)}
  </svg>;
})}</AbsoluteFill>;

export function shakeOffset(frame:number,events:VisualEvent[]) {
  const event=events.find(e=>e.effect_type==='screen_shake' && frame>=e.start_frame && frame<e.end_frame);
  if(!event) return 0;
  const progress=(frame-event.start_frame)/Math.max(1,event.end_frame-event.start_frame-1);
  return interpolate(progress,[0,.15,.45,.7,1],[0,4,-3,1,0])*(event.intensity??1);
}
