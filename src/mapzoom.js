/* Pan and zoom for the SVG choropleths, shared by every page that draws one.
 *
 * Wraps whatever is already inside the <svg> in a transform group, so the
 * projection code above it never has to know this exists. Strokes are marked
 * non-scaling: at ×8 a scaled 0.25px township border would read as a fat black
 * line and swallow the fill it is supposed to separate.
 *
 * Wheel behaviour is cooperative by default: a plain wheel scrolls the page and
 * shows a hint, ⌘/Ctrl + wheel zooms. A 1000px-tall map sitting in the middle of
 * a long page would otherwise trap the scroll every time the pointer crossed it.
 * The 滾輪 toggle in the corner switches plain wheel to zoom for anyone who
 * wants it; the choice is remembered per page for the session.
 */
function enableMapZoom(svg, opts = {}) {
  const NS = 'http://www.w3.org/2000/svg';
  const MAX = opts.max || 12;
  const KEY = 'mapzoom-wheel';
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;

  const vb = svg.viewBox.baseVal;
  const W = vb.width || 990, H = vb.height || 1000;

  const g = document.createElementNS(NS, 'g');
  while (svg.firstChild) g.appendChild(svg.firstChild);
  svg.appendChild(g);
  svg.classList.add('zoomable');

  let k = 1, tx = 0, ty = 0;

  // Keep the drawing covering the frame: at k the content is W*k wide, so the
  // offset may run from -(k-1)*W to 0 before sea would show at an edge.
  const clamp = () => {
    tx = Math.min(0, Math.max(-(k - 1) * W, tx));
    ty = Math.min(0, Math.max(-(k - 1) * H, ty));
  };
  const apply = () => {
    clamp();
    g.setAttribute('transform', `translate(${tx.toFixed(2)} ${ty.toFixed(2)}) scale(${k.toFixed(4)})`);
    svg.classList.toggle('zoomed', k > 1.001);
    if (out) out.textContent = `×${k.toFixed(1)}`;
    if (reset) reset.disabled = k <= 1.001;
  };

  /** Client coordinates → viewBox coordinates, before the transform. */
  const toLocal = (cx, cy) => {
    const r = svg.getBoundingClientRect();
    return [(cx - r.left) / r.width * W, (cy - r.top) / r.height * H];
  };

  /** Scale by `f` while holding the point under (cx, cy) still. */
  function zoomAt(cx, cy, f) {
    const [px, py] = toLocal(cx, cy);
    const next = Math.min(MAX, Math.max(1, k * f));
    if (next === k) return;
    tx = px - (px - tx) * (next / k);
    ty = py - (py - ty) * (next / k);
    k = next;
    apply();
  }
  function zoomCentre(f) {
    const r = svg.getBoundingClientRect();
    zoomAt(r.left + r.width / 2, r.top + r.height / 2, f);
  }
  function reset0() { k = 1; tx = 0; ty = 0; apply(); }

  /* ── controls ─────────────────────────────────────────────────────────── */
  // The svg may or may not sit in a positioned wrapper; give it one either way
  // so the overlay has something to anchor to.
  let host = svg.parentElement;
  if (!host.classList.contains('mapwrap')) {
    const w = document.createElement('div');
    w.className = 'mapwrap';
    svg.replaceWith(w);
    w.appendChild(svg);
    host = w;
  }
  const bar = document.createElement('div');
  bar.className = 'zoomctl';
  bar.innerHTML =
    '<button type="button" data-a="in"  title="放大" aria-label="放大">+</button>' +
    '<button type="button" data-a="out" title="縮小" aria-label="縮小">−</button>' +
    '<button type="button" data-a="reset" title="重設" aria-label="重設縮放">重設</button>' +
    '<span class="lvl" aria-live="polite">×1.0</span>' +
    '<button type="button" data-a="wheel" class="wheel" aria-pressed="false"' +
    ' title="開啟後，直接滾動滑鼠滾輪即可縮放">滾輪</button>';
  host.appendChild(bar);
  const out = bar.querySelector('.lvl');
  const reset = bar.querySelector('[data-a="reset"]');
  const wheelBtn = bar.querySelector('[data-a="wheel"]');

  let wheelZoom = sessionStorage.getItem(KEY) === '1';
  const setWheel = on => {
    wheelZoom = on;
    wheelBtn.setAttribute('aria-pressed', String(on));
    try { sessionStorage.setItem(KEY, on ? '1' : '0'); } catch { /* private mode */ }
  };
  setWheel(wheelZoom);

  bar.addEventListener('click', e => {
    const b = e.target.closest('button');
    if (!b) return;
    e.stopPropagation();
    ({ in: () => zoomCentre(1.5), out: () => zoomCentre(1 / 1.5),
       reset: reset0, wheel: () => setWheel(!wheelZoom) })[b.dataset.a]();
  });

  const hint = document.createElement('div');
  hint.className = 'zoomhint';
  hint.textContent = navigator.platform.includes('Mac')
    ? '⌘ ＋ 滾輪可縮放，或按右上角「滾輪」' : 'Ctrl ＋ 滾輪可縮放，或按右上角「滾輪」';
  host.appendChild(hint);
  let hintTimer = 0;
  const showHint = () => {
    hint.classList.add('on');
    clearTimeout(hintTimer);
    hintTimer = setTimeout(() => hint.classList.remove('on'), 1400);
  };

  /* ── wheel ────────────────────────────────────────────────────────────── */
  svg.addEventListener('wheel', e => {
    if (!(e.ctrlKey || e.metaKey || wheelZoom)) { showHint(); return; }
    e.preventDefault();
    // deltaMode 1 is lines, 2 is pages; normalise so a trackpad and a notched
    // wheel move by comparable amounts.
    const px = e.deltaY * (e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? 100 : 1);
    zoomAt(e.clientX, e.clientY, Math.exp(-px * 0.0022));
  }, { passive: false });

  /* ── drag to pan, pinch to zoom ───────────────────────────────────────── */
  const pts = new Map();
  let last = null, pinch = 0, moved = 0;

  svg.addEventListener('pointerdown', e => {
    if (e.button != null && e.button !== 0) return;
    pts.set(e.pointerId, e);
    moved = 0;
    if (pts.size === 1) { last = e; }
    if (pts.size === 2) {
      const [a, b] = [...pts.values()];
      pinch = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
    }
  });

  svg.addEventListener('pointermove', e => {
    if (!pts.has(e.pointerId)) return;
    pts.set(e.pointerId, e);
    if (pts.size === 2) {
      const [a, b] = [...pts.values()];
      const d = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
      if (pinch) zoomAt((a.clientX + b.clientX) / 2, (a.clientY + b.clientY) / 2, d / pinch);
      pinch = d;
      e.preventDefault();
      return;
    }
    if (k <= 1.001 || !last) return;          // nothing to pan at full extent
    const r = svg.getBoundingClientRect();
    const dx = (e.clientX - last.clientX) / r.width * W;
    const dy = (e.clientY - last.clientY) / r.height * H;
    moved += Math.abs(e.clientX - last.clientX) + Math.abs(e.clientY - last.clientY);
    tx += dx; ty += dy; last = e;
    svg.setPointerCapture?.(e.pointerId);
    apply();
  });

  const end = e => {
    pts.delete(e.pointerId);
    if (pts.size < 2) pinch = 0;
    if (pts.size === 0) last = null;
  };
  svg.addEventListener('pointerup', end);
  svg.addEventListener('pointercancel', end);
  svg.addEventListener('lostpointercapture', end);

  // A drag that ends on a polygon must not also count as selecting it.
  svg.addEventListener('click', e => {
    if (moved > 6) { e.stopPropagation(); e.preventDefault(); moved = 0; }
  }, true);

  svg.addEventListener('dblclick', e => {
    e.preventDefault();
    zoomAt(e.clientX, e.clientY, e.shiftKey ? 1 / 2 : 2);
  });

  /* ── keyboard ─────────────────────────────────────────────────────────── */
  svg.setAttribute('tabindex', svg.getAttribute('tabindex') ?? '0');
  svg.addEventListener('keydown', e => {
    const step = 60 / k;
    const act = {
      '+': () => zoomCentre(1.5), '=': () => zoomCentre(1.5),
      '-': () => zoomCentre(1 / 1.5), '_': () => zoomCentre(1 / 1.5),
      '0': reset0, Escape: reset0,
      ArrowLeft: () => { tx += step; apply(); }, ArrowRight: () => { tx -= step; apply(); },
      ArrowUp: () => { ty += step; apply(); }, ArrowDown: () => { ty -= step; apply(); },
    }[e.key];
    if (!act) return;
    e.preventDefault();
    act();
  });

  apply();
  return { reset: reset0, zoomCentre };
}
