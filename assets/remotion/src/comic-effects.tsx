import React from 'react';
import { AbsoluteFill } from 'remotion';
import { effectOpacity } from './runtime/performance-controller.mjs';

// Drawn comic symbols, ported from the local performance upgrade. They render
// only when a project authors a visual event; nothing is added by default.
export type VisualEvent = {
  event_id: string; effect_type: string; start_frame: number; end_frame: number;
  position?: [number, number]; intensity?: number; size?: number; color?: string; keyword?: string; asset?: string;
};

const NOT_DRAWN = ['screen_shake', 'subtitle_emphasis', 'background_simplify'];

export const ComicEffects = ({ events, frame, width, height }: { events: VisualEvent[]; frame: number; width: number; height: number }) => (
  <AbsoluteFill style={{ pointerEvents: 'none' }}>
    {events.filter(e => frame >= e.start_frame && frame < e.end_frame && !NOT_DRAWN.includes(e.effect_type)).map(e => {
      const [x, y] = e.position ?? [0.88, 0.18];
      const size = height * (e.size ?? 0.13);
      const opacity = effectOpacity(frame, e);
      const age = frame - e.start_frame;
      const length = e.end_frame - e.start_frame;
      const stroke = e.color ?? '#20272b';
      const common = { position: 'absolute' as const, left: x * width - size / 2, top: y * height - size / 2, width: size, height: size, opacity };
      if (e.effect_type === 'flash' || e.effect_type === 'background_tint') {
        return <AbsoluteFill key={e.event_id} style={{ background: e.color ?? '#fff3c3', opacity: e.effect_type === 'flash' ? Math.max(0, 1 - age / Math.max(1, length)) * 0.24 * (e.intensity ?? 1) : 0.1 * (e.intensity ?? 1) }} />;
      }
      if (e.effect_type === 'radial_burst') {
        const burstColor = e.color ?? '#f5c84c';
        return <AbsoluteFill key={e.event_id} style={{
          opacity,
          background: `repeating-conic-gradient(from 0deg at ${x * 100}% ${y * 100}%, ${burstColor} 0deg 10deg, transparent 10deg 20deg)`,
        }} />;
      }
      if (['question', 'exclamation', 'ellipsis'].includes(e.effect_type)) {
        return <div key={e.event_id} style={{ ...common, textAlign: 'center', fontFamily: 'sans-serif', fontSize: size * 0.88, fontWeight: 900, color: stroke, WebkitTextStroke: '1px #fff5d8' }}>{e.effect_type === 'question' ? '?' : e.effect_type === 'exclamation' ? '!' : '…'}</div>;
      }
      // sweat drop slides a little while it is visible
      const slide = e.effect_type === 'sweat_drop' ? Math.min(1, age / Math.max(1, length)) * size * 0.12 : 0;
      return (
        <svg key={e.event_id} style={{ ...common, top: common.top + slide }} viewBox="0 0 100 100" fill="none" stroke={stroke} strokeWidth="4" strokeLinecap="round">
          {e.effect_type === 'sweat_drop' && <path d="M50 10 C46 29 28 43 28 61 C28 89 72 89 72 61 C72 43 54 29 50 10 Z" fill="#a9deec" />}
          {e.effect_type === 'black_line' && [22, 36, 50, 64, 78].map((a, i) => <path key={a} d={`M${a} 12 L${a} ${42 + (i % 2) * 10}`} stroke={e.color ?? '#3a2a40'} />)}
          {e.effect_type === 'vein' && <path d="M28 20 Q50 28 47 44 M72 20 Q50 28 53 44 M28 80 Q50 72 47 56 M72 80 Q50 72 53 56" stroke="#d15a42" />}
          {e.effect_type === 'sparkle' && <path d="M50 10 L59 41 L90 50 L59 59 L50 90 L41 59 L10 50 L41 41 Z" fill="#f4c969" />}
          {['shock_lines', 'speed_lines', 'focus_lines'].includes(e.effect_type) && [0, 45, 90, 135, 180, 225, 270, 315].map(angle => <path key={angle} d="M50 3 L50 25" transform={`rotate(${angle} 50 50)`} />)}
        </svg>
      );
    })}
  </AbsoluteFill>
);
