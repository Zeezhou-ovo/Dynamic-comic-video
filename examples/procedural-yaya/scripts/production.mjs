import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';

const root = resolve(import.meta.dirname, '..');
const planPath = resolve(root, 'production/plan.json');
const plan = JSON.parse(readFileSync(planPath, 'utf8'));
const reviewPath = resolve(root, 'out/review/visual_review.json');
const sourceHash = () => {
  const hash = createHash('sha256');
  for (const file of [planPath, ...(plan.source_files || []).map(name => resolve(root, name))])
    hash.update(readFileSync(file));
  return hash.digest('hex');
};
const errors = [];
const required = (value, label) => {
  if (typeof value !== 'string' || !value.trim()) errors.push(`${label} is empty`);
};

required(plan.project_id, 'project_id');
if (!Array.isArray(plan.source_files) || !plan.source_files.length ||
    plan.source_files.some(name => typeof name !== 'string' || name.startsWith('/') || name.includes('..') || !existsSync(resolve(root, name))))
  errors.push('source_files must list existing project-relative files');
required(plan.character?.id, 'character.id');
required(plan.scene?.space, 'scene.space');
if (!Array.isArray(plan.character?.identity_anchors) || plan.character.identity_anchors.length < 3)
  errors.push('character needs at least three identity anchors');
const { width, height, fps, duration_frames: total } = plan.format || {};
if (![width, height, fps, total].every(Number.isInteger) || width % 2 || height % 2 || fps <= 0 || total <= 0)
  errors.push('format needs even dimensions and positive integer fps/duration_frames');
const beatIds = new Set((plan.beats || []).map(b => b.id));
if (beatIds.size !== (plan.beats || []).length || !beatIds.size) errors.push('beats must have unique ids');
let cursor = 0;
const shotIds = new Set();
for (const shot of plan.shots || []) {
  required(shot.id, 'shot.id');
  if (shotIds.has(shot.id)) errors.push(`duplicate shot ${shot.id}`);
  shotIds.add(shot.id);
  if (!beatIds.has(shot.beat_id)) errors.push(`${shot.id}: unknown beat ${shot.beat_id}`);
  if (shot.start_frame !== cursor) errors.push(`${shot.id}: timeline gap or overlap at frame ${cursor}`);
  if (!Number.isInteger(shot.duration_frames) || shot.duration_frames < 2) errors.push(`${shot.id}: invalid duration`);
  cursor += shot.duration_frames || 0;
  for (const field of ['event', 'reaction', 'incoming_state', 'outgoing_state', 'transition_in', 'transition_out', 'handoff'])
    required(shot[field], `${shot.id}.${field}`);
  let readCursor = 0;
  for (const read of shot.reads || []) {
    if (read.start_frame !== readCursor || !Number.isInteger(read.end_frame) || read.end_frame <= read.start_frame)
      errors.push(`${shot.id}: reader times must be contiguous and positive`);
    readCursor = read.end_frame;
    required(read.meaning, `${shot.id}.read.meaning`);
  }
  if (readCursor !== shot.duration_frames) errors.push(`${shot.id}: reads do not cover the whole shot`);
}
if (cursor !== total) errors.push(`shot duration ${cursor} differs from format duration ${total}`);
if (new Set((plan.shots || []).map(s => s.beat_id)).size !== beatIds.size) errors.push('some narrative beats lack a shot');
for (let i = 1; i < (plan.shots || []).length; i++) {
  const previous = plan.shots[i - 1], current = plan.shots[i];
  if (previous.transition_out !== current.transition_in)
    errors.push(`${previous.id}/${current.id}: transition does not match at the seam`);
}
if (errors.length) {
  errors.forEach(e => console.error(`production plan: ${e}`));
  process.exit(1);
}

const command = process.argv[2] || 'check';
const generatedPath = resolve(root, 'src/generated/shot_plan.js');
if (command === 'check') {
  console.log(`${plan.project_id}: ${plan.shots.length} shots, ${total} frames, ${total / fps}s; beats and seams checked`);
} else if (command === 'sync') {
  const generated = `// Generated from production/plan.json. Edit the plan, then run scripts/production.mjs sync.\nconst SHOT_PLAN = ${JSON.stringify({ fps, duration_frames: total, shots: plan.shots.map(s => ({ id: s.id, start_frame: s.start_frame, duration_frames: s.duration_frames })) }, null, 2)};\n`;
  mkdirSync(dirname(generatedPath), { recursive: true });
  if (!existsSync(generatedPath) || readFileSync(generatedPath, 'utf8') !== generated)
    writeFileSync(generatedPath, generated);
  console.log(`synced ${generatedPath}`);
} else if (command === 'sheets') {
  const result = [];
  for (const shot of plan.shots) {
    const frames = [shot.start_frame + 2,
      ...shot.reads.map(r => shot.start_frame + Math.floor((r.start_frame + r.end_frame) / 2)),
      shot.start_frame + shot.duration_frames - 2];
    const times = [...new Set(frames)].map(f => (f / fps).toFixed(3));
    const output = `out/review/${shot.id.toLowerCase()}.jpg`;
    const run = spawnSync(resolve(root, 'scripts/render-local.sh'),
      [`--sheet=${times.join(',')}`, `--cols=${times.length}`, '--w=360', `--out=${output}`],
      { cwd: root, stdio: 'inherit' });
    if (run.status !== 0) process.exit(run.status || 1);
    result.push({ shot_id: shot.id, image: output, times, reviewed: false,
      inspect: ['character identity', 'event readability', 'contacts', 'transition', 'reaction hold'] });
  }
  writeFileSync(reviewPath, JSON.stringify({ source_sha256: sourceHash(), shots: result }, null, 2) + '\n');
  console.log(`wrote ${reviewPath}; review flags remain false until images are inspected`);
} else if (command === 'approve') {
  if (!existsSync(reviewPath)) {
    console.error('run sheets and inspect the images before approving');
    process.exit(1);
  }
  const review = JSON.parse(readFileSync(reviewPath, 'utf8'));
  if (review.source_sha256 !== sourceHash()) {
    console.error('source changed since the review sheets were rendered; rerun sheets');
    process.exit(1);
  }
  const shotId = process.argv.find(x => x.startsWith('--shot='))?.slice(7);
  const note = process.argv.find(x => x.startsWith('--note='))?.slice(7);
  const item = review.shots.find(s => s.shot_id === shotId);
  if (!item || !note?.trim()) {
    console.error('usage: node scripts/production.mjs approve --shot=A --note="what you observed"');
    process.exit(2);
  }
  item.reviewed = true;
  item.note = note;
  item.reviewed_at = new Date().toISOString();
  writeFileSync(reviewPath, JSON.stringify(review, null, 2) + '\n');
  console.log(`approved visual review for shot ${shotId}`);
} else {
  console.error('usage: node scripts/production.mjs check|sync|sheets|approve');
  process.exit(2);
}
