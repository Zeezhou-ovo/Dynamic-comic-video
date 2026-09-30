export const DEPTH_STRENGTHS = Object.freeze({
  foreground: 1.2,
  character: 1.0,
  midground: 0.55,
  background: 0.2,
  sky: 0.05,
});

/** Convert the shared camera state into one depth-aware world-to-screen transform. */
export function evaluateLayerTransform(camera, depth, viewport) {
  const requestedStrength = camera.parallaxStrengths?.[depth];
  const depthStrength = Number.isFinite(requestedStrength)
    ? requestedStrength
    : (DEPTH_STRENGTHS[depth] ?? 1);
  const factor = camera.parallaxEnabled ? depthStrength : 1;
  const layerCameraX = camera.focusX + (camera.x - camera.focusX) * factor;
  const layerCameraY = camera.focusY + (camera.y - camera.focusY) * factor;
  const zoom = 1 + (camera.zoom - 1) * factor;
  const anchorX = camera.screenX * viewport.width;
  const anchorY = camera.screenY * viewport.height;

  return Object.freeze({
    depth,
    factor,
    zoom,
    translateX: anchorX - layerCameraX * zoom,
    translateY: anchorY - layerCameraY * zoom,
    transform: `translate3d(${anchorX - layerCameraX * zoom}px, ${anchorY - layerCameraY * zoom}px, 0) scale(${zoom})`,
  });
}
