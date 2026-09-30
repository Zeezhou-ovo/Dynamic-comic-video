/** Build a project-scoped allow-list from Scene and Character Asset Manifests. */
export function createAssetLoader(sceneManifest, characterAssetManifest) {
  const registered = new Set();
  const add = (path) => {
    if (typeof path !== 'string' || !path || path.startsWith('/') || path.split(/[\\/]/).includes('..')) {
      throw new TypeError(`Invalid manifest asset path: ${path}`);
    }
    registered.add(path);
  };
  for (const layer of sceneManifest.layers ?? []) if (layer.asset) add(layer.asset);
  for (const object of sceneManifest.objects ?? []) add(object.asset);
  for (const character of characterAssetManifest.characters ?? []) {
    for (const part of Object.values(character.parts ?? {})) {
      add(part.asset);
      for (const path of Object.values(part.state_assets ?? {})) add(path);
    }
  }
  return Object.freeze({
    has: (path) => registered.has(path),
    resolve: (path) => {
      if (!registered.has(path)) throw new Error(`Renderer requested an asset absent from the manifests: ${path}`);
      return path;
    },
    paths: Object.freeze([...registered].sort()),
  });
}
