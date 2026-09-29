import { readFileSync } from 'node:fs';

const shots = new Set(['wide', 'medium', 'close_up']);
const motions = new Set(['static', 'push_in', 'pull_out', 'pan', 'follow', 'reveal']);
const transitions = new Set(['cut', 'dissolve', 'fade', 'foreground_wipe']);
const lights = new Set(['none', 'subtle', 'strong']);
const emphasis = new Set(['shot_size_change', 'push_in', 'character_reaction', 'lighting_change', 'intentional_pause']);
const layers = ['foreground', 'character', 'midground', 'background', 'sky'];
const required = ['narrative_goal', 'visual_focus', 'camera_shot', 'camera_motion', 'primary_action',
  'secondary_motion', 'depth_layers', 'parallax_enabled', 'ambient_motion', 'lighting_change',
  'pause_before', 'pause_after', 'transition', 'important_moment', 'emphasis'];
const nonempty = v => typeof v === 'string' && v.trim().length > 0;
const check = (ok, message) => { if (!ok) throw new Error(`Animation plan: ${message}`); };

export function validatePlan(plan) {
  check(plan?.planVersion === 3, 'new projects require planVersion 3');
  for (const key of ['fps', 'duration', 'width', 'height'])
    check(typeof plan[key] === 'number' && Number.isFinite(plan[key]) && plan[key] > 0, `${key} must be positive`);
  check(Array.isArray(plan.shots) && plan.shots.length > 0, 'shots must be a non-empty array');
  let previous = 0, moving = 0, staticWithoutReason = [];
  for (const [i, scene] of plan.shots.entries()) {
    check(Number.isFinite(scene.start) && Number.isFinite(scene.end), `scene ${i} needs numeric start/end`);
    check(Math.abs(scene.start - previous) < 1e-6 && scene.end > scene.start && scene.end <= plan.duration,
      `scene ${i} must follow the previous scene without a gap`);
    check(nonempty(scene.action), `scene ${i} needs action`);
    const a = scene.animation_plan;
    check(a && typeof a === 'object', `scene ${i} needs animation_plan before rendering`);
    for (const key of required) check(Object.hasOwn(a, key), `scene ${i} missing ${key}`);
    for (const key of ['narrative_goal', 'visual_focus', 'primary_action'])
      check(nonempty(a[key]), `scene ${i} needs non-empty ${key}`);
    check(shots.has(a.camera_shot), `scene ${i} has invalid camera_shot`);
    check(motions.has(a.camera_motion), `scene ${i} has invalid camera_motion`);
    check(lights.has(a.lighting_change), `scene ${i} has invalid lighting_change`);
    check(transitions.has(a.transition), `scene ${i} has invalid transition`);
    for (const [key, max] of [['secondary_motion', 2], ['ambient_motion', 3]])
      check(Array.isArray(a[key]) && a[key].length <= max && a[key].every(nonempty),
        `scene ${i} ${key} allows at most ${max} non-empty entries`);
    check(a.depth_layers && typeof a.depth_layers === 'object' &&
      Object.keys(a.depth_layers).sort().join() === [...layers].sort().join() &&
      layers.every(k => a.depth_layers[k] === null || nonempty(a.depth_layers[k])),
      `scene ${i} must explicitly define all five depth_layers`);
    check(typeof a.parallax_enabled === 'boolean', `scene ${i} parallax_enabled must be boolean`);
    const active = layers.filter(k => a.depth_layers[k] !== null).length;
    if (a.camera_motion !== 'static') {
      moving++;
      check(nonempty(a.camera_purpose), `scene ${i} moving camera needs camera_purpose`);
      check(active < 2 || a.parallax_enabled, `scene ${i} moving camera with depth requires parallax`);
    } else if (!nonempty(a.static_necessity)) staticWithoutReason.push(i);
    for (const key of ['pause_before', 'pause_after'])
      check(typeof a[key] === 'number' && Number.isFinite(a[key]) && a[key] >= 0,
        `scene ${i} ${key} must be non-negative seconds`);
    check(a.pause_before + a.pause_after <= scene.end - scene.start,
      `scene ${i} pauses exceed scene duration`);
    check(typeof a.important_moment === 'boolean', `scene ${i} important_moment must be boolean`);
    check(Array.isArray(a.emphasis) && a.emphasis.every(v => emphasis.has(v)),
      `scene ${i} has invalid emphasis`);
    check(!a.important_moment || a.emphasis.length > 0,
      `scene ${i} important moment needs visual emphasis`);
    previous = scene.end;
  }
  check(Math.abs(previous - plan.duration) < 1e-6, 'shots must cover the full duration');
  check(moving * 2 >= plan.shots.length || staticWithoutReason.length === 0,
    `fewer than half of scenes move; static scenes ${staticWithoutReason.join(', ')} need static_necessity`);
  return plan;
}

export function loadPlan(path = 'plan.json') {
  let plan;
  try { plan = JSON.parse(readFileSync(path, 'utf8')); }
  catch (error) { throw new Error(`Animation plan: cannot read ${path}: ${error.message}`); }
  return validatePlan(plan);
}
