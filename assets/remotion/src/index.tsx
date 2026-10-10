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
import { selectSubtitleCue } from './runtime/subtitle-controller.mjs';
import { createShotContext } from './runtime/shot-context.mjs';
import { evaluateCamera } from './runtime/camera-controller.mjs';
import { evaluateLayerTransform } from './runtime/parallax-controller.mjs';
import { createAssetLoader } from './runtime/asset-loader.mjs';
import { buildSceneGraph } from './runtime/scene-graph.mjs';
import {
  createCharacterPerformanceContext,
  evaluateCharacterPerformance,
  evaluateCharacterPart,
  resolveCharacterLayerAsset,
} from './runtime/character-controller.mjs';
import {
  captionRuns,
  drivingPropMotion,
  expressionAsset,
  mouthAsset,
  propTransform,
  shakeOffset,
} from './runtime/performance-controller.mjs';
import { ComicEffects, VisualEvent } from './comic-effects';
import { evaluatePoseTrack } from './runtime/pose-controller.mjs';
import { evaluateEffects } from './runtime/effect-controller.mjs';

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
type PropMotion = {
  pivot: [number, number];
  roll_radius?: number;
  events: { event_id: string; kind: 'rock' | 'lean'; start_frame: number; end_frame: number; amplitude_deg: number; period_frames?: number; decay_frames?: number }[];
};
type Layer = {
  layer_id: string;
  prop_motion?: PropMotion;
  attach_to?: string;
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
    speech?: { speaker: string; closed_asset: string; open_asset: string; shape_assets?: Partial<Record<'small' | 'round' | 'wide', string>> };
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
  mouth_shape_frames?: string[];
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
  scene_instances?: { character_id: string; slot_id: string; visible: boolean }[];
  visible_objects?: string[];
  composition?: Record<string, any>;
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
  timeline?: {
    mouth_events?: { speaker: string; shape: string; start_frame: number; end_frame: number }[];
    expression_events?: { layer_id?: string; pose_asset?: string; start_frame: number; end_frame: number }[];
    visual_events?: VisualEvent[];
    sound_events?: { event_id: string; asset?: string; start_frame: number; end_frame: number; source_start_frame?: number; volume?: number }[];
  };
  animation?: {
    shot_id: string;
    characters?: {
      character_id: string;
      pose_clips: {
        clip_id: string; start_frame: number; anticipation_end_frame?: number; action_end_frame?: number;
        hold_end_frame?: number; end_frame: number; base_pose: string; action_pose: string; smear?: boolean;
        rotation_deg?: number; translate?: {x: number; y: number}; squash_stretch?: {x: number; y: number};
      }[];
    }[];
    effects?: VisualEvent[];
  };
};
type RenderData = {
  version?: string;
  format: { width: number; height: number; fps: number; duration_frames: number };
  asset_mode: string;
  shots: ShotPlan[];
  scene_manifest?: any;
  character_assets?: any;
  presentation?: { subtitle?: { font_height_ratio: number; emphasis_scale: number; hold_frames: number } };
  audio_bed?: { asset: string; volume?: number };
};
const data = input as RenderData;
const sceneAssetLoader = data.scene_manifest && data.character_assets
  ? createAssetLoader(data.scene_manifest, data.character_assets)
  : null;

function evaluateShotCharacters(shot: ShotPlan, frame: number) {
  return new Map((shot.character_performance ?? []).map(performance => {
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
}

const SceneShot = ({ shot }: { shot: ShotPlan }) => {
  const frame = useCurrentFrame();
  const context = createShotContext(shot, frame, data.format);
  const camera = evaluateCamera(frame, context);
  const characterStates = evaluateShotCharacters(shot, frame);
  const sceneGraph = buildSceneGraph({
    sceneManifest: data.scene_manifest,
    characterAssetManifest: data.character_assets,
    sceneInstances: shot.scene_instances ?? [],
    visibleObjects: shot.visible_objects ?? [],
    viewport: data.format,
  });
  const caption = selectSubtitleCue(shot.dialogue, frame, data.presentation?.subtitle?.hold_frames ?? 0);
  const v2Effects = evaluateEffects(frame, shot.animation?.effects ?? []);
  const v2Shake = v2Effects.screenShakeX;

  return (
    <AbsoluteFill style={{ overflow: 'hidden', transform: v2Shake ? `translate(${v2Shake}px, 0px)` : undefined }}>
      {sceneGraph.nodes.map(node => {
        const depth = node.depth as Depth;
        const depthTransform = evaluateLayerTransform(camera, depth, data.format);
        if (node.nodeType === 'character') {
          const state = characterStates.get(node.id);
          const poseTrack = shot.animation?.characters?.find(item => item.character_id === node.id)?.pose_clips ?? [];
          const poseState = evaluatePoseTrack(frame, poseTrack);
          const baseRoot = state?.root ?? { x: 0, y: 0, scale: 1, rotation: 0, opacity: 1 };
          const root = {
            x: baseRoot.x + (poseState?.root.x ?? 0),
            y: baseRoot.y + (poseState?.root.y ?? 0),
            scale: baseRoot.scale,
            rotation: baseRoot.rotation + (poseState?.root.rotation ?? 0),
            opacity: baseRoot.opacity,
            scaleX: poseState?.root.scaleX ?? 1,
            scaleY: poseState?.root.scaleY ?? 1,
          };
          const v2State = poseState?.pose
            ? {...state, states: {...(state?.states ?? {}), pose: `pose:${poseState.pose}`}}
            : state;
          return (
            <AbsoluteFill key={node.id} style={{ transformOrigin: '0 0', transform: depthTransform.transform }}>
              <div style={{
                position: 'absolute', left: node.x + root.x, top: node.y + root.y,
                width: node.referenceSize.width, height: node.referenceSize.height,
                transformOrigin: `${node.rootAnchor[0] * 100}% ${node.rootAnchor[1] * 100}%`,
                transform: `scale(${node.scaleX * root.scale * root.scaleX}, ${node.scaleY * root.scale * root.scaleY}) rotate(${root.rotation}deg)`,
                opacity: root.opacity,
              }}>
                {node.parts.map(part => {
                  const acting = { part: part.partId, pivot: part.pivot, keys: [] };
                  const local = evaluateCharacterPart(frame, acting, v2State);
                  const asset = resolveCharacterLayerAsset({
                    asset: part.asset, state_assets: part.state_assets, acting,
                  }, v2State, frame);
                  return (
                    <Img key={part.id} src={staticFile(sceneAssetLoader!.resolve(asset))} style={{
                      position: 'absolute', left: part.x + local.x, top: part.y + local.y,
                      width: part.width, height: part.height, opacity: local.opacity,
                      transformOrigin: `${part.pivot[0] * 100}% ${part.pivot[1] * 100}%`,
                      transform: `rotate(${local.rotation}deg) scale(${local.scale})`,
                    }} />
                  );
                })}
              </div>
            </AbsoluteFill>
          );
        }
        return (
          <AbsoluteFill key={node.id} style={{ transformOrigin: '0 0', transform: depthTransform.transform }}>
            <Img src={staticFile(sceneAssetLoader!.resolve(node.asset))} style={{
              position: 'absolute', left: node.x, top: node.y, width: node.width, height: node.height,
              objectFit: node.fit === 'cover' ? 'cover' : node.fit === 'contain' ? 'contain' : 'fill',
            }} />
          </AbsoluteFill>
        );
      })}
      <ComicEffects events={[...(shot.timeline?.visual_events ?? []), ...(shot.animation?.effects ?? [])]} frame={frame} width={data.format.width} height={data.format.height} />
      {caption && (
        <div style={{
          position: 'absolute', zIndex: 1000, bottom: '7%', left: '6%', right: '6%', textAlign: 'center',
          color: 'white', fontSize: Math.round(data.format.height * (data.presentation?.subtitle?.font_height_ratio ?? 0.045) * ((caption.emphasis === 'punchline' || caption.emphasis === 'surprise') ? (data.presentation?.subtitle?.emphasis_scale ?? (0.052 / 0.045)) : 1)),
          fontFamily: 'Arial, "Microsoft YaHei", sans-serif', fontWeight: 700,
          whiteSpace: 'pre-wrap', overflowWrap: 'anywhere',
          textShadow: '-2px -2px 0 #172332, 2px -2px 0 #172332, -2px 2px 0 #172332, 2px 2px 0 #172332',
        }}>{caption.text}</div>
      )}
    </AbsoluteFill>
  );
};

const Shot = ({ shot }: { shot: ShotPlan }) => {
  const frame = useCurrentFrame();
  const context = createShotContext(data.version === '0.4' ? shot : { ...shot, camera: undefined }, frame, data.format);
  const camera = evaluateCamera(frame, context);
  const characterStates = evaluateShotCharacters(shot, frame);
  const caption = selectSubtitleCue(shot.dialogue, frame, data.presentation?.subtitle?.hold_frames ?? 0);
  const timeline = shot.timeline ?? {};
  const visualEvents = timeline.visual_events ?? [];
  const shake = shakeOffset(frame, visualEvents);

  return (
    <AbsoluteFill style={{ overflow: 'hidden' }}>
      <AbsoluteFill style={{ transform: shake ? `translate(${shake}px, 0px)` : undefined }}>
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
        pose = expressionAsset(frame, layer.layer_id, timeline.expression_events ?? []) ?? pose;
        if (acting?.speech) {
          if (performanceState) {
            pose = performanceState.mouth.state === 'open' ? acting.speech.open_asset : acting.speech.closed_asset;
          } else {
            pose = mouthAsset(frame, acting.speech, shot.dialogue ?? [], timeline.mouth_events ?? []);
          }
        }
        const prop = propTransform(frame, drivingPropMotion(layer, shot.layers));
        const region = layer.region;
        const depthTransform = evaluateLayerTransform(camera, layer.depth ?? 'character', data.format);
        const root = performanceState?.root;

        return (
          <AbsoluteFill
            key={layer.layer_id}
            style={{ transformOrigin: '0 0', transform: depthTransform.transform }}
          >
            <AbsoluteFill style={prop ? { transformOrigin: prop.origin, transform: prop.transform } : undefined}>
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
          </AbsoluteFill>
        );
      })}
      </AbsoluteFill>
      <ComicEffects events={visualEvents} frame={frame} width={data.format.width} height={data.format.height} />
      {caption && (
        <div style={{
          position: 'absolute', bottom: '10%', left: '6%', right: '6%', textAlign: 'center',
          color: 'white', fontSize: Math.round(data.format.height * (data.presentation?.subtitle?.font_height_ratio ?? 0.045) * ((caption.emphasis === 'punchline' || caption.emphasis === 'surprise') ? (data.presentation?.subtitle?.emphasis_scale ?? (0.052 / 0.045)) : 1)),
          fontFamily: 'Arial, "Microsoft YaHei", sans-serif', fontWeight: 700,
          whiteSpace: 'pre-wrap', overflowWrap: 'anywhere',
          textShadow: '-2px -2px 0 black, 2px -2px 0 black, -2px 2px 0 black, 2px 2px 0 black',
        }}>{captionRuns(caption.text, frame, visualEvents).map((run, index) => (
          run.highlight ? <span key={index} style={{ color: run.color }}>{run.text}</span> : <React.Fragment key={index}>{run.text}</React.Fragment>
        ))}</div>
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
        {data.scene_manifest ? <SceneShot shot={shot} /> : <Shot shot={shot} />}
        {shot.dialogue?.filter(cue => cue.audio).map((cue, index) => (
          <Sequence key={index} from={cue.start_frame} durationInFrames={cue.end_frame - cue.start_frame}>
            <Audio src={staticFile(cue.audio!)} />
          </Sequence>
        ))}
        {(shot.timeline?.sound_events ?? []).filter(event => event.asset).map(event => (
          <Sequence key={event.event_id} from={event.start_frame} durationInFrames={event.end_frame - event.start_frame}>
            <Audio src={staticFile(event.asset!)} startFrom={event.source_start_frame ?? 0} volume={event.volume ?? 0.35} />
          </Sequence>
        ))}
      </Sequence>
    ))}
    {data.audio_bed && <Audio src={staticFile(data.audio_bed.asset)} loop volume={data.audio_bed.volume ?? 0.15} />}
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
