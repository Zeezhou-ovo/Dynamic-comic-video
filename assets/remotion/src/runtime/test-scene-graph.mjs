import assert from 'node:assert/strict';
import { createAssetLoader } from './asset-loader.mjs';
import { buildSceneGraph } from './scene-graph.mjs';

const sceneManifest = {
  scene_id: 'test', reference_size: { width: 960, height: 540 },
  layers: [
    { id: 'root', parent_id: null, kind: 'group', depth: 'background', z: 0, visible: true },
    { id: 'bg', parent_id: 'root', kind: 'render_layer', depth: 'background', asset: 'scene/bg.png', fit: 'canvas', z: 0, visible: true },
    { id: 'mid', parent_id: 'root', kind: 'render_layer', depth: 'midground', asset: 'scene/mid.png', fit: 'canvas', z: 5, visible: true },
    { id: 'people', parent_id: 'root', kind: 'group', depth: 'character', z: 10, visible: true },
  ],
  objects: [{ id: 'book', parent_id: 'root', asset: 'scene/book.png', depth: 'foreground',
    position: [0.5, 0.75], size: [0.2, 0.1], pivot: [0.5, 0.5], z: 30, visible: true }],
  character_slots: { left: { parent_id: 'people', position: [0.3, 0.82], scale: 0.8, facing: 1, z: 12, depth: 'character' } },
};
const characterAssetManifest = { characters: [{
  character_id: 'a', reference_size: { width: 260, height: 360 }, root_anchor: [0.5, 0.95],
  parts: { body: { asset: 'chars/a/body.png', pixel_size: { width: 260, height: 360 }, anchor: [0.5, 0.95],
    pivot: [0.5, 0.95], depth: 'character', z: 10, state_assets: { happy: 'chars/a/happy.png' } } },
}] };
const assetLoader = createAssetLoader(sceneManifest, characterAssetManifest);
assert.equal(assetLoader.resolve('chars/a/happy.png'), 'chars/a/happy.png');
assert.throws(() => assetLoader.resolve('chars/a/unlisted.png'), /absent from the manifests/);
assert.throws(() => createAssetLoader({ layers: [{ asset: '../secret.png' }], objects: [] }, { characters: [] }), /Invalid manifest asset path/);

const args = { sceneManifest, characterAssetManifest,
  sceneInstances: [{ character_id: 'a', slot_id: 'left', visible: true }],
  visibleObjects: ['book'], viewport: { width: 960, height: 540 } };
const graph = buildSceneGraph(args);
const repeat = buildSceneGraph(args);
assert.deepEqual(graph, repeat, 'Scene Graph flattening must be deterministic');
assert.deepEqual(graph.nodes.map((node) => node.id), ['bg', 'mid', 'a', 'book']);
const character = graph.nodes.find((node) => node.id === 'a');
assert.equal(character.rootWorldX, 288);
assert.ok(Math.abs(character.rootWorldY - 442.8) < 1e-8);
assert.equal(character.x, 158);
assert.ok(Math.abs(character.y - 100.8) < 1e-8);
assert.equal(character.parts[0].asset, 'chars/a/body.png');
assert.equal(character.parts[0].width, 260);
assert.deepEqual(graph.nodes.find((node) => node.id === 'book').depth, 'foreground');
console.log('PASS: scene graph/asset-loader cases');
