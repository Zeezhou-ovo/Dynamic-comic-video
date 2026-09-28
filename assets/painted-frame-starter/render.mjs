import { chromium } from 'playwright';
import ffmpegInstaller from '@ffmpeg-installer/ffmpeg';
import { spawn } from 'node:child_process';
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { pathToFileURL } from 'node:url';

const args = Object.fromEntries(process.argv.slice(2).map(part => {
  const [key, ...rest] = part.replace(/^--/, '').split('=');
  return [key, rest.length ? rest.join('=') : true];
}));

if (!args.frames && !args.stills && !args.encode) {
  console.log('Use --stills=0,2,4, --frames, or --encode [--audio=assets/audio.wav]');
  process.exit(0);
}

const browser = await chromium.launch({
  headless: true,
  ...(args.chrome || process.env.CHROME_PATH ? { executablePath: args.chrome || process.env.CHROME_PATH } : {}),
  args: ['--allow-file-access-from-files'],
});

async function openPage() {
  const page = await browser.newPage();
  page.on('pageerror', error => console.error('PAGE ERROR:', error.message));
  await page.goto(pathToFileURL(resolve('studio.html')).href, { waitUntil: 'load' });
  await page.waitForFunction(() => window.ready === true, { timeout: 30000 });
  return page;
}

const firstPage = await openPage();
const config = await firstPage.evaluate(() => window.videoConfig);
const fps = Number(args.fps || config.fps);
const count = Math.ceil(config.duration * fps);
const frameName = i => `out/frames/f${String(i).padStart(5, '0')}.png`;

async function capture(page, t) {
  const dataUrl = await page.evaluate(time => window.renderAt(time), t);
  return Buffer.from(dataUrl.slice(dataUrl.indexOf(',') + 1), 'base64');
}

if (args.stills) {
  mkdirSync('out/stills', { recursive: true });
  for (const value of String(args.stills).split(',')) {
    const t = Number(value);
    if (!Number.isFinite(t) || t < 0 || t > config.duration) throw new Error(`Invalid still time: ${value}`);
    writeFileSync(`out/stills/t${value.replace('.', '_')}.png`, await capture(firstPage, t));
  }
} else if (args.frames) {
  mkdirSync('out/frames', { recursive: true });
  const workerCount = Math.max(1, Number(args.workers || 2));
  let next = 0, finished = 0;
  const workers = await Promise.all(Array.from({ length: workerCount }, (_, index) => index === 0 ? firstPage : openPage()));
  await Promise.all(workers.map(async page => {
    while (next < count) {
      const i = next++;
      writeFileSync(frameName(i), await capture(page, i / fps));
      if (++finished % fps === 0 || finished === count) console.log(`${finished}/${count} frames`);
    }
  }));
  for (const page of workers) await page.close();
} else if (args.encode) {
  const missing = [];
  for (let i = 0; i < count; i++) if (!existsSync(frameName(i))) missing.push(i);
  if (missing.length) throw new Error(`${missing.length} frames missing; render --frames first`);
  const out = String(args.out || 'out/video.mp4');
  mkdirSync(dirname(out), { recursive: true });
  const cmd = ['-y', '-loglevel', 'error', '-framerate', String(fps), '-i', 'out/frames/f%05d.png'];
  if (args.audio) cmd.push('-i', String(args.audio));
  cmd.push('-map', '0:v');
  if (args.audio) cmd.push('-map', '1:a');
  cmd.push('-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p');
  if (args.audio) cmd.push('-c:a', 'aac', '-b:a', '192k');
  cmd.push('-t', String(config.duration), '-movflags', '+faststart', out);
  await new Promise((resolveRun, rejectRun) => {
    const process = spawn(ffmpegInstaller.path, cmd, { stdio: 'inherit' });
    process.on('error', rejectRun);
    process.on('close', code => code === 0 ? resolveRun() : rejectRun(new Error(`FFmpeg exited ${code}`)));
  });
  console.log(`Wrote ${out}`);
}

await firstPage.close().catch(() => {});
await browser.close();
