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

type Depth = 'foreground' | 'character' | 'midground' | 'background' | 'sky';
type Key = { frame: number; x: number; y: number; rotation: number; opacity: number };
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
  region?: [number, number, number, number];
  z: number;
  from: { x: number; y: number; scale: number };
  to: { x: number; y: number; scale: number };
  acting?: {
    part: string;
    pivot: [number, number];
    keys: Key[];
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
};
type ShotPlan = {
  shot_id: string;
  start_frame: number;
  duration_frames: number;
  camera?: CameraPlan;
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
        const local = (key: 'x' | 'y' | 'rotation' | 'opacity', fallback: number) => acting
          ? interpolate(
              frame,
              acting.keys.map(keyframe => keyframe.frame),
              acting.keys.map(keyframe => keyframe[key]),
              { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
            )
          : fallback;
        let pose = acting?.poses?.filter(item => item.frame <= frame).at(-1)?.asset ?? layer.asset;
        if (acting?.speech) {
          const cue = shot.dialogue?.find(item => item.speaker === acting.speech!.speaker && frame >= item.start_frame && frame < item.end_frame);
          pose = cue?.mouth_open_frames?.includes(frame - cue.start_frame)
            ? acting.speech.open_asset
            : acting.speech.closed_asset;
        }
        const region = layer.region;
        const depthTransform = evaluateLayerTransform(camera, layer.depth ?? 'character', data.format);

        return (
          <AbsoluteFill
            key={layer.layer_id}
            style={{ transformOrigin: '0 0', transform: depthTransform.transform }}
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
                  opacity: local('opacity', 1),
                  transformOrigin: acting ? `${acting.pivot[0] * 100}% ${acting.pivot[1] * 100}%` : '50% 50%',
                  transform: `translate(${local('x', 0)}px, ${local('y', 0)}px) rotate(${local('rotation', 0)}deg)`,
                }}
              />
            </AbsoluteFill>
          </AbsoluteFill>
        );
      })}
      {caption && (
        <div style={{
          position: 'absolute', bottom: '10%', left: '6%', right: '6%', textAlign: 'center',
          color: 'white', fontSize: Math.round(data.format.height * 0.045),
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
