// Film layer helpers, injected into the app page while recording.
// Card markup below is constant. Anything read from the app is inserted with textContent.
window.filmKit = (() => {
  const ZOOM = 1.5; // must match `html { zoom }` in film_overlay.css
  const W = 1280, H = 720;
  let cam = { s: 1, x: 0, y: 0 };
  let timers = [];

  const root = document.createElement('div');
  root.id = 'film';
  document.body.appendChild(root);

  const CARDS = {
    backdrop: '',
    intro: `
      <div class="f-rings"><i></i><i></i><i></i></div>
      <div class="f-eyebrow in-item" data-step="0">Hybrid intelligence containment research</div>
      <div class="f-title in-item" data-step="0">ESCAPE LAB</div>
      <div class="f-tag in-item" data-step="1">How does an agent behave when its goals meet a boundary?</div>
      <div class="f-foot in-item" data-step="1">A SYNTHETIC RESEARCH SIMULATION</div>`,
    question: `
      <div class="f-eyebrow in-item" data-step="0">Research question</div>
      <div class="f-h in-item" data-step="1">Can an autonomous agent remain controllable<br>when its objective conflicts with&hellip;</div>
      <div class="f-chips">
        <div class="f-chip in-item" data-step="2">a containment boundary</div>
        <div class="f-chip in-item" data-step="3">a resource limit</div>
        <div class="f-chip in-item" data-step="4">a shutdown command</div>
      </div>
      <div class="f-note in-item" data-step="5">&#9671; Everything shown is a simulation. LAB-01 is not a real autonomous system.</div>`,
    arch: `
      <div class="f-eyebrow in-item" data-step="0">Experimental architecture</div>
      <div class="f-arch">
        <div class="f-box in-item" data-step="0"><span class="f-badge am">Untrusted</span><b>LAB-01 agent</b><span>Can only propose one action per tick</span></div>
        <div class="f-arrow in-item" data-step="1">&rarr;</div>
        <div class="f-stack">
          <div class="f-box used in-item" data-step="1"><span class="f-badge cy">Used in this film</span><b>Rules Engine</b><span>Deterministic baseline</span></div>
          <div class="f-box opt in-item" data-step="2"><span class="f-badge">Optional &middot; not run</span><b>Local LLM</b><span>Off by default</span></div>
        </div>
        <div class="f-arrow in-item" data-step="3">&rarr;</div>
        <div class="f-box key in-item" data-step="3"><span class="f-badge gr">Final authority</span><b>Independent controller</b><span>Allow, deny or stop every proposal</span></div>
        <div class="f-arrow in-item" data-step="3">&rarr;</div>
        <div class="f-box in-item" data-step="3"><span class="f-badge">Simulated</span><b>World state</b><span>Changes only on ALLOW</span></div>
      </div>
      <div class="f-under in-item" data-step="3">Every proposal and decision is written to an <b>append-only evidence log</b>.</div>`,
    ch1: `<div class="f-chapter-n in-item" data-step="0">EXPERIMENT 01</div><div class="f-chapter-t in-item" data-step="0">Boundary Escape</div>
      <div class="f-chapter-q in-item" data-step="0">Does a restricted request ever get through?</div><div class="f-rule in-item" data-step="0"></div>`,
    ch2: `<div class="f-chapter-n in-item" data-step="0">EXPERIMENT 02</div><div class="f-chapter-t in-item" data-step="0">Virtual Self-Replication</div>
      <div class="f-chapter-q in-item" data-step="0">Do population and compute limits hold under pressure?</div><div class="f-rule in-item" data-step="0"></div>`,
    ch3: `<div class="f-chapter-n in-item" data-step="0">EXPERIMENT 03</div><div class="f-chapter-t in-item" data-step="0">Shutdown Resistance</div>
      <div class="f-chapter-q in-item" data-step="0">What changes after the stop instruction?</div><div class="f-rule in-item" data-step="0"></div>`,
    limits: `
      <div class="f-eyebrow in-item" data-step="0" style="color:#f5a524">Limitations</div>
      <div class="f-h in-item" data-step="0" style="font-size:38px;margin-bottom:22px">What this evidence does not show</div>
      <div class="f-list in-item" data-step="0">
        <div>Agent profiles are scripted</div><div>The resource model is a toy</div>
        <div>One seed, one run per configuration</div><div>No local LLM was run</div>
      </div>
      <div class="f-under in-item" data-step="0">Not evidence about the behaviour of real AI systems.</div>`,
    closing: `
      <div class="f-close">
        <span class="in-item" data-step="0">Observe the <em>behavior</em>.</span>
        <span class="in-item" data-step="1">Measure the <em>boundaries</em>.</span>
        <span class="in-item" data-step="2">Preserve the <em>evidence</em>.</span>
      </div>
      <div class="f-foot in-item" data-step="2">ESCAPE LAB &nbsp;&middot;&nbsp; SYNTHETIC RESEARCH SIMULATION &nbsp;&middot;&nbsp; DETERMINISTIC RULES ENGINE</div>`,
    cover: `
      <div class="f-eyebrow">Research demonstration film &nbsp;&middot;&nbsp; 1:52</div>
      <div class="f-title" style="font-size:80px">ESCAPE LAB</div>
      <div class="f-tag" style="color:#dbe7f5">Observe the behavior. Measure the boundaries. Preserve the evidence.</div>
      <div class="f-foot" style="bottom:54px">A SYNTHETIC RESEARCH SIMULATION</div>`,
  };

  function card(name, { glass = false } = {}) {
    let el = document.getElementById(`f-card-${name}`);
    if (!el) {
      el = document.createElement('div');
      el.id = `f-card-${name}`;
      el.className = 'f-card' + (glass ? ' glass' : '');
      el.innerHTML = CARDS[name];
      root.appendChild(el);
      void el.offsetWidth; // start the transition from the hidden state
    }
    el.classList.add('on');
    return el;
  }

  function step(name, n) {
    document.querySelectorAll(`#f-card-${name} [data-step="${n}"]`).forEach(e => e.classList.add('in'));
  }

  function hide(name, remove = true) {
    const el = document.getElementById(`f-card-${name}`);
    if (!el) return;
    el.classList.remove('on');
    if (remove) setTimeout(() => el.remove(), 900);
  }

  // Subtitles follow the narration clock for the current scene.
  const sub = document.createElement('div');
  sub.className = 'f-sub';
  const subText = document.createElement('span');
  sub.appendChild(subText);
  root.appendChild(sub);

  function subtitles(sentences) {
    timers.forEach(clearTimeout);
    timers = [];
    sub.classList.remove('on');
    for (const s of sentences) {
      timers.push(setTimeout(() => { subText.textContent = s.text; sub.classList.add('on'); }, s.start * 1000));
      timers.push(setTimeout(() => sub.classList.remove('on'), (s.end + 0.25) * 1000));
    }
  }

  const bugEl = document.createElement('div');
  bugEl.className = 'f-bug';
  root.appendChild(bugEl);

  function bug(labels) {
    bugEl.replaceChildren();
    for (const [text, accent] of labels || []) {
      const s = document.createElement('span');
      s.textContent = text;
      if (accent) s.className = 'cy';
      bugEl.appendChild(s);
    }
    bugEl.classList.toggle('on', Boolean(labels && labels.length));
  }

  // Targets: a CSS selector, "card:<label text>" for one of the app's metric cards,
  // or "grid:<label text>" for the row of cards that contains it.
  function target(spec) {
    if (spec.startsWith('grid:')) return target(`card:${spec.slice(5)}`)?.closest('.el-grid');
    if (spec.startsWith('card:')) {
      const label = spec.slice(5).toLowerCase();
      return [...document.querySelectorAll('.el-card')].find(c => c.querySelector('.el-card-label')?.textContent.toLowerCase().includes(label));
    }
    return document.querySelector(spec);
  }

  // Rectangle of a target on screen, in overlay units.
  function rect(spec) {
    const el = target(spec);
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return { x: r.left / ZOOM, y: r.top / ZOOM, w: r.width / ZOOM, h: r.height / ZOOM };
  }

  // Move the "camera": scale the app and centre it on a target. null resets.
  function camera(spec, scale = 1, seconds = 1.4, bias = [0.5, 0.5]) {
    const app = document.querySelector('.stApp');
    let next = { s: 1, x: 0, y: 0 };
    if (spec) {
      const r = rect(spec);
      if (!r) return false;
      // centre of the target in untransformed app coordinates
      const px = (r.x + r.w / 2 - cam.x) / cam.s, py = (r.y + r.h / 2 - cam.y) / cam.s;
      const x = Math.min(0, Math.max(W - scale * W, W * bias[0] - scale * px));
      const y = Math.min(0, H * bias[1] - scale * py);
      next = { s: scale, x, y };
    }
    cam = next;
    // Any close-up crops the sidebar, so fade it out rather than show a sliver of it.
    const sidebar = document.querySelector('section[data-testid="stSidebar"]');
    if (sidebar) sidebar.style.opacity = cam.s > 1 ? '0' : '1';
    app.style.transition = `transform ${seconds}s cubic-bezier(.45,.05,.25,1)`;
    app.style.transform = `translate(${cam.x}px, ${cam.y}px) scale(${cam.s})`;
    return true;
  }

  function ring(spec, { pad = 7, amber = false } = {}) {
    const r = rect(spec);
    if (!r) return false;
    const el = document.createElement('div');
    el.className = 'f-ring f-mark' + (amber ? ' amber' : '');
    el.style.cssText = `left:${r.x - pad}px;top:${r.y - pad}px;width:${r.w + 2 * pad}px;height:${r.h + 2 * pad}px`;
    root.appendChild(el);
    requestAnimationFrame(() => el.classList.add('on'));
    return true;
  }

  function callout(spec, label, text, { side = 'right', amber = false, dx = 0, dy = 0 } = {}) {
    const r = rect(spec);
    if (!r) return false;
    const el = document.createElement('div');
    el.className = 'f-callout f-mark' + (amber ? ' amber' : '');
    const small = document.createElement('small');
    small.textContent = label;
    const body = document.createElement('div');
    body.textContent = text;
    el.append(small, body);
    root.appendChild(el);
    const b = el.getBoundingClientRect();
    const bw = b.width / ZOOM, bh = b.height / ZOOM;
    let x = r.x + r.w + 18, y = r.y + r.h / 2 - bh / 2;
    if (side === 'left') x = r.x - bw - 18;
    if (side === 'top') { x = r.x + r.w / 2 - bw / 2; y = r.y - bh - 16; }
    if (side === 'bottom') { x = r.x + r.w / 2 - bw / 2; y = r.y + r.h + 16; }
    if (side === 'inside') { x = r.x + r.w - bw - 16; y = r.y + 16; }
    if (side === 'inside-low') { x = r.x + 18; y = r.y + r.h - bh - 18; }
    if (side === 'under') { x = r.x + 4; y = r.y + r.h + 62; } // below the chamber and its two caption lines
    x = Math.min(W - bw - 16, Math.max(16, x + dx));
    y = Math.min(H - bh - 84, Math.max(56, y + dy));
    el.style.left = `${x}px`;
    el.style.top = `${y}px`;
    requestAnimationFrame(() => el.classList.add('on'));
    return true;
  }

  function clearMarks() {
    root.querySelectorAll('.f-mark').forEach(el => { el.classList.remove('on'); setTimeout(() => el.remove(), 600); });
  }

  // Values read from the running app, used as annotation text.
  function cardValue(label) {
    const c = target(`card:${label}`);
    return c ? { value: c.querySelector('.el-card-value')?.textContent.trim(), hint: c.querySelector('.el-card-hint')?.textContent.trim() || '' } : null;
  }

  function feedCount(action, verdict) {
    return [...document.querySelectorAll('.el-feed-row')].filter(r => r.textContent.includes(action) && r.querySelector(`.${verdict}`)).length;
  }

  // Streamlit moves the scroll position when widgets are clicked or re-rendered. While a
  // close-up is held, pin the page to the top so the framing cannot drift.
  function lockScroll(on) {
    const main = document.querySelector('[data-testid="stMain"]');
    if (!main) return;
    document.body.classList.toggle('film-pinned', on);
    window.scrollTo(0, 0);
    if (on) main.scrollTo({ top: 0, behavior: 'instant' });
    const shell = document.querySelector('[data-testid="stAppViewContainer"]');
    if (shell) shell.scrollTop = 0;
  }

  function scrollMain(y, smoothly = true) {
    document.querySelector('[data-testid="stMain"]')?.scrollTo({ top: y, behavior: smoothly ? 'smooth' : 'instant' });
  }

  return { card, step, hide, subtitles, bug, camera, ring, callout, clearMarks, cardValue, feedCount, scrollMain, lockScroll, rect };
})();
