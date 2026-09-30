const DEPTHS = new Set(['foreground', 'character', 'midground', 'background', 'sky']);

/** Flatten manifest hierarchy into deterministic renderer nodes without losing parents. */
export function buildSceneGraph({ sceneManifest, characterAssetManifest, sceneInstances, visibleObjects, viewport }) {
  const { width, height } = viewport;
  const ref = sceneManifest.reference_size;
  const sx = width / ref.width;
  const sy = height / ref.height;
  const nodes = [];
  for (const layer of sceneManifest.layers) {
    if (layer.kind === 'group' || !layer.visible) continue;
    if (!DEPTHS.has(layer.depth)) throw new TypeError(`Unsupported Scene Graph depth: ${layer.depth}`);
    nodes.push({
      id: layer.id, parentId: layer.parent_id, nodeType: 'image', depth: layer.depth,
      z: layer.z, visible: layer.visible, asset: layer.asset, fit: layer.fit,
      x: 0, y: 0, width: ref.width * sx, height: ref.height * sy,
    });
  }
  const visibleObjectIds = new Set(visibleObjects ?? sceneManifest.objects.map((item) => item.id));
  for (const object of sceneManifest.objects) {
    if (!object.visible || !visibleObjectIds.has(object.id)) continue;
    const objectWidth = object.size[0] * width;
    const objectHeight = object.size[1] * height;
    const anchorX = object.position[0] * width;
    const anchorY = object.position[1] * height;
    nodes.push({
      id: object.id, parentId: object.parent_id, nodeType: 'image', depth: object.depth,
      z: object.z, visible: true, asset: object.asset, fit: 'contain',
      x: anchorX - objectWidth * object.pivot[0], y: anchorY - objectHeight * object.pivot[1],
      width: objectWidth, height: objectHeight,
    });
  }
  const charactersById = new Map(characterAssetManifest.characters.map((item) => [item.character_id, item]));
  const slots = sceneManifest.character_slots;
  for (const instance of sceneInstances ?? []) {
    if (!instance.visible) continue;
    const manifest = charactersById.get(instance.character_id);
    const slot = slots[instance.slot_id];
    if (!manifest || !slot) throw new Error(`Unresolved Scene Character Instance: ${instance.character_id}/${instance.slot_id}`);
    const charScaleX = sx * slot.scale;
    const charScaleY = sy * slot.scale;
    const rootWorldX = slot.position[0] * width;
    const rootWorldY = slot.position[1] * height;
    const rootAnchor = manifest.root_anchor;
    const charW = manifest.reference_size.width;
    const charH = manifest.reference_size.height;
    // The CSS root scales around rootAnchor; keep the unscaled layout origin so
    // that the anchor itself lands exactly on the normalized slot position.
    const rootX = rootWorldX - rootAnchor[0] * charW;
    const rootY = rootWorldY - rootAnchor[1] * charH;
    const parts = Object.entries(manifest.parts).map(([partId, part]) => {
      const partWidth = part.pixel_size.width;
      const partHeight = part.pixel_size.height;
      let localX = part.anchor[0] * charW - part.pivot[0] * partWidth;
      const localY = part.anchor[1] * charH - part.pivot[1] * partHeight;
      if (slot.facing === -1) localX = rootAnchor[0] * charW - (localX - rootAnchor[0] * charW) - partWidth;
      return {
        id: `${instance.character_id}:${partId}`, parentId: instance.character_id,
        nodeType: 'character_part', characterId: instance.character_id, partId,
        depth: part.depth ?? slot.depth, z: slot.z + part.z, visible: true,
        asset: part.asset, state_assets: part.state_assets, pivot: part.pivot,
        x: localX, y: localY, width: partWidth, height: partHeight,
      };
    });
    nodes.push({
      id: instance.character_id, parentId: slot.parent_id, nodeType: 'character',
      depth: slot.depth, z: slot.z, visible: true, x: rootX, y: rootY,
      rootWorldX, rootWorldY, rootAnchor, referenceSize: manifest.reference_size,
      scaleX: charScaleX, scaleY: charScaleY, facing: slot.facing, parts,
    });
  }
  nodes.sort((a, b) => a.z - b.z || a.id.localeCompare(b.id));
  return Object.freeze({ sceneId: sceneManifest.scene_id, nodes: Object.freeze(nodes) });
}
