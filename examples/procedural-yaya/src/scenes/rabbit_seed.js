// Yaya finds a glowing seed and grows a flower in the dusk forest.
(() => {
  const G = 875, SEED_X = 1160, PLANT_X = 1250;

  function forest(t, bloom = 0) {
    boilSeed('forest-sky');
    paint(rectPts(-400, -300, W + 800, H + 600), { wash: mixCol('#233650', '#46566A', bloom * .35), ink: null });
    paint(ellPts(810, 540, 1120, 360, 34, 7),
      { fill: '#64768B', fillOp: 55 + 20 * bloom, bleed: .27, tex: .65, ink: null });
    boilSeed('forest-moon');
    glow(1490, 180, 280, '#F5D9A2', .45 + .22 * bloom);
    paint(ellPts(1490, 180, 79, 79, 28, 2), { wash: '#F0D8AD', ink: null });
    for (let i = 0; i < 18; i++) {
      boilSeed('forest-star-' + i);
      const x = 170 + hash(i * 2) * 1550, y = 70 + hash(i * 2 + 1) * 480;
      paint(ellPts(x, y, 2.5 + hash(i + 60) * 2, 2.5 + hash(i + 60) * 2, 9),
        { wash: '#E9DCB7', washOp: 130 + 75 * Math.sin(t * 2 + i), ink: null });
    }
    for (let layer = 0; layer < 2; layer++) {
      for (let i = 0; i < 9; i++) {
        boilSeed(`tree-${layer}-${i}`);
        const x = -120 + i * 255 + layer * 105;
        const h = (layer ? 180 : 285) + 110 * hash(i * 4 + layer + 50);
        const base = G + (layer ? 9 : -68);
        const w = layer ? 30 : 22;
        paint(rectPts(x, base - h, w, h + 92, 2),
          { wash: layer ? '#2A5554' : '#344F60', ink: null });
        paint(ellPts(x + w / 2, base - h + 18, layer ? 126 : 105,
          layer ? 110 : 92, 25, 4),
          { wash: layer ? '#315E59' : '#365665', ink: null });
        paint(ellPts(x - 30, base - h + 50, layer ? 80 : 65,
          layer ? 72 : 58, 19, 3),
          { wash: layer ? '#315E59' : '#365665', ink: null });
      }
    }
    boilSeed('hills');
    paint(ellPts(960, 940, 1450, 270, 40, 3), { wash: '#42665F', ink: null });
    boilSeed('earth');
    paint(rectPts(-300, G, W + 600, 420, 3), { wash: '#355D54', ink: null });
    paint(ellPts(1060, 1110, 1040, 215, 38, 4),
      { wash: '#607B65', washOp: 95, ink: null });
    inkLine([[-300, G], [W + 300, G]], 1.1, '#213D46', 'inkfine');
    for (let i = 0; i < 19; i++) {
      boilSeed('grass-' + i);
      const x = 45 + i * 102 + hash(i + 110) * 50;
      const y = G + 20 + hash(i + 130) * 110;
      const sway = 7 * Math.sin(t * 1.4 + i);
      inkLine([[x, y], [x - 9 + sway, y - 30], [x - 13 + sway, y - 43]], .7, '#91A88B', 'inkfine', .4);
      inkLine([[x, y], [x + 12 + sway, y - 23]], .7, '#91A88B', 'inkfine', .4);
    }
    for (let i = 0; i < 5; i++) {
      boilSeed('mushroom-' + i);
      const x = 120 + i * 380 + hash(i + 170) * 80;
      const y = G + 95 + hash(i + 190) * 75;
      paint(rrPts(x - 5, y - 24, 10, 27, 3, 1), { wash: '#E3D1B6', ink: '#253F46', sw: .5 });
      paint(ellPts(x, y - 26, 23, 12, 18, 1), { wash: '#C78E78', ink: '#253F46', sw: .6 });
    }
    for (let i = 0; i < 7; i++) {
      boilSeed('firefly-' + i);
      const x = 320 + hash(i + 230) * 1300;
      const y = 450 + hash(i + 260) * 320 + 12 * Math.sin(t * (1 + hash(i + 280)) + i);
      glow(x, y, 18, '#F6D890', .12 + .11 * Math.sin(t * 2 + i));
    }
    boilSeed('foreground-trunks');
    paint(rectPts(-120, -60, 160, 930, 5), { wash: '#1A3942', ink: null });
    paint(rectPts(W - 30, -80, 150, 960, 5), { wash: '#1A3942', ink: null });
    for (const side of [-1, 1]) {
      const x = side < 0 ? 20 : W - 10;
      inkLine([[x, 205], [x - side * 130, 110], [x - side * 290, 50]],
        13, '#1A3942', 'dry', .55);
      for (let i = 0; i < 4; i++) {
        boilSeed(`corner-leaf-${side}-${i}`);
        paint(ellPts(x - side * (105 + i * 55), 65 + i * 12,
          93 - i * 10, 55 + i * 4, 20, 3),
          { wash: '#254C4B', ink: null });
      }
    }
  }

  function seed(x, y, t, alpha = 1) {
    if (alpha <= 0) return;
    boilSeed('seed');
    glow(x, y, 112 + 18 * Math.sin(t * 4), '#FFD179', .8 * alpha);
    paint(ellPts(x, y, 28, 36, 19, 1.5, .25),
      { wash: '#F8D37A', washOp: 255 * alpha, ink: '#604B44', sw: 1 });
    paint(ellPts(x - 8, y - 10, 5, 8, 11), { wash: '#FFF0B8', washOp: 235 * alpha, ink: null });
    for (let i = 0; i < 4; i++) {
      boilSeed('seed-spark-' + i);
      const a = t * (1.1 + .2 * i) + i * TAU / 4;
      const r = 44 + 9 * Math.sin(t * 3 + i);
      paint(starPts(x + Math.cos(a) * r, y + Math.sin(a) * r,
        5 + 2 * Math.sin(t * 5 + i), .3, 4),
        { wash: '#FFE8AC', washOp: 130 * alpha, ink: null });
    }
  }

  function flower(t) {
    const grow = easeOut(seg(t, 9.3, 11.25));
    if (grow <= 0) return;
    boilSeed('flower-stem');
    const top = G - 255 * grow;
    glow(PLANT_X, top, 90 + 210 * ease(seg(t, 11.5, 13.2)), '#F7C966', .25 + .6 * grow);
    inkLine([[PLANT_X, G], [PLANT_X - 12 * grow, G - 120 * grow], [PLANT_X, top]],
      2.3, '#A6C582', 'ink', .45);
    const leaf = easeOut(seg(t, 10.1, 11.4));
    for (const side of [-1, 1]) {
      paint(ellPts(PLANT_X + side * 44 * leaf, G - 105 * grow,
        46 * leaf, 17 * leaf, 17, 1, side * .35),
        { wash: '#96BC7F', ink: '#345A55', sw: .7 });
    }
    if (t > 11.12) {
      for (let i = 0; i < 7; i++) {
        boilSeed('flower-petal-' + i);
        const open = easeOut(seg(t, 11.55 + i * .075, 12.3 + i * .075));
        if (open <= 0) continue;
        const a = i * TAU / 7 + .2;
        paint(ellPts(PLANT_X + Math.cos(a) * 51 * open, top + Math.sin(a) * 51 * open,
          37 * open, 55 * open, 20, 1.5, a - Math.PI / 2),
          { wash: i % 2 ? '#F3C981' : '#F4D694', ink: '#65504C', sw: .8 });
      }
      const centre = easeOut(seg(t, 12.0, 12.8));
      if (centre > 0) {
        boilSeed('flower-centre');
        paint(ellPts(PLANT_X, top, 41 * centre, 41 * centre, 24, 1),
          { wash: '#D58D5E', ink: '#65504C', sw: 1 });
        for (let j = 0; j < 7; j++) {
          const a = j * TAU / 7;
          paint(ellPts(PLANT_X + Math.cos(a) * 19 * centre,
            top + Math.sin(a) * 18 * centre, 3, 3, 8),
            { wash: '#FBE2A5', ink: null });
        }
      }
    }
    const magic = ease(seg(t, 12.15, 13.05));
    if (magic > 0) {
      for (let i = 0; i < 9; i++) {
        boilSeed('bloom-spark-' + i);
        const angle = i * TAU / 9 + .35;
        const radius = 75 + 82 * magic + 13 * Math.sin(t * 2 + i);
        const twinkle = .55 + .45 * Math.sin(t * 5 + i);
        paint(starPts(PLANT_X + Math.cos(angle) * radius,
          top + Math.sin(angle) * radius, 6 * magic * twinkle, .3, 4),
          { wash: '#FFE6A8', washOp: 170 * magic, ink: null });
      }
    }
  }

  function shotFall(t, lt, dur) {
    camBegin(960 + 10 * Math.sin(t * .5), 540, 1.05);
    forest(t);
    rabbit(590, G, 31, t, { mood: lt < 2.55 ? 'curious' : 'surprised',
      look: ease(seg(lt, 1.1, 1.55)) * .6, earKick: 2.55 });
    if (lt >= 1.05) {
      const k = easeIn(seg(lt, 1.05, 2.55));
      const p = arcPt([1450, 140], [SEED_X, G - 35], 95, k);
      seed(p[0], p[1], t);
    }
    camEnd();
  }

  function shotPlant(t, lt, dur) {
    camBegin(1030 + 55 * ease(seg(lt, 0, 2.3)), 540 - 12 * Math.sin(lt * .7), 1.12 + .025 * ease(seg(lt, 0, 2.2)));
    forest(t);
    const move = ease(seg(lt, 0, 2.15)), x = lerp(660, 1038, move);
    const hopArc = (a, b, h) => lt > a && lt < b ? h * 4 * seg(lt, a, b) * (1 - seg(lt, a, b)) : 0;
    const hop = hopArc(.28, 1.08, 2.9) + hopArc(1.25, 2.08, 3.4);
    const stride = lt < 2.1 ? .65 * Math.sin(lt * TAU * 2.3) : 0;
    const squash = .11 * Math.exp(-18 * Math.abs(lt - .25))
      + .16 * Math.exp(-19 * Math.abs(lt - 1.1))
      + .18 * Math.exp(-19 * Math.abs(lt - 2.1));
    const reach = ease(seg(lt, 2.0, 3.0));
    const lean = .14 * ease(seg(lt, 2.1, 3.1));
    rabbit(x, G, 32, t, { mood: lt < .25 ? 'surprised' : lt < 2.3 ? 'curious' : 'happy', hop, reach, lean, stride, squash });
    const paw = [1038 + 3.7 * 32, G - 4.95 * 32];
    if (lt < 2.2) seed(SEED_X, G - 35, t);
    else if (lt < 3.1) {
      const k = ease(seg(lt, 2.2, 3.1));
      seed(lerp(SEED_X, paw[0], k), lerp(G - 35, paw[1], k), t);
    } else {
      const k = ease(seg(lt, 3.1, 4.3));
      seed(lerp(paw[0], PLANT_X, k), lerp(paw[1], G + 12, k), t,
        1 - seg(lt, 4.1, 4.55));
    }
    if (lt > 4.15) {
      boilSeed('plant-ring');
      const p = seg(lt, 4.15, 4.8);
      paint(ellPts(PLANT_X, G + 6, 18 + 75 * p, 6 + 20 * p, 24, 1),
        { wash: '#F7D78E', washOp: 115 * (1 - p), ink: null });
    }
    camEnd();
  }

  function shotBloom(t, lt, dur) {
    const settle = ease(seg(lt, 0, 1.3));
    camBegin(lerp(1085, 1050 + 18 * Math.sin(lt * .45), settle),
      lerp(540 - 12 * Math.sin(5 * .7), 535 - 25 * ease(seg(lt, 2.0, 5.0)), settle),
      lerp(1.145, 1.17 + .08 * ease(seg(lt, 0, dur)), settle));
    forest(t, ease(seg(t, 10, 13.5)));
    flower(t);
    const joy = ease(seg(t, 12.5, 13.3));
    const hop = joy * 2.1 * Math.sin(Math.PI * seg(t, 13.0, 14.0)) ** 2;
    rabbit(lerp(1038, 970, settle), G, lerp(32, 33, settle), t,
      { mood: t < 10.4 ? 'happy' : t < 12.5 ? 'surprised' : 'happy',
        look: .65 * settle, reach: lerp(1, .2 + .65 * joy, settle),
        lean: .14 * (1 - settle), hop, earKick: 12.5 });
    camEnd();
  }

  const drawById = { A: shotFall, B: shotPlant, C: shotBloom };
  shots(SHOT_PLAN.shots.map(shot => {
    if (!drawById[shot.id]) throw new Error(`No drawing function for shot ${shot.id}`);
    return [shot.start_frame / SHOT_PLAN.fps, drawById[shot.id]];
  }));
})();
