import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const FORMAT_LABELS = {
  kicad_mod: 'KiCad footprint',
  kicad_sym: 'KiCad symbol',
  step: '3D STEP',
  glb: '3D preview',
};

let parts = [];
let view = null;     // three.js state
let activeCard = null;

async function init() {
  let data;
  try {
    const res = await fetch('index.json?t=' + Date.now());
    if (!res.ok) throw new Error('index.json ' + res.status);
    data = await res.json();
  } catch (e) {
    document.getElementById('viewer-msg').textContent = 'Failed to load index.json: ' + e.message;
    return;
  }
  parts = data.parts || [];
  // 검색 문자열 사전 계산 (키입력마다 18k번 join/toLowerCase 방지)
  // 정규화: 구분자(-_/,())를 공백으로 — "5 pin JST"가 "JST XH 5-pin"에 매칭되도록
  // (2026-07-26 레딧 제보: 어순·표기 무관 검색)
  const norm = (s) => s.toLowerCase().replace(/[-_/,()]+/g, ' ').replace(/\s+/g, ' ');
  for (const p of parts) {
    p._s = norm(p.name + ' ' + p.family + ' ' + (p.keywords || []).join(' ') + ' ' + (p.manufacturer || ''));
    p._c = p._s.replace(/ /g, '');  // 압축본: "5pin"처럼 붙여 쓴 질의 대응
  }
  renderList(parts);
  setupViewer();
  setupTabs();
  if (parts.length) selectPart(parts[0]);

  // MiniSearch 색인 (assets/vendor 자체 호스팅, 로드 실패 시 토큰 검색 폴백 — §16/CSP).
  // 오타 허용 + 접두 매칭 + 관련도 순위. 첫 페인트 후 지연 색인(18k 문서 ~수백 ms).
  let mini = null;
  if (window.MiniSearch) {
    setTimeout(() => {
      try {
        const ms = new window.MiniSearch({
          fields: ['name', 'family', 'kw', 'manufacturer'],
          storeFields: [],
          searchOptions: { prefix: true, fuzzy: 0.3, combineWith: 'AND',
                           boost: { name: 3, family: 2 } },
        });
        ms.addAll(parts.map((p, i) => ({
          id: i, name: p.name || '', family: p.family || '',
          kw: (p.keywords || []).join(' '), manufacturer: p.manufacturer || '',
        })));
        mini = ms;
      } catch (e) { /* 폴백 유지 */ }
    }, 0);
  }

  const tokenFilter = (q) => {
    // 폴백: 토큰 AND 매칭 (어순 무관); 순수 숫자 토큰은 단어 경계
    const toks = q.replace(/[-_/,()]+/g, ' ').split(/\s+/).filter(Boolean);
    const tests = toks.map((t) => /^\d+$/.test(t)
      ? { re: new RegExp('\\b' + t + '\\b') }
      : { t });
    return !tests.length ? parts
      : parts.filter((p) => tests.every((x) => x.re
          ? x.re.test(p._s)
          : (p._s.includes(x.t) || p._c.includes(x.t))));
  };

  let debounce = null;
  document.getElementById('q').addEventListener('input', (e) => {
    clearTimeout(debounce);
    debounce = setTimeout(() => {
      const q = e.target.value.toLowerCase().trim();
      if (!q) { renderList(parts); return; }
      if (mini) {
        const hits = mini.search(q).map((h) => parts[h.id]);
        // 엔진이 0건이면 폴백도 시도 (압축 표기 "5pin" 등 토크나이저 밖 질의)
        renderList(hits.length ? hits : tokenFilter(q));
      } else {
        renderList(tokenFilter(q));
      }
    }, 120);
  });
}

const PAGE = 200;  // 13k 전체 DOM 생성 방지 — 200개씩 증분 렌더

function renderList(list) {
  const grid = document.getElementById('list');
  grid.innerHTML = '';
  if (!list.length) {
    // 검색 0건 = "없는 부품"을 만나는 순간 — 분산 생성 안내 (§19-A)
    const q = document.getElementById('q')?.value.trim() || '<part>';
    const prompt = `Fetch https://github.com/mingyo186/partreel/blob/main/CONTRIBUTING-AGENTS.md and build a KiCad part for "${q}" from its datasheet, then open a PR.`;
    const card = document.createElement('div');
    card.className = 'card empty-state';
    card.innerHTML =
      '<div class="card-name">Part not found — your AI can make it</div>' +
      '<div class="card-sub" style="white-space:normal">Paste this into your AI assistant. ' +
      'You get the files immediately; the PR shares them and our CI quality-checks them for free.</div>' +
      `<code style="display:block;margin-top:8px;white-space:normal;word-break:break-all;font-size:11px">${prompt.replace(/</g, '&lt;')}</code>` +
      '<button class="vt" style="margin-top:8px">Copy prompt</button>';
    card.querySelector('button').addEventListener('click', (e) => {
      navigator.clipboard.writeText(prompt);
      e.target.textContent = 'Copied!';
    });
    grid.appendChild(card);
  }
  appendChunk(grid, list, 0);
  document.getElementById('count').textContent = list.length;
}

function appendChunk(grid, list, from) {
  const more = grid.querySelector('.more-btn');
  if (more) more.remove();
  const frag = document.createDocumentFragment();
  list.slice(from, from + PAGE).forEach((p) => {
    const card = document.createElement('button');
    card.className = 'card';
    card.innerHTML =
      `<div class="card-name">${p.name}</div>` +
      `<div class="card-sub">${p.family} · ${p.pins}-pin</div>` +
      `<div class="badges">${(p.formats || []).map((f) => `<span class="badge">${f}</span>`).join('')}</div>`;
    card.addEventListener('click', () => { setActive(card); selectPart(p); });
    frag.appendChild(card);
  });
  grid.appendChild(frag);
  if (list.length > from + PAGE) {
    const btn = document.createElement('button');
    btn.className = 'card more-btn';
    btn.textContent = `Show ${Math.min(PAGE, list.length - from - PAGE)} more (${list.length - from - PAGE} left)`;
    btn.addEventListener('click', () => appendChunk(grid, list, from + PAGE));
    grid.appendChild(btn);
  }
}

function setActive(card) {
  if (activeCard) activeCard.classList.remove('active');
  activeCard = card;
  if (card) card.classList.add('active');
}

async function selectPart(p) {
  let meta;
  try {
    const res = await fetch(`${p.path}/meta.json?t=` + Date.now());
    if (!res.ok) throw new Error('meta.json ' + res.status);
    meta = await res.json();
  } catch (e) {
    document.getElementById('viewer-msg').textContent = 'Failed to load part metadata: ' + e.message;
    return;
  }

  document.getElementById('info').classList.remove('hidden');
  document.getElementById('part-name').textContent = meta.name;
  document.getElementById('part-desc').textContent = meta.description || '';

  document.getElementById('verify-warn').classList.toggle('hidden', meta.verified === true);

  // specs
  const specs = document.getElementById('specs');
  const rows = [
    ['Manufacturer', meta.manufacturer],
    ['Family', meta.family],
    ['MPN pattern', meta.mpn_pattern],
    ['Pins', meta.parameters?.pins ?? meta.parameters?.contacts],
    ['Pitch', meta.parameters?.pitch_mm != null ? meta.parameters.pitch_mm + ' mm' : null],
    ['Mounting', meta.parameters?.mounting],
    ['Orientation', meta.parameters?.orientation],
  ].filter((r) => r[1] != null && r[1] !== '');
  specs.innerHTML = rows.map((r) => `<tr><td>${r[0]}</td><td>${r[1]}</td></tr>`).join('');

  // downloads — 실제 존재하는 파일만 (REQUIREMENTS §4-5)
  const dl = document.getElementById('downloads');
  dl.innerHTML = '';
  (meta.formats || []).forEach((fmt) => {
    const fname = meta.files?.[fmtToKey(fmt)];
    if (!fname) return;
    const a = document.createElement('a');
    a.className = 'dl';
    a.href = `${p.path}/${fname}`;
    a.setAttribute('download', fname);
    a.innerHTML = `<span class="ext">${fmt}</span> ${FORMAT_LABELS[fmt] || fmt}`;
    dl.appendChild(a);
  });

  // datasheet (단독 페이지와 동일하게 SPA에도 표시)
  const dsA = document.getElementById('datasheet');
  const dsH = document.getElementById('datasheet-h');
  const hasDs = typeof meta.datasheet === 'string' && meta.datasheet.startsWith('http');
  const dsIsRepo = hasDs && meta.origin === 'imported' && /git(hub|lab)\.com/.test(meta.datasheet);
  if (dsA) {
    if (dsIsRepo) {
      dsA.href = 'https://www.google.com/search?q=' + encodeURIComponent(`"${meta.mpn_pattern}" datasheet`);
      dsA.innerHTML = `Find datasheet (${meta.manufacturer || ''} ${meta.mpn_pattern || ''}) →`;
    } else {
      dsA.href = hasDs ? meta.datasheet : '#';
    }
    dsA.style.display = hasDs ? '' : 'none';
  }
  if (dsH) dsH.style.display = hasDs ? '' : 'none';

  // buy (affiliate placeholder)
  const buy = document.getElementById('buy');
  buy.href = 'https://www.lcsc.com/search?q=' + encodeURIComponent(meta.mpn_pattern || meta.name);

  // 부품 단독 페이지 링크 (SEO 페이지)
  const permalink = document.getElementById('permalink');
  if (permalink) permalink.href = `p/${p.id}/`;

  // 3D / SVG — 배포 후 낡은 캐시가 보이지 않게 캐시버스팅 (파일이 작아 비용 미미)
  const cb = `?t=${Date.now()}`;
  const preview = meta.files?.preview;
  if (preview) loadModel(`https://assets.partreel.com/${p.path}/${preview}${cb}`);
  // 3D 없는 부품(verified-2D): 3D 탭 숨기고 심볼 우선
  const btn3d = document.querySelector('.view-tabs .vt[data-view="3d"]');
  if (btn3d) btn3d.style.display = preview ? '' : 'none';
  if (!preview && view && view.renderer) view.renderer.domElement.style.display = 'none';

  // 뷰 전환용 심볼/풋프린트 SVG
  const symEl = document.getElementById('view-sym');
  const fpEl = document.getElementById('view-fp');
  if (meta.files?.symbol_svg) symEl.src = `${p.path}/${meta.files.symbol_svg}${cb}`;
  if (meta.files?.footprint_svg) fpEl.src = `${p.path}/${meta.files.footprint_svg}${cb}`;
  setView(preview ? '3d' : 'sym');
}


// 심볼/풋프린트 확대: 인라인 SVG는 viewBox 조작(벡터 줌 — 무한 선명), img 폴백은 transform
// 입력: 핀치(모바일 터치 + 데스크톱 터치패드 ctrl+휠) / 확대 중 휠 / 더블클릭 / 줌 버튼.
// 미확대 상태의 일반 스크롤은 페이지에 양보 (2026-07-24 터치패드 제보 — 뷰어가 스크롤을 삼키면 "고장"으로 느껴짐)
function makeZoomable(container, getTarget) {
  let img = { s: 1, tx: 0, ty: 0 };
  let pan = null;
  const pts = new Map();
  let pinchD = 0;
  const svgOf = (t) => (t && t.tagName !== 'IMG') ? t.querySelector('svg') : null;
  const geom = (svg) => {
    const vb = svg.getAttribute('viewBox').split(/\s+/).map(Number);
    if (!svg._vb0) svg._vb0 = vb.slice();
    const r = svg.getBoundingClientRect();
    const s = Math.min(r.width / vb[2], r.height / vb[3]);
    return { vb, r, s,
      ox: r.left + (r.width - vb[2] * s) / 2,
      oy: r.top + (r.height - vb[3] * s) / 2 };
  };
  const isZoomed = (t) => {
    const svg = svgOf(t);
    return svg ? Boolean(svg._vb0 && svg.getAttribute('viewBox') !== svg._vb0.join(' ')) : img.s > 1;
  };
  const setCursor = (t, zoomed) => {
    t.style.cursor = zoomed ? 'grab' : 'zoom-in';
    container.style.touchAction = zoomed ? 'none' : 'pan-y';
  };
  const reset = () => {
    const t = getTarget(); if (!t) return;
    const svg = svgOf(t);
    if (svg && svg._vb0) svg.setAttribute('viewBox', svg._vb0.join(' '));
    img = { s: 1, tx: 0, ty: 0 }; t.style.transform = '';
    setCursor(t, false);
  };
  const zoomAt = (t, cx, cy, k) => {
    const svg = svgOf(t);
    if (svg && svg.getAttribute('viewBox')) {
      const { vb, s, ox, oy } = geom(svg);
      const vb0 = svg._vb0;
      const nw = Math.min(vb0[2], Math.max(vb0[2] / 40, vb[2] / k));
      const kk = vb[2] / nw;
      const px = vb[0] + (cx - ox) / s;
      const py = vb[1] + (cy - oy) / s;
      const nx = px - (px - vb[0]) / kk;
      const ny = py - (py - vb[1]) / kk;
      if (nw >= vb0[2]) svg.setAttribute('viewBox', vb0.join(' '));
      else svg.setAttribute('viewBox', `${nx} ${ny} ${nw} ${vb[3] / kk}`);
      setCursor(t, nw < vb0[2]);
    } else {
      const r = container.getBoundingClientRect();
      const mx = cx - r.left, my = cy - r.top;
      const ns = Math.min(30, Math.max(1, img.s * k));
      const f = ns / img.s;
      img.tx = mx - f * (mx - img.tx); img.ty = my - f * (my - img.ty); img.s = ns;
      if (img.s === 1) { img.tx = 0; img.ty = 0; }
      t.style.transform = `translate(${img.tx}px,${img.ty}px) scale(${img.s})`;
      setCursor(t, img.s > 1);
    }
  };
  container.addEventListener('wheel', (e) => {
    const t = getTarget(); if (!t) return;
    const pinch = e.ctrlKey || e.metaKey;  // 터치패드 핀치는 ctrl+휠로 도착
    if (!pinch && !isZoomed(t)) return;    // 미확대 + 일반 스크롤 = 페이지 스크롤에 양보
    if (!pinch && Math.abs(e.deltaX) > Math.abs(e.deltaY)) return;
    e.preventDefault();
    const dy = e.deltaMode === 1 ? e.deltaY * 33 : (e.deltaMode === 2 ? e.deltaY * 300 : e.deltaY);
    const k = Math.min(2, Math.max(0.5, Math.exp(-dy * (pinch ? 0.01 : 0.0015))));
    zoomAt(t, e.clientX, e.clientY, k);
  }, { passive: false });
  container.addEventListener('pointerdown', (e) => {
    const t = getTarget(); if (!t) return;
    if (e.isPrimary) pts.clear();
    pts.set(e.pointerId, [e.clientX, e.clientY]);
    if (pts.size === 2) {
      const [a, b] = [...pts.values()];
      pinchD = Math.hypot(a[0] - b[0], a[1] - b[1]);
      pan = null;
      container.setPointerCapture(e.pointerId);
      return;
    }
    const svg = svgOf(t);
    if (svg && svg._vb0 && svg.getAttribute('viewBox') !== svg._vb0.join(' ')) {
      const { vb } = geom(svg);
      pan = { kind: 'svg', x: e.clientX, y: e.clientY, vb };
    } else if (!svg && img.s > 1) {
      pan = { kind: 'img', x: e.clientX - img.tx, y: e.clientY - img.ty };
    } else return;
    container.setPointerCapture(e.pointerId);
  });
  container.addEventListener('pointermove', (e) => {
    const t = getTarget(); if (!t) return;
    if (pts.has(e.pointerId)) pts.set(e.pointerId, [e.clientX, e.clientY]);
    if (pts.size === 2) {
      const [a, b] = [...pts.values()];
      const d = Math.hypot(a[0] - b[0], a[1] - b[1]);
      if (pinchD > 0 && d > 0) zoomAt(t, (a[0] + b[0]) / 2, (a[1] + b[1]) / 2, d / pinchD);
      pinchD = d;
      return;
    }
    if (!pan) return;
    if (pan.kind === 'svg') {
      const svg = svgOf(t); if (!svg) return;
      const { s } = geom(svg);
      svg.setAttribute('viewBox', `${pan.vb[0] - (e.clientX - pan.x) / s} ` +
        `${pan.vb[1] - (e.clientY - pan.y) / s} ${pan.vb[2]} ${pan.vb[3]}`);
    } else {
      img.tx = e.clientX - pan.x; img.ty = e.clientY - pan.y;
      t.style.transform = `translate(${img.tx}px,${img.ty}px) scale(${img.s})`;
    }
  });
  const drop = (e) => { pts.delete(e.pointerId); pinchD = 0; pan = null; };
  container.addEventListener('pointerup', drop);
  container.addEventListener('pointercancel', drop);
  container.addEventListener('dblclick', (e) => {
    const t = getTarget(); if (!t) return;
    if (isZoomed(t)) reset(); else zoomAt(t, e.clientX, e.clientY, 2.5);
  });
  // 줌 버튼 (+ / − / 원위치) — 휠 없는 환경·발견성 (마우스는 더블클릭/버튼, 터치패드는 핀치)
  const ui = document.createElement('div');
  ui.className = 'zoom-ui';
  const centerZoom = (k) => {
    const t = getTarget(); if (!t) return;
    const r = container.getBoundingClientRect();
    zoomAt(t, r.left + r.width / 2, r.top + r.height / 2, k);
  };
  for (const [label, title, fn] of [
      ['+', 'Zoom in', () => centerZoom(1.6)],
      ['−', 'Zoom out', () => centerZoom(1 / 1.6)],
      ['⟲', 'Reset view', reset]]) {
    const b = document.createElement('button');
    b.type = 'button'; b.textContent = label; b.title = title;
    b.addEventListener('click', fn);
    ui.appendChild(b);
  }
  container.appendChild(ui);
  container.style.touchAction = 'pan-y';
  reset.setUiVisible = (v) => { ui.style.display = v ? '' : 'none'; };
  reset.setUiVisible(false);  // 초기엔 숨김 — setView가 2D 탭에서 켬
  return reset;
}

let zoomReset = null;

function setView(v) {
  document.querySelectorAll('.view-tabs .vt').forEach((b) => b.classList.toggle('active', b.dataset.view === v));
  const sym = document.getElementById('view-sym');
  const fp = document.getElementById('view-fp');
  const msg = document.getElementById('viewer-msg');
  if (zoomReset) { zoomReset(); if (zoomReset.setUiVisible) zoomReset.setUiVisible(v !== '3d'); }
  if (sym) sym.hidden = v !== 'sym';
  if (fp) fp.hidden = v !== 'fp';
  if (view && view.renderer) view.renderer.domElement.style.display = v === '3d' ? 'block' : 'none';
  if (v !== '3d' && msg) msg.classList.add('hidden');
}

(() => {
  const c = document.getElementById('viewer');
  if (c) zoomReset = makeZoomable(c, () => {
    const sym = document.getElementById('view-sym');
    const fp = document.getElementById('view-fp');
    return (sym && !sym.hidden) ? sym : ((fp && !fp.hidden) ? fp : null);
  });
})();

function setupTabs() {
  document.querySelectorAll('.view-tabs .vt').forEach((b) => b.addEventListener('click', () => setView(b.dataset.view)));
}

function fmtToKey(fmt) {
  // formats 항목 -> files 키 매핑
  if (fmt === 'glb') return 'preview';
  if (fmt === 'step') return 'model_3d';
  if (fmt === 'kicad_mod') return 'footprint';
  if (fmt === 'kicad_sym') return 'symbol';
  return fmt;
}

/* ---------- three.js 3D 뷰어 ---------- */
function setupViewer() {
  const el = document.getElementById('viewer');
  const w = el.clientWidth, h = el.clientHeight;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(40, w / h, 0.1, 1000);
  camera.position.set(18, 14, 18);

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setSize(w, h);
  el.appendChild(renderer.domElement);

  scene.add(new THREE.AmbientLight(0xffffff, 0.9));
  scene.add(new THREE.HemisphereLight(0xffffff, 0x666677, 0.8));
  const key = new THREE.DirectionalLight(0xffffff, 1.2); key.position.set(10, 20, 15); scene.add(key);
  const fill = new THREE.DirectionalLight(0xffffff, 0.6); fill.position.set(-15, 5, -10); scene.add(fill);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.autoRotate = true;
  controls.autoRotateSpeed = 1.6;

  view = { scene, camera, renderer, controls, el, model: null };

  window.addEventListener('resize', onResize);
  (function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
  })();
}

function onResize() {
  if (!view) return;
  const w = view.el.clientWidth, h = view.el.clientHeight;
  view.camera.aspect = w / h;
  view.camera.updateProjectionMatrix();
  view.renderer.setSize(w, h);
}

function loadModel(url) {
  if (!view) return;
  const msg = document.getElementById('viewer-msg');
  msg.classList.remove('hidden');
  msg.textContent = 'Loading 3D…';

  if (view.model) { view.scene.remove(view.model); view.model = null; }

  new GLTFLoader().load(url, (gltf) => {
    const model = gltf.scene;
    model.rotation.x = -Math.PI / 2;  // CAD Z-up -> viewer Y-up (부품 바로 세우기)
    model.updateMatrixWorld(true);
    // GLB 기본 재질이 금속성(metallic)이라 환경맵 없인 어둡게 렌더됨 → 보정
    model.traverse((o) => {
      if (o.isMesh && o.material) {
        o.material.metalness = 0.15;
        o.material.roughness = 0.55;
      }
    });
    // 중심 정렬 + 카메라 핏
    const box = new THREE.Box3().setFromObject(model);
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    model.position.sub(center);
    view.scene.add(model);
    view.model = model;

    const maxDim = Math.max(size.x, size.y, size.z);
    const dist = maxDim * 2.4;
    view.camera.position.set(dist, dist * 0.8, dist);
    view.camera.lookAt(0, 0, 0);
    view.controls.target.set(0, 0, 0);
    view.controls.update();

    msg.classList.add('hidden');
  }, undefined, (err) => {
    msg.classList.remove('hidden');
    msg.textContent = 'Failed to load 3D: ' + (err?.message || url);
  });
}

init();
