/* Сфера Мысли — 3D-фон библиотеки (Three.js r128)
   Тёмный читальный зал: стена стеллажей вдали, парящие книги, золотая пыль в свете лампы.
   Камера мягко следует за мышью и прокруткой. Учитывает prefers-reduced-motion. */
(() => {
  const canvas = document.getElementById('bg-canvas');
  const fail = () => document.body.classList.add('no-webgl');
  if (!canvas || typeof THREE === 'undefined') return fail();

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
  } catch (e) { return fail(); }

  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const mobile = matchMedia('(max-width: 700px)').matches;
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2)); // чёткая картинка на 2K/4K
  renderer.setSize(innerWidth, innerHeight, false);
  renderer.setClearColor(0x0d0a07, 1);
  renderer.outputEncoding = THREE.sRGBEncoding;

  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x0d0a07, 0.03);
  const camera = new THREE.PerspectiveCamera(55, innerWidth / innerHeight, 0.1, 120);
  camera.position.set(0, 0, 9);

  /* --- свет --- */
  scene.add(new THREE.AmbientLight(0x6b5a45, 0.7));
  const lamp = new THREE.PointLight(0xffc67a, 2.2, 60, 1.6);
  lamp.position.set(2, 3, -4);
  scene.add(lamp);
  const rim = new THREE.PointLight(0x7a4a2a, 1.2, 50, 1.5);
  rim.position.set(-9, -4, 2);
  scene.add(rim);

  /* --- мягкая текстура для пыли и свечения --- */
  const glowTex = (() => {
    const c = document.createElement('canvas'); c.width = c.height = 64;
    const x = c.getContext('2d'), g = x.createRadialGradient(32, 32, 0, 32, 32, 32);
    g.addColorStop(0, 'rgba(255,236,190,1)'); g.addColorStop(.35, 'rgba(255,214,140,.45)'); g.addColorStop(1, 'rgba(255,200,120,0)');
    x.fillStyle = g; x.fillRect(0, 0, 64, 64);
    return new THREE.CanvasTexture(c);
  })();

  /* --- стена стеллажей вдали (instancing: ~2000 книг одним вызовом) --- */
  (function shelves() {
    const hues = [0.0, 0.02, 0.05, 0.08, 0.1, 0.55, 0.33, 0.75];
    const rows = 11, startY = -17, rowH = 3.2, halfW = 38;
    const mesh = new THREE.InstancedMesh(
      new THREE.BoxGeometry(1, 1, 1),
      new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.8 }), 2600);
    const m = new THREE.Matrix4(), q = new THREE.Quaternion(), s = new THREE.Vector3(), p = new THREE.Vector3(), c = new THREE.Color();
    let n = 0;
    for (let r = 0; r < rows; r++) {
      const y = startY + r * rowH;
      for (let x = -halfW; x < halfW && n < 2590;) {
        const w = 0.22 + Math.random() * 0.4, h = 1.5 + Math.random() * 1.2, d = 0.9 + Math.random() * 0.4;
        if (Math.random() < 0.05) { x += w + 0.3 + Math.random(); continue; } // пропуск — «книгу взяли»
        p.set(x + w / 2, y + h / 2, -26);
        s.set(w * 0.96, h, d);
        m.compose(p, q, s); mesh.setMatrixAt(n, m);
        const hue = hues[(Math.random() * hues.length) | 0];
        c.setHSL(hue, 0.32 + Math.random() * 0.2, 0.1 + Math.random() * 0.12);
        mesh.setColorAt(n, c);
        n++; x += w;
      }
      const plank = new THREE.Mesh(new THREE.BoxGeometry(halfW * 2 + 2, 0.18, 1.6),
        new THREE.MeshStandardMaterial({ color: 0x2a1b0f, roughness: 0.7 }));
      plank.position.set(0, y - 0.09, -26);
      scene.add(plank);
    }
    mesh.count = n;
    mesh.instanceMatrix.needsUpdate = true;
    mesh.instanceColor.needsUpdate = true;
    scene.add(mesh);
  })();

  /* --- тёплое свечение за центром --- */
  const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, color: 0xffb85c, transparent: true, opacity: 0.32, blending: THREE.AdditiveBlending, depthWrite: false, fog: false }));
  halo.scale.set(40, 26, 1); halo.position.set(3, 2, -20);
  scene.add(halo);

  /* --- парящие книги --- */
  const COVERS = [0x5a1f1f, 0x1f3b4d, 0x2f4a2f, 0x4a3320, 0x3b2a4d, 0x6b4a1e, 0x24303a, 0x7a2e2e, 0x35402a];
  const paperMat = new THREE.MeshStandardMaterial({ color: 0xe9dcc0, roughness: 0.9 });
  const goldMat = new THREE.MeshStandardMaterial({ color: 0xc9a96e, roughness: 0.35, metalness: 0.85 });
  const coverMats = COVERS.map(col => new THREE.MeshStandardMaterial({ color: col, roughness: 0.55, metalness: 0.08 }));

  function makeBook() {
    const grp = new THREE.Group();
    const w = 0.9 + Math.random() * 0.5, h = 1.3 + Math.random() * 0.6, t = 0.22 + Math.random() * 0.26;
    const cm = coverMats[(Math.random() * coverMats.length) | 0];
    const box = (x, y, z, mat) => new THREE.Mesh(new THREE.BoxGeometry(x, y, z), mat);
    const pages = box(w - 0.05, h - 0.07, t - 0.06, paperMat); pages.position.x = 0.02;
    const front = box(w, h, 0.03, cm); front.position.z = t / 2;
    const back = box(w, h, 0.03, cm); back.position.z = -t / 2;
    const spine = box(0.06, h, t + 0.03, cm); spine.position.x = -w / 2;
    const band1 = box(0.066, h * 0.07, t + 0.04, goldMat); band1.position.set(-w / 2, h * 0.26, 0);
    const band2 = band1.clone(); band2.position.y = -h * 0.26;
    const plate = new THREE.Mesh(new THREE.PlaneGeometry(w * 0.5, h * 0.12), goldMat);
    plate.position.set(0.04, h * 0.2, t / 2 + 0.017);
    const frame = new THREE.Mesh(new THREE.PlaneGeometry(w * 0.72, h * 0.72), new THREE.MeshBasicMaterial({ color: 0xc9a96e, transparent: true, opacity: 0.1, depthWrite: false }));
    frame.position.set(0.04, 0, t / 2 + 0.016);
    grp.add(pages, front, back, spine, band1, band2, plate, frame);
    return grp;
  }

  const books = [];
  const count = mobile ? 16 : 34;
  for (let i = 0; i < count; i++) {
    const b = makeBook();
    const z = -14 + Math.random() * 16;
    const spread = 7 + (-z) * 0.5 + 4;
    b.position.set((Math.random() * 2 - 1) * spread * 1.5, (Math.random() * 2 - 1) * (spread * 0.8), z);
    b.rotation.set(Math.random() * 6.28, Math.random() * 6.28, Math.random() * 6.28);
    b.userData = {
      base: b.position.y, ph: Math.random() * 6.28,
      sp: 0.25 + Math.random() * 0.4, amp: 0.15 + Math.random() * 0.35,
      rot: new THREE.Vector3((Math.random() - .5) * 0.18, (Math.random() - .5) * 0.22, (Math.random() - .5) * 0.12)
    };
    const sc = 0.8 + Math.random() * 0.7; b.scale.setScalar(sc);
    scene.add(b); books.push(b);
  }

  /* --- золотая пыль --- */
  const dustN = mobile ? 350 : 900;
  const dpos = new Float32Array(dustN * 3), dv = new Float32Array(dustN);
  for (let i = 0; i < dustN; i++) {
    dpos[i * 3] = (Math.random() - .5) * 40; dpos[i * 3 + 1] = (Math.random() - .5) * 24; dpos[i * 3 + 2] = -16 + Math.random() * 24;
    dv[i] = 0.08 + Math.random() * 0.22;
  }
  const dgeo = new THREE.BufferGeometry();
  dgeo.setAttribute('position', new THREE.BufferAttribute(dpos, 3));
  const dust = new THREE.Points(dgeo, new THREE.PointsMaterial({ map: glowTex, size: 0.2, color: 0xffd9a0, transparent: true, opacity: 0.75, blending: THREE.AdditiveBlending, depthWrite: false, sizeAttenuation: true }));
  scene.add(dust);

  /* --- управление камерой --- */
  const mouse = { x: 0, y: 0 }; let scrollY = 0;
  addEventListener('pointermove', e => { mouse.x = (e.clientX / innerWidth - .5) * 2; mouse.y = (e.clientY / innerHeight - .5) * 2; }, { passive: true });
  addEventListener('scroll', () => { scrollY = window.scrollY; }, { passive: true });
  addEventListener('resize', () => {
    camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix();
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(innerWidth, innerHeight, false);
    if (reduce) renderer.render(scene, camera);
  });

  const clock = new THREE.Clock(); let raf = 0;
  function frame() {
    const t = clock.getElapsedTime();
    camera.position.x += (mouse.x * 1.4 - camera.position.x) * 0.04;
    camera.position.y += (-mouse.y * 0.9 - scrollY * 0.004 - camera.position.y) * 0.04;
    camera.lookAt(0, camera.position.y * 0.3, -4);
    lamp.intensity = 2.1 + Math.sin(t * 2.3) * 0.12 + Math.sin(t * 5.1) * 0.06; // живой огонь
    for (const b of books) {
      const d = b.userData;
      b.rotation.x += d.rot.x * 0.01; b.rotation.y += d.rot.y * 0.01; b.rotation.z += d.rot.z * 0.01;
      b.position.y = d.base + Math.sin(t * d.sp + d.ph) * d.amp;
    }
    const p = dgeo.attributes.position.array;
    for (let i = 0; i < dustN; i++) {
      p[i * 3 + 1] += dv[i] * 0.012;
      p[i * 3] += Math.sin(t * .3 + i) * 0.0016;
      if (p[i * 3 + 1] > 12) p[i * 3 + 1] = -12;
    }
    dgeo.attributes.position.needsUpdate = true;
    renderer.render(scene, camera);
    raf = requestAnimationFrame(frame);
  }

  if (reduce) { camera.lookAt(0, 0, -4); renderer.render(scene, camera); return; }
  frame();
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) cancelAnimationFrame(raf); else { clock.getDelta(); frame(); }
  });
})();
