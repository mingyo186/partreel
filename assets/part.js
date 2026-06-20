// 부품 단독 페이지용 3D 뷰어. #viewer[data-glb]를 읽어 GLB를 렌더.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const el = document.getElementById('viewer');
const url = el && el.dataset.glb;

if (el && url) {
  const w = el.clientWidth, h = el.clientHeight;
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(40, w / h, 0.1, 1000);
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setSize(w, h);
  el.appendChild(renderer.domElement);

  scene.add(new THREE.AmbientLight(0xffffff, 0.7));
  const key = new THREE.DirectionalLight(0xffffff, 1.1); key.position.set(10, 20, 15); scene.add(key);
  const fill = new THREE.DirectionalLight(0xffffff, 0.5); fill.position.set(-15, 5, -10); scene.add(fill);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.autoRotate = true;
  controls.autoRotateSpeed = 1.6;

  const msg = el.querySelector('.viewer-msg');

  new GLTFLoader().load(url, (gltf) => {
    const model = gltf.scene;
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
  }, undefined, () => { if (msg) msg.textContent = '3D 로드 실패'; });

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
