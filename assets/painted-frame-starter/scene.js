// Replace drawWorld(t) with the project's story, characters, and shared painted environment.
const VIDEO = { width: 1280, height: 720, fps: 24, duration: 8, boilFps: 12 };
window.videoConfig = VIDEO;
let frameTime = 0, output, paper;

function painted(points, color, outline = '#302637') {
  brush.wash(color, 255);
  brush.noFill(); brush.noHatch(); brush.noStroke();
  brush.polygon(points);
  if (outline) {
    brush.noWash(); brush.set('ink', outline, 1);
    brush.beginShape(0);
    for (const [x, y] of points) brush.vertex(x, y);
    brush.endShape(true);
  }
}

function setup() {
  createCanvas(VIDEO.width, VIDEO.height, WEBGL);
  pixelDensity(1); noLoop();
  brush.scaleBrushes(3.4);
  brush.add('ink', { type: 'default', weight: 4, scatter: .2, sharpness: .8,
    grain: 35, opacity: 230, spacing: .2, pressure: [1.1, .75], rotate: 'natural' });
  paper = createGraphics(VIDEO.width, VIDEO.height);
  paper.background('#f3ebdc');
  output = document.getElementById('output');
  window.ready = true;
}

function drawWorld(t) {
  // Executable sample: one changing sky, a shared ground, and a moving light.
  const progress = Math.max(0, Math.min(1, t / VIDEO.duration));
  painted([[0, 0], [1280, 0], [1280, 490], [0, 490]],
    progress < .5 ? '#344477' : '#cd8c9a', null);
  painted([[0, 475], [1280, 475], [1280, 720], [0, 720]], '#baaa92');
  const x = 180 + progress * 920, y = 350 - Math.sin(progress * Math.PI) * 170;
  const points = [];
  for (let i = 0; i < 20; i++) {
    const a = i / 20 * Math.PI * 2;
    points.push([x + Math.cos(a) * 28, y + Math.sin(a) * 28]);
  }
  painted(points, '#f8d875', '#ad793b');
}

function draw() {
  push(); translate(-VIDEO.width / 2, -VIDEO.height / 2);
  randomSeed(1000 + Math.floor(frameTime * VIDEO.boilFps));
  image(paper, 0, 0);
  drawWorld(frameTime);
  pop();
}

window.renderAt = async (t) => {
  frameTime = t;
  await redraw();
  output.getContext('2d').drawImage(drawingContext.canvas, 0, 0);
  return output.toDataURL('image/png');
};
