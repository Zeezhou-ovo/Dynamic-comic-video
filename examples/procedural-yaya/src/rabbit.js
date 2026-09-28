// Yaya: a small white forest rabbit. Coordinates are in body units; (x, y) is the ground point.
// All pose fields are computed from time by the scene, so every frame can be rendered independently.
function rabbit(x, y, u, t, pose = {}) {
  const mood = pose.mood || 'curious';
  const hop = pose.hop || 0;
  const lean = pose.lean || 0;
  const reach = pose.reach || 0;
  const look = pose.look || 0;
  const stride = pose.stride || 0;
  const squash = pose.squash || 0;
  const ear = .09 * Math.sin(t * 3.3) + .15 * spring(t, pose.earKick ?? 100) - .12 * Math.abs(stride);
  const fur = '#F3EEE1', shade = '#D8D7D5', inner = '#DA9C9E', scarf = '#DB735D';

  boilSeed('rabbit-shadow');
  paint(ellPts(x, y + 7, 3.7 * u * (1 - hop * .12), .62 * u, 24, 1),
    { wash: '#233C47', washOp: 75, ink: null });
  push(); translate(x, y - hop * u); rotate(lean); scale(1 + squash * .28, 1 - squash);

  boilSeed('rabbit-tail');
  paint(ellPts(-2.35 * u, -2.35 * u, .95 * u, .95 * u, 21, u * .025),
    { wash: fur, ink: PAL.ink, sw: 1.2 });
  boilSeed('rabbit-feet');
  for (const side of [-1, 1]) {
    paint(ellPts(side * 1.25 * u + side * stride * .28 * u,
      -.35 * u - Math.max(0, side * stride) * .35 * u, 1.55 * u, .55 * u, 19, u * .025),
      { wash: shade, ink: PAL.ink, sw: 1.1 });
  }
  boilSeed('rabbit-body');
  paint(ellPts(0, -3.2 * u, 2.45 * u, 3.2 * u, 28, u * .035),
    { wash: fur, ink: PAL.ink, sw: 1.5 });
  paint(ellPts(.35 * u, -2.8 * u, 1.25 * u, 1.85 * u, 23, u * .03),
    { wash: '#FFF8E8', ink: null });

  boilSeed('rabbit-arm-left');
  paint(ellPts(-2.05 * u, -3.4 * u, .9 * u, 1.45 * u, 18, u * .025, -.35),
    { wash: fur, ink: PAL.ink, sw: 1 });
  boilSeed('rabbit-arm-right');
  const pawX = (2.05 + 1.7 * reach) * u, pawY = (-3.35 - 1.6 * reach) * u;
  if (reach > .15) {
    paint(ribbon([[1.8 * u, -3.6 * u], [2.55 * u, -3.65 * u - .6 * reach * u], [pawX, pawY]],
      .95 * u, .68 * u), { wash: fur, ink: PAL.ink, sw: 1 });
  } else {
    push(); translate(2 * u, -3.4 * u); rotate(-.65 * reach);
    paint(ellPts(.25 * u, -.1 * u, .85 * u, 1.4 * u, 18, u * .025, .4),
      { wash: fur, ink: PAL.ink, sw: 1 });
    pop();
  }
  if (reach > .15) paint(ellPts(pawX, pawY, .58 * u, .48 * u, 16),
    { wash: fur, ink: PAL.ink, sw: .9 });

  boilSeed('rabbit-ears');
  for (const side of [-1, 1]) {
    push(); translate(side * 1.18 * u, -9.25 * u);
    rotate(side * (.2 + ear + .045 * Math.sin(t * 2.4 + side)));
    paint(ellPts(0, -1.95 * u, .76 * u, 2.65 * u, 26, u * .035),
      { wash: fur, ink: PAL.ink, sw: 1.35 });
    paint(ellPts(0, -2.0 * u, .36 * u, 1.85 * u, 22, u * .025),
      { wash: inner, ink: null });
    pop();
  }
  boilSeed('rabbit-head');
  paint(ellPts(0, -7.9 * u, 2.72 * u, 2.45 * u, 31, u * .04),
    { wash: fur, ink: PAL.ink, sw: 1.5 });
  for (const side of [-1, 1]) {
    paint(ellPts(side * 1.35 * u, -7.35 * u, .58 * u, .36 * u, 16),
      { wash: '#EDC7B8', washOp: 185, ink: null });
    const blink = mood !== 'surprised' && frac(t * .37 + .14 * side) < .035;
    if (mood === 'happy' || blink) {
      inkLine([[side * 1.35 * u - .36 * u, -8.15 * u], [side * 1.35 * u, -8.42 * u], [side * 1.35 * u + .36 * u, -8.15 * u]],
        1.2, PAL.ink, 'inkfine', .55);
    } else {
      const eyeX = side * 1.35 * u + look * .13 * u;
      paint(ellPts(eyeX, -8.15 * u, .24 * u,
        mood === 'surprised' ? .45 * u : .32 * u, 13), { wash: PAL.ink, ink: null });
      paint(ellPts(eyeX - .065 * u, -8.27 * u, .065 * u, .075 * u, 10),
        { wash: '#FFF9EE', ink: null });
    }
  }
  paint(ellPts(.1 * u, -7.25 * u, .28 * u, .2 * u, 12), { wash: '#C77477', ink: null });
  if (mood === 'surprised') {
    paint(ellPts(.1 * u, -6.7 * u, .17 * u, .27 * u, 12), { wash: PAL.ink, ink: null });
  } else {
    const smile = mood === 'happy' ? .37 : .12;
    inkLine([[-.48 * u, -6.87 * u], [.1 * u, (-6.87 + smile) * u], [.67 * u, -6.87 * u]],
      1.1, PAL.ink, 'inkfine', .6);
  }
  boilSeed('rabbit-scarf');
  paint(rrPts(-1.55 * u, -5.95 * u, 3.25 * u, .57 * u, .2 * u, u * .025),
    { wash: scarf, ink: PAL.ink, sw: .9 });
  push(); translate(1.12 * u, -5.64 * u); rotate(-.12 - .2 * stride + .05 * Math.sin(t * 2));
  paint(rrPts(-.22 * u, 0, .68 * u, 1.3 * u, .18 * u, u * .02),
    { wash: scarf, ink: PAL.ink, sw: .9 });
  pop();
  pop();
}
