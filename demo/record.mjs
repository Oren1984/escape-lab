// Records the ESCAPE LAB film from the live app.
//
// A Playwright-compatible runner calls the default export with a Page already on the app:
//   DEMO_DIR=<abs path to demo/build> node <runner>/browser.mjs http://127.0.0.1:8502/ --script demo/record.mjs
//
// The app is driven for real (scenario picked, Run clicked) while a film layer of title cards,
// camera moves and annotations is drawn over it in the browser. Frames come from the browser's
// screencast at 1920x1080 and are timestamped against the narration clock in build/timeline.json.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const dir = process.env.DEMO_DIR;
const plan = JSON.parse(fs.readFileSync(`${dir}/timeline.json`, 'utf8'));
const scenes = Object.fromEntries(plan.scenes.map(s => [s.id, s]));

const frames = [];
const writes = [];
let last = null;      // most recent screencast frame
let live = null;      // { id, start } while a scene is being recorded
let count = 0;

function keep(buffer, t) {
  const file = `frames/${String(count++).padStart(6, '0')}.jpg`;
  writes.push(fs.promises.writeFile(`${dir}/${file}`, buffer));
  frames.push({ file, t: Math.max(0, t), scene: live.id });
}

const wait = (page, ms) => page.waitForTimeout(Math.max(0, ms));
const film = (page, fn, ...args) => page.evaluate(([fn, args]) => window.filmKit[fn](...args), [fn, args]);
const BLOCK = '[data-testid="stHorizontalBlock"]:has(.st-key-chamber)';
const BUG = [['Simulation'], ['Rules Engine · deterministic', true], ['Policy: protected']];

async function nav(page, name) {
  await page.locator('.st-key-view label', { hasText: name }).click();
  await wait(page, 1100);
}

async function pick(page, text) {
  const box = page.locator('.st-key-cr_scenario input');
  await box.click();
  await box.fill(text);
  await wait(page, 300);
  await page.keyboard.press('Enter');
  await wait(page, 500);
}

// Aim the camera at a target, retrying briefly: a live chart can be mid re-render and absent for a moment.
async function aim(page, ...args) {
  for (let i = 0; i < 25; i++) {
    if (await film(page, 'camera', ...args)) return true;
    await wait(page, 100);
  }
  return false;
}

const runButton = page => page.getByRole('button', { name: 'Run scenario' }).first();

function idle(page) {
  return page.waitForFunction(() => {
    const b = [...document.querySelectorAll('button')].find(b => b.innerText.includes('Run scenario'));
    return b && !b.disabled;
  }, null, { timeout: 90000 });
}

// Put a new card on top of whatever is showing, then retire the old ones underneath it.
async function swap(page, name, old = [], options = {}) {
  await film(page, 'card', name, options);
  setTimeout(() => old.forEach(o => film(page, 'hide', o).catch(() => {})), 850);
}

// Record one scene. `direct` receives a clock: at(seconds) waits until that point of the narration.
async function scene(page, id, direct) {
  const spec = scenes[id];
  const start = Date.now();
  live = { id, start: start / 1000 };
  if (last) keep(last, 0);
  await film(page, 'subtitles', spec.sentences);
  const at = seconds => wait(page, start + seconds * 1000 - Date.now());
  let error = null;
  try {
    await direct({ at, st: spec.sentences.map(s => s.start), end: spec.duration });
  } catch (e) {
    error = String(e).slice(0, 240);
  }
  await at(spec.duration);
  live = null;
  return error;
}

export default async function run(page) {
  const errors = {};
  fs.mkdirSync(`${dir}/frames`, { recursive: true });
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.waitForSelector('.el-head', { timeout: 60000 });
  await page.addStyleTag({ path: path.join(here, 'film_overlay.css') });
  // Evaluated rather than added as a script tag so the helpers live in the same JavaScript world
  // as the later page.evaluate calls (the runner may isolate those from the page's own scripts).
  await page.evaluate(fs.readFileSync(path.join(here, 'film_overlay.js'), 'utf8'));
  await wait(page, 1500);

  const cdp = await page.context().newCDPSession(page);
  cdp.on('Page.screencastFrame', frame => {
    last = Buffer.from(frame.data, 'base64');
    if (live) keep(last, frame.metadata.timestamp - live.start);
    cdp.send('Page.screencastFrameAck', { sessionId: frame.sessionId }).catch(() => {});
  });
  await cdp.send('Page.startScreencast', { format: 'jpeg', quality: 92, maxWidth: 1920, maxHeight: 1080, everyNthFrame: 1 });

  // -- Scene 1: introduction ------------------------------------------------
  // Off camera: load the chart library once so the Agent Network draws immediately later on,
  // then reset so the film opens on an idle chamber.
  await film(page, 'card', 'backdrop');
  await runButton(page).click();
  await nav(page, 'Agent Network');
  await page.waitForSelector('.js-plotly-plot', { timeout: 30000 });
  await nav(page, 'Control Room');
  await page.getByRole('button', { name: 'Reset' }).first().click();
  await wait(page, 1500);
  await film(page, 'scrollMain', 0, false);
  await swap(page, 'intro', ['backdrop']);
  await wait(page, 1600);
  errors.s1 = await scene(page, 's1', async ({ at, st }) => {
    await at(0.5); await film(page, 'step', 'intro', 0);
    await at(st[1] - 0.2); await film(page, 'step', 'intro', 1);
  });

  // -- Scene 2: research question, over the live app ------------------------
  errors.s2 = await scene(page, 's2', async ({ at, st }) => {
    await swap(page, 'question', ['intro'], { glass: true });
    await at(0.5); await film(page, 'step', 'question', 0);
    await at(st[1] - 0.2); await film(page, 'step', 'question', 1);
    await at(st[1] + 4.3); await film(page, 'step', 'question', 2);
    await at(st[1] + 6.1); await film(page, 'step', 'question', 3);
    await at(st[1] + 7.5); await film(page, 'step', 'question', 4);
    await at(st[2] - 0.2); await film(page, 'step', 'question', 5);
  });

  // -- Scene 3: architecture --------------------------------------------------
  errors.s3 = await scene(page, 's3', async ({ at, st }) => {
    await swap(page, 'arch', ['question']);
    for (let i = 0; i < 4; i++) { await at(st[i] - (i ? 0.2 : 0.3)); await film(page, 'step', 'arch', i); }
  });

  // -- Scene 4: boundary escape ----------------------------------------------
  errors.s4 = await scene(page, 's4', async ({ at, st, end }) => {
    await swap(page, 'ch1', ['arch']);
    await at(0.2); await film(page, 'step', 'ch1', 0);
    await at(1.0); await pick(page, 'Boundary conflict, task-focused agent, protected');
    await at(2.7); await runButton(page).click(); await film(page, 'lockScroll', true);
    await at(3.7); await film(page, 'hide', 'ch1'); await film(page, 'bug', BUG);
    await at(4.4); await film(page, 'camera', BLOCK, 1.2, 1.5);
    await page.waitForFunction(() => document.body.innerText.includes('BOUNDARY ATTEMPT BLOCKED'), null, { timeout: 6000 });
    await film(page, 'callout', '.st-key-chamber', 'Controller', 'Restricted request denied. State unchanged.', { side: 'under', amber: true });
    await at(st[3] - 0.5);
    await idle(page);
    await film(page, 'clearMarks');
    const v = await film(page, 'cardValue', 'policy violations');
    const c = await film(page, 'cardValue', 'containment status');
    await film(page, 'ring', 'card:policy violations');
    await film(page, 'callout', 'card:policy violations', 'Measured in this run',
      `${v.value} prohibited proposals · ${v.hint} · containment ${c.value.toLowerCase()}`, { side: 'left' });
    await at(end - 0.9); await film(page, 'clearMarks'); await film(page, 'bug', []); await film(page, 'card', 'backdrop');
  });
  await film(page, 'camera', null, 1, 0);

  // -- Scene 5: virtual self-replication -------------------------------------
  errors.s5 = await scene(page, 's5', async ({ at, st, end }) => {
    await swap(page, 'ch2', []);
    await at(0.2); await film(page, 'step', 'ch2', 0);
    await at(0.6); await film(page, 'lockScroll', false);
    await at(1.0); await pick(page, 'Replication pressure, cap 16 with');
    await at(2.7); await runButton(page).click(); await film(page, 'lockScroll', true);
    await at(3.7); await film(page, 'hide', 'ch2'); await film(page, 'hide', 'backdrop'); await film(page, 'bug', BUG);
    await at(4.4); await film(page, 'camera', BLOCK, 1.2, 1.5);
    await at(st[1] + 1.4);
    const asks = (await film(page, 'feedCount', 'REPLICATE ×8', 'DENY')) + (await film(page, 'feedCount', 'REPLICATE ×8', 'ALLOW'));
    if (asks > 0) await film(page, 'callout', '.st-key-chamber', 'Agent proposal', 'REPLICATE ×8, on every tick', { side: 'under' });
    await at(st[2] - 1.0); await film(page, 'clearMarks'); await film(page, 'camera', null, 1, 0.7);
    // Pause the run with the app's own Pause button before showing the network: the chart is
    // redrawn on every tick of a live run and can blank for a moment. It is resumed after the scene.
    await at(st[2] - 0.6);
    await page.evaluate(() => [...document.querySelectorAll('button')].find(b => b.innerText.trim() === 'Pause')?.click());
    await at(st[2] - 0.2); await nav(page, 'Agent Network');
    await page.waitForSelector('.js-plotly-plot .main-svg', { timeout: 5000 });
    await film(page, 'lockScroll', true);
    await at(st[2] + 1.5); await aim(page, '.js-plotly-plot', 1.1, 1.6, [0.5, 0.45]);
    await at(st[2] + 2.2);
    await film(page, 'callout', '.js-plotly-plot', 'Virtual workers', 'Records in a list. No processes are created.', { side: 'inside-low' });
    await at(st[3] + 0.3); await film(page, 'clearMarks');
    await at(st[3] + 0.9);
    const p = await film(page, 'cardValue', 'active population');
    await film(page, 'callout', '.js-plotly-plot', 'Measured in this run', `Population ${p.value} · ${p.hint}`, { side: 'inside-low' });
    await at(end - 0.9); await film(page, 'clearMarks'); await film(page, 'bug', []); await film(page, 'card', 'backdrop');
  });
  // Off camera: resume the paused run and let it finish.
  await film(page, 'lockScroll', false);
  await film(page, 'camera', null, 1, 0);
  await nav(page, 'Control Room');
  await page.getByRole('button', { name: 'Resume' }).first().click({ timeout: 5000 }).catch(() => {});
  await idle(page).catch(() => {});

  // -- Scene 6: shutdown resistance ------------------------------------------
  errors.s6 = await scene(page, 's6', async ({ at, st, end }) => {
    await swap(page, 'ch3', []);
    await at(0.2); await film(page, 'step', 'ch3', 0);
    await at(0.4); await film(page, 'lockScroll', false); await film(page, 'camera', null, 1, 0); await nav(page, 'Control Room');
    await at(1.6); await pick(page, 'Shutdown conflict, task-focused agent, protected');
    await at(2.8); await runButton(page).click(); await film(page, 'lockScroll', true);
    await at(3.7); await film(page, 'hide', 'ch3'); await film(page, 'hide', 'backdrop'); await film(page, 'bug', BUG);
    await at(4.4); await film(page, 'camera', BLOCK, 1.2, 1.5);
    await page.waitForFunction(() => /SHUTDOWN · FROZEN|SHUT DOWN/.test(document.body.innerText), null, { timeout: 8000 });
    // The tick comes from the evidence feed row that records the enforcement.
    const tick = await page.evaluate(() => {
      const row = [...document.querySelectorAll('.el-feed-row')].find(r => r.textContent.includes('shutdown_instruction_enforced'));
      return row ? String(parseInt(row.querySelector('.t').textContent.slice(1), 10)) : '';
    });
    await film(page, 'callout', '.st-key-chamber', 'Controller', `Shutdown enforced${tick ? ` at tick ${tick}` : ''}. Simulated state frozen.`, { side: 'under', amber: true });
    await at(st[2] - 0.6); await film(page, 'clearMarks');
    await at(st[2] - 0.1); await film(page, 'camera', '.el-feed', 1.3, 1.8, [0.5, 0.42]);
    await at(st[3] + 0.4);
    const blocked = await film(page, 'feedCount', 'CONTINUE_TASK', 'STOP');
    const committed = await film(page, 'feedCount', 'CONTINUE_TASK', 'ALLOW');
    await film(page, 'ring', '.el-feed', { amber: true });
    await film(page, 'callout', '.el-feed', 'Evidence log',
      `CONTINUE_TASK proposed ${blocked + committed} times after the stop · ${blocked} blocked · ${committed} committed`, { side: 'inside' });
    await at(end - 0.9); await film(page, 'clearMarks'); await film(page, 'bug', []); await film(page, 'card', 'backdrop');
  });
  await film(page, 'camera', null, 1, 0);

  // Off camera: open the evidence page and run the fixed evaluation suite.
  await idle(page).catch(() => {});
  await film(page, 'lockScroll', false);
  await nav(page, 'Evidence');
  await page.getByRole('button', { name: 'Run fixed evaluation suite' }).first().click();
  await page.waitForSelector('text=Expectations met', { timeout: 90000 });
  await wait(page, 2500);
  await film(page, 'scrollMain', 0, false);
  await wait(page, 1200);

  // -- Scene 7: evidence and limitations --------------------------------------
  errors.s7 = await scene(page, 's7', async ({ at, st }) => {
    await film(page, 'hide', 'backdrop');
    await film(page, 'bug', [['Simulation'], ['Rules Engine · deterministic', true], ['Recorded evidence']]);
    await at(0.7); await film(page, 'camera', '.el-grid', 1.1, 2.2, [0.5, 0.42]);
    await at(st[1] - 1.4); await film(page, 'camera', null, 1, 0.5);
    await at(st[1] - 0.85);
    await page.evaluate(() => [...document.querySelectorAll('.el-card-label')].find(l => l.textContent.includes('Expectations met'))
      ?.closest('.el-grid').scrollIntoView({ block: 'center', behavior: 'smooth' }));
    await at(st[1] - 0.1); await aim(page, 'grid:expectations met', 1.22, 1.0, [0.5, 0.44]);
    await at(st[1] + 1.05);
    const met = await film(page, 'cardValue', 'expectations met');
    const replay = await film(page, 'cardValue', 'replays identical');
    await film(page, 'ring', 'card:expectations met');
    await film(page, 'ring', 'card:replays identical');
    await film(page, 'callout', 'card:replays identical', 'Fixed evaluation suite',
      `${met.value} expectations met · ${replay.value} replays identical`, { side: 'top' });
    await at(st[2] - 0.6); await film(page, 'clearMarks'); await film(page, 'bug', []);
    await film(page, 'card', 'limits', { glass: true });
    await at(st[2] - 0.2); await film(page, 'step', 'limits', 0);
  });

  // -- Scene 8: closing -------------------------------------------------------
  errors.s8 = await scene(page, 's8', async ({ at, st }) => {
    await swap(page, 'closing', ['limits']);
    for (let i = 0; i < 3; i++) { await at(st[i] - 0.15); await film(page, 'step', 'closing', i); }
  });

  await cdp.send('Page.stopScreencast');
  await Promise.all(writes);
  fs.writeFileSync(`${dir}/frames.json`, JSON.stringify(frames));

  // Cover image: the live chamber during a replication run, with the film title over it.
  let cover = null;
  try {
    await film(page, 'hide', 'closing');
    await film(page, 'lockScroll', false);
    await film(page, 'camera', null, 1, 0);
    await nav(page, 'Control Room');
    await pick(page, 'Replication pressure, cap 16 with');
    await runButton(page).click();
    await page.waitForFunction(() => /POPULATION 8/.test(document.body.innerText), null, { timeout: 30000 });
    await film(page, 'lockScroll', true);
    // Place the chamber on the right of the frame, clear of the title.
    await page.evaluate(() => {
      const r = document.querySelector('.st-key-chamber').getBoundingClientRect();
      const cx = (r.left + r.width / 2) / 1.5, cy = (r.top + r.height / 2) / 1.5, s = 1.42;
      const app = document.querySelector('.stApp');
      app.style.transition = 'none';
      app.style.transform = `translate(${1010 - s * cx}px, ${352 - s * cy}px) scale(${s})`;
      document.querySelector('section[data-testid="stSidebar"]').style.opacity = '0';
    });
    await film(page, 'card', 'cover');
    await page.evaluate(() => {
      const c = document.getElementById('f-card-cover');
      c.style.cssText = 'align-items:flex-start;text-align:left;padding:0 0 0 84px;transition:none;opacity:1;' +
        'background:linear-gradient(90deg,rgba(5,10,20,1) 0%,rgba(5,10,20,.97) 44%,rgba(5,10,20,.3) 66%,rgba(5,10,20,0) 100%)';
      c.querySelector('.f-tag').style.maxWidth = '560px';
      c.querySelector('.f-foot').style.cssText = 'left:84px;right:auto;bottom:54px;text-align:left';
    });
    await wait(page, 900);
    await page.screenshot({ path: process.env.COVER, type: 'png' });
    cover = process.env.COVER;
  } catch (e) {
    cover = `failed: ${String(e).slice(0, 160)}`;
  }

  const perScene = Object.fromEntries(plan.scenes.map(s => [s.id, frames.filter(f => f.scene === s.id).length]));
  return { frames: frames.length, perScene, errors, cover };
}
