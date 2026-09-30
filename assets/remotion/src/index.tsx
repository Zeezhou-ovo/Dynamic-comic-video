import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Composition,
  Img,
  Sequence,
  interpolate,
  registerRoot,
  staticFile,
  useCurrentFrame,
} from 'remotion';
import input from './render-data.json';
import { createShotContext } from './runtime/shot-context.mjs';
import { evaluateCamera } from './runtime/camera-controller.mjs';
import { evaluateLayerTransform } from './runtime/parallax-controller.mjs';
import {
  createCharacterPerformanceContext,
  evaluateCharacterPerformance,
  evaluateCharacterPart,
  resolveCharacterLayerAsset,
} from './runtime/character-controller.mjs';

type Depth = 'foreground' | 'character' | 'midground' | 'background' | 'sky';
type Key = { frame: number; x: number; y: number; scale?: number; rotation: number; opacity: number };
type CameraPose = { x: number; y: number; zoom: number };
type CameraPlan = {
  type: 'static' | 'push_in' | 'pull_out' | 'pan_left' | 'pan_right' | 'follow';
  focus_target?: { id?: string; x: number; y: number };
  from?: CameraPose;
  to?: CameraPose;
  follow_path?: { frame: number; x: number; y: number }[];
  easing?: 'linear' | 'easeIn' | 'easeOut' | 'easeInOut';
  screen_target?: { x: number; y: number };
  parallax_enabled?: boolean;
  parallax_strengths?: Partial<Record<Depth, number>>;
};
type Layer = {
  layer_id: string;
  asset: string;
  depth?: Depth;
  character_id?: string;
  state_assets?: Record<string, string>;
  region?: [number, number, number, number];
  z: number;
  from: { x: number; y: number; scale: number };
  to: { x: number; y: number; scale: number };
  acting?: {
    part: string;
    pivot: [number, number];
    keys: Key[];
    easing?: 'linear' | 'easeIn' | 'easeOut' | 'easeInOut';
    speech?: { speaker: string; closed_asset: string; open_asset: string };
    poses?: { frame: number; asset: string }[];
  };
};
type DialogueCue = {
  speaker: string;
  text: string;
  start_frame: number;
  end_frame: number;
  audio?: string;
  mouth_open_frames?: number[];
  emphasis?: 'normal' | 'important' | 'reveal' | 'punchline' | 'awkward' | 'surprise';
  beat_id?: string;
};
type ShotPlan = {
  shot_id: string;
  start_frame: number;
  duration_frames: number;
  shot_intent?: string;
  camera_intent?: string;
  framing?: 'wide' | 'medium' | 'close_up';
  camera?: CameraPlan;
  character_performance?: {
    character_id: string;
    role: 'idle' | 'speaker' | 'listener';
    pose?: string;
    expression?: string;
    root_pivot?: [number, number];
    root_easing?: 'linear' | 'easeIn' | 'easeOut' | 'easeInOut';
    root_keys?: { frame: number; x: number; y: number; scale: number; rotation: number; opacity: number }[];
    events: { event_id: string; preset: 'idle' | 'talk' | 'nod' | 'shake_head' | 'point' | 'raise_hand' | 'blink' | 'small_bounce'; start_frame: number; peak_frame: number; settle_frame: number; end_frame: number; part?: string; amplitude?: number; easing?: string }[];
    capabilities: { parts: string[]; poses: string[]; expressions: string[] };
  }[];
  layers: Layer[];
  dialogue?: DialogueCue[];
};
type RenderData = {
  version?: string;
  format: { width: number; height: number; fps: number; duration_frames: number };
  asset_mode: string;
  shots: ShotPlan[];
};
const data = input as RenderData;

const Shot = ({ shot }: { shot: ShotPlan }) => {
  const frame = useCurrentFrame();
  const context = createShotContext(data.version === '0.4' ? shot : { ...shot, camera: undefined }, frame, data.format);
  const camera = evaluateCamera(frame, context);
  const characterStates = new Map((shot.character_performance ?? []).map(performance => {
    const characterContext = createCharacterPerformanceContext({
      characterId: performance.character_id,
      performance,
      capabilities: performance.capabilities,
      absoluteFrame: shot.start_frame + frame,
      localFrame: frame,
      startFrame: shot.start_frame,
      durationFrames: shot.duration_frames,
      fps: data.format.fps,
      dialogue: shot.dialogue ?? [],
    });
    return [performance.character_id, evaluateCharacterPerformance(characterContext)];
  }));
  const caption = shot.dialogue?.find(cue => frame >= cue.start_frame && frame < cue.end_frame);

  return (
    <AbsoluteFill style={{ overflow: 'hidden' }}>
      {[...shot.layers].sort((a, b) => a.z - b.z).map(layer => {
        const value = (key: 'x' | 'y' | 'scale') => interpolate(
          frame,
          [0, shot.duration_frames - 1],
          [layer.from[key], layer.to[key]],
          { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
        );
        const acting = layer.acting;
        const performanceState = layer.character_id ? characterStates.get(layer.character_id) : undefined;
        const local = evaluateCharacterPart(frame, acting, performanceState);
        let pose = resolveCharacterLayerAsset(layer, performanceState, frame);
        if (acting?.speech) {
          const cue = shot.dialogue?.find(item => item.speaker === acting.speech!.speaker && frame >= item.start_frame && frame < item.end_frame);
          if (performanceState) {
            pose = performanceState.mouth.state === 'open' ? acting.speech.open_asset : acting.speech.closed_asset;
          } else {
            pose = cue?.mouth_open_frames?.includes(frame - cue.start_frame)
              ? acting.speech.open_asset
              : acting.speech.closed_asset;
          }
        }
        const region = layer.region;
        const depthTransform = evaluateLayerTransform(camera, layer.depth ?? 'character', data.format);
        const root = performanceState?.root;

        return (
          <AbsoluteFill
            key={layer.layer_id}
            style={{ transformOrigin: '0 0', transform: depthTransform.transform }}
          >
            <AbsoluteFill
              style={{
                transformOrigin: root ? `${performanceState?.rootPivot[0] * 100}% ${performanceState?.rootPivot[1] * 100}%` : '50% 50%',
                transform: root ? `translate(${root.x}px, ${root.y}px) rotate(${root.rotation}deg) scale(${root.scale})` : undefined,
                opacity: root?.opacity,
              }}
            >
            <AbsoluteFill
              style={{
                clipPath: region
                  ? `inset(${region[1] * 100}% ${(1 - region[0] - region[2]) * 100}% ${(1 - region[1] - region[3]) * 100}% ${region[0] * 100}%)`
                  : undefined,
                transformOrigin: '50% 50%',
                transform: `translate(${value('x')}px, ${value('y')}px) scale(${value('scale')})`,
              }}
            >
              <Img
                src={staticFile(pose)}
                style={{
                  width: '100%',
                  height: '100%',
                  opacity: local.opacity,
                  transformOrigin: acting ? `${acting.pivot[0] * 100}% ${acting.pivot[1] * 100}%` : '50% 50%',
                  transform: `translate(${local.x}px, ${local.y}px) rotate(${local.rotation}deg) scale(${local.scale})`,
                }}
              />
            </AbsoluteFill>
            </AbsoluteFill>
          </AbsoluteFill>
        );
      })}
      {caption && (
        <div style={{
          position: 'absolute', bottom: '10%', left: '6%', right: '6%', textAlign: 'center',
          color: 'white', fontSize: Math.round(data.format.height * (caption.emphasis === 'punchline' || caption.emphasis === 'surprise' ? 0.052 : 0.045)),
          fontFamily: 'Arial, "Microsoft YaHei", sans-serif', fontWeight: 700,
          whiteSpace: 'pre-wrap', overflowWrap: 'anywhere',
          textShadow: '-2px -2px 0 black, 2px -2px 0 black, -2px 2px 0 black, 2px 2px 0 black',
        }}>{caption.text}</div>
      )}
      {data.asset_mode === 'fixture' && (
        <div style={{ position: 'absolute', left: 24, bottom: 20, color: 'white', background: '#172332', padding: '8px 14px', fontSize: 18, fontFamily: 'sans-serif' }}>
          PIPELINE FIXTURE · {shot.shot_id} · NOT FINAL ART
        </div>
      )}
    </AbsoluteFill>
  );
};

const Video = () => (
  <AbsoluteFill style={{ background: '#172332' }}>
    {data.shots.map(shot => (
      <Sequence key={shot.shot_id} from={shot.start_frame} durationInFrames={shot.duration_frames}>
        <Shot shot={shot} />
        {shot.dialogue?.filter(cue => cue.audio).map((cue, index) => (
          <Sequence key={index} from={cue.start_frame} durationInFrames={cue.end_frame - cue.start_frame}>
            <Audio src={staticFile(cue.audio!)} />
          </Sequence>
        ))}
      </Sequence>
    ))}
  </AbsoluteFill>
);

registerRoot(() => (
  <Composition
    id="MangaMotion"
    component={Video}
    width={data.format.width}
    height={data.format.height}
    fps={data.format.fps}
    durationInFrames={data.format.duration_frames}
  />
));
