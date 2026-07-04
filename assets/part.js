// 부품 단독 페이지: 뷰 탭(3D/심볼/풋프린트) + 3D 뷰어.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const el = document.getElementById('viewer');
const symEl = document.getElementById('view-sym');
const fpEl = document.getElementById('view-fp');
let rendererCanvas = null;

const CB = `?t=${Date.now()}`;  // 배포 후 낡은 캐시 방지
if (el) {
  if (el.dataset.sym && symEl) symEl.src = el.dataset.sym + CB;
  if (el.dataset.fp && fpEl) fpEl.src = el.dataset.fp + CB;
}

function setView(v) {
  document.querySelectorAll('.view-tabs .vt').forEach((b) => b.classList.toggle('active', b.dataset.view === v));
  const msg = el && el.querySelector('.viewer-msg');
  if (symEl) symEl.hidden = v !== 'sym';
  if (fpEl) fpEl.hidden = v !== 'fp';
  if (rendererCanvas) rendererCanvas.style.display = v === '3d' ? 'block' : 'none';
  if (v !== '3d' && msg) msg.style.display = 'none';
}
document.querySelectorAll('.view-tabs .vt').forEach((b) => b.addEventListener('click', () => setView(b.dataset.view)));

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
