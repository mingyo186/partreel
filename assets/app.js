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
  renderList(parts);
  setupViewer();
  setupTabs();
  if (parts.length) selectPart(parts[0]);

  document.getElementById('q').addEventListener('input', (e) => {
    const q = e.target.value.toLowerCase().trim();
    const filtered = !q ? parts : parts.filter((p) =>
      (p.name + ' ' + p.family + ' ' + (p.keywords || []).join(' ')).toLowerCase().includes(q));
    renderList(filtered);
  });
}

function renderList(list) {
  const grid = document.getElementById('list');
  grid.innerHTML = '';
  list.forEach((p) => {
    const card = document.createElement('button');
    card.className = 'card';
    card.innerHTML =
      `<div class="card-name">${p.name}</div>` +
      `<div class="card-sub">${p.family} · ${p.pins}-pin</div>` +
      `<div class="badges">${(p.formats || []).map((f) => `<span class="badge">${f}</span>`).join('')}</div>`;
    card.addEventListener('click', () => { setActive(card); selectPart(p); });
    grid.appendChild(card);
  });
  document.getElementById('count').textContent = list.length;
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

function setView(v) {
  document.querySelectorAll('.view-tabs .vt').forEach((b) => b.classList.toggle('active', b.dataset.view === v));
  const sym = document.getElementById('view-sym');
  const fp = document.getElementById('view-fp');
  const msg = document.getElementById('viewer-msg');
  if (sym) sym.hidden = v !== 'sym';
  if (fp) fp.hidden = v !== 'fp';
  if (view && view.renderer) view.renderer.domElement.style.display = v === '3d' ? 'block' : 'none';
  if (v !== '3d' && msg) msg.classList.add('hidden');
}

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
