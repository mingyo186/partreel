// 부품 단독 페이지: 뷰 탭(3D/심볼/풋프린트) + 3D 뷰어.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const el = document.getElementById('viewer');
const symEl = document.getElementById('view-sym');
const fpEl = document.getElementById('view-fp');
let rendererCanvas = null;

const CB = `?t=${Date.now()}`;  // 배포 후 낡은 캐시 방지 (glb/api 전용)
// SVG는 페이지에 인라인됨(v9) — 초대형만 img 폴백(data-src, 콘텐츠 해시 버전)
for (const e of [symEl, fpEl]) {
  if (e && e.tagName === 'IMG' && e.dataset.src) e.src = e.dataset.src;
}


// 심볼/풋프린트 확대: 인라인 SVG는 viewBox 조작(벡터 줌 — 무한 선명), img 폴백은 transform
function makeZoomable(container, getTarget) {
  let img = { s: 1, tx: 0, ty: 0 };
  let pan = null;
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
  const setCursor = (t, zoomed) => { t.style.cursor = zoomed ? 'grab' : 'zoom-in'; };
  const reset = () => {
    const t = getTarget(); if (!t) return;
    const svg = svgOf(t);
    if (svg && svg._vb0) svg.setAttribute('viewBox', svg._vb0.join(' '));
    img = { s: 1, tx: 0, ty: 0 }; t.style.transform = '';
    setCursor(t, false);
  };
  container.addEventListener('wheel', (e) => {
    const t = getTarget(); if (!t) return;
    e.preventDefault();
    const k = Math.exp(-e.deltaY * 0.0015);
    const svg = svgOf(t);
    if (svg && svg.getAttribute('viewBox')) {
      const { vb, s, ox, oy } = geom(svg);
      const vb0 = svg._vb0;
      const nw = Math.min(vb0[2], Math.max(vb0[2] / 40, vb[2] / k));
      const kk = vb[2] / nw;
      const px = vb[0] + (e.clientX - ox) / s;
      const py = vb[1] + (e.clientY - oy) / s;
      const nx = px - (px - vb[0]) / kk;
      const ny = py - (py - vb[1]) / kk;
      if (nw >= vb0[2]) svg.setAttribute('viewBox', vb0.join(' '));
      else svg.setAttribute('viewBox', `${nx} ${ny} ${nw} ${vb[3] / kk}`);
      setCursor(t, nw < vb0[2]);
    } else {
      const r = container.getBoundingClientRect();
      const mx = e.clientX - r.left, my = e.clientY - r.top;
      const ns = Math.min(30, Math.max(1, img.s * k));
      const f = ns / img.s;
      img.tx = mx - f * (mx - img.tx); img.ty = my - f * (my - img.ty); img.s = ns;
      if (img.s === 1) { img.tx = 0; img.ty = 0; }
      t.style.transform = `translate(${img.tx}px,${img.ty}px) scale(${img.s})`;
      setCursor(t, img.s > 1);
    }
  }, { passive: false });
  container.addEventListener('pointerdown', (e) => {
    const t = getTarget(); if (!t) return;
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
    if (!pan) return;
    const t = getTarget(); if (!t) return;
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
  container.addEventListener('pointerup', () => { pan = null; });
  container.addEventListener('dblclick', () => { if (getTarget()) reset(); });
  return reset;
}

let zoomReset = null;

function setView(v) {
  document.querySelectorAll('.view-tabs .vt').forEach((b) => b.classList.toggle('active', b.dataset.view === v));
  const msg = el && el.querySelector('.viewer-msg');
  if (zoomReset) zoomReset();
  if (symEl) symEl.hidden = v !== 'sym';
  if (fpEl) fpEl.hidden = v !== 'fp';
  if (rendererCanvas) rendererCanvas.style.display = v === '3d' ? 'block' : 'none';
  if (v !== '3d' && msg) msg.style.display = 'none';
}
document.querySelectorAll('.view-tabs .vt').forEach((b) => b.addEventListener('click', () => setView(b.dataset.view)));
if (el && el.dataset.default && el.dataset.default !== '3d') setView(el.dataset.default);
if (el) zoomReset = makeZoomable(el, () => (symEl && !symEl.hidden) ? symEl : ((fpEl && !fpEl.hidden) ? fpEl : null));  // verified-2D 기본탭

const url = el && el.dataset.glb ? el.dataset.glb + CB : null;
if (el && url) {
  const w = el.clientWidth, h = el.clientHeight;
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(40, w / h, 0.1, 1000);
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setSize(w, h);
  el.appendChild(renderer.domElement);
  rendererCanvas = renderer.domElement;

  scene.add(new THREE.AmbientLight(0xffffff, 0.9));
  scene.add(new THREE.HemisphereLight(0xffffff, 0x666677, 0.8));
  const key = new THREE.DirectionalLight(0xffffff, 1.2); key.position.set(10, 20, 15); scene.add(key);
  const fill = new THREE.DirectionalLight(0xffffff, 0.6); fill.position.set(-15, 5, -10); scene.add(fill);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.autoRotate = true;
  controls.autoRotateSpeed = 1.6;

  const msg = el.querySelector('.viewer-msg');

  new GLTFLoader().load(url, (gltf) => {
    const model = gltf.scene;
    model.rotation.x = -Math.PI / 2;  // CAD Z-up -> viewer Y-up (부품 바로 세우기)
    model.updateMatrixWorld(true);
    // 금속성 기본 재질이 환경맵 없인 어둡게 렌더됨 → 보정
    model.traverse((o) => {
      if (o.isMesh && o.material) {
        o.material.metalness = 0.15;
        o.material.roughness = 0.55;
      }
    });
    const box = new THREE.Box3().setFromObject(model);
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    model.position.sub(center);
    scene.add(model);
    const d = Math.max(size.x, size.y, size.z) * 2.4;
    camera.position.set(d, d * 0.8, d);
    camera.lookAt(0, 0, 0);
    controls.target.set(0, 0, 0);
    controls.update();
    if (msg) msg.style.display = 'none';
  }, undefined, () => { if (msg) msg.textContent = 'Failed to load 3D'; });

  window.addEventListener('resize', () => {
    const w2 = el.clientWidth, h2 = el.clientHeight;
    camera.aspect = w2 / h2; camera.updateProjectionMatrix(); renderer.setSize(w2, h2);
  });

  (function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
  })();
}

// Field-report 배지: 부품 API에서 field_reports 읽어 >0일 때만 표시 (§17-⑤)
(async () => {
  const badge = document.getElementById('field-badge');
  if (!badge) return;
  try {
    const pid = location.pathname.split('/').filter(Boolean).pop();
    const r = await fetch(`/api/v1/parts/${pid}.json${CB}`);
    if (!r.ok) return;
    const fr = (await r.json()).field_reports || {};
    const ok = fr.worked | 0, bad = fr.problem | 0;
    if (ok + bad > 0) {
      badge.textContent = `✅ field-verified on real boards: ${ok}` +
        (bad ? ` · ⚠️ problems reported: ${bad}` : '');
      badge.hidden = false;
    }
  } catch (e) { /* 배지는 장식 — 실패해도 조용히 */ }
})();
