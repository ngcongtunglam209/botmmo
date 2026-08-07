
<script type="module">
const adminThreeCanvas = document.getElementById("adminThreeScene");
const reducedMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
if (!adminThreeCanvas || reducedMotion || !window.WebGLRenderingContext) {
  document.documentElement.classList.add(reducedMotion ? "three-reduced" : "three-fallback");
} else {
  import("https://cdn.jsdelivr.net/npm/three@0.164.1/build/three.module.js")
    .then((THREE) => {
      const renderer = new THREE.WebGLRenderer({
        canvas: adminThreeCanvas,
        alpha: true,
        antialias: true,
        powerPreference: "low-power"
      });
      renderer.setClearColor(0x000000, 0);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.55));

      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(46, 1, 0.1, 120);
      camera.position.set(0, 8.5, 24);

      const rig = new THREE.Group();
      scene.add(rig);

      const gridA = new THREE.GridHelper(48, 48, 0x0891b2, 0xb6c2d1);
      gridA.material.transparent = true;
      gridA.material.opacity = 0.22;
      gridA.position.y = -6.5;
      rig.add(gridA);

      const gridB = new THREE.GridHelper(36, 24, 0xe11d48, 0xcbd5e1);
      gridB.material.transparent = true;
      gridB.material.opacity = 0.12;
      gridB.rotation.z = Math.PI / 2;
      gridB.position.set(-18, 0, -8);
      rig.add(gridB);

      const linePalette = [0x0891b2, 0x4f46e5, 0xca8a04, 0xe11d48];
      const streamGroup = new THREE.Group();
      rig.add(streamGroup);
      for (let j = 0; j < 18; j += 1) {
        const points = [];
        const z = -14 + j * 1.65;
        const phase = j * 0.45;
        for (let i = 0; i < 72; i += 1) {
          const x = -26 + i * 0.78;
          const y = Math.sin(i * 0.22 + phase) * 0.6 + Math.cos(j * 0.7) * 0.3;
          points.push(new THREE.Vector3(x, y, z + Math.sin(i * 0.09 + phase) * 0.55));
        }
        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        const material = new THREE.LineBasicMaterial({
          color: linePalette[j % linePalette.length],
          transparent: true,
          opacity: j % 3 === 0 ? 0.30 : 0.18
        });
        const line = new THREE.Line(geometry, material);
        line.userData.phase = phase;
        streamGroup.add(line);
      }

      const nodeGeometry = new THREE.BufferGeometry();
      const vertices = [];
      const colors = [];
      const color = new THREE.Color();
      for (let i = 0; i < 180; i += 1) {
        const x = ((i * 37) % 100) / 100 * 48 - 24;
        const z = ((i * 61) % 100) / 100 * 30 - 16;
        const y = Math.sin(i * 1.7) * 2.1 - 1.4;
        vertices.push(x, y, z);
        color.setHex(linePalette[i % linePalette.length]);
        colors.push(color.r, color.g, color.b);
      }
      nodeGeometry.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
      nodeGeometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
      const nodeMaterial = new THREE.PointsMaterial({
        size: 0.055,
        vertexColors: true,
        transparent: true,
        opacity: 0.36
      });
      const nodes = new THREE.Points(nodeGeometry, nodeMaterial);
      rig.add(nodes);

      function resize() {
        const width = window.innerWidth || 1;
        const height = window.innerHeight || 1;
        renderer.setSize(width, height, false);
        camera.aspect = width / height;
        camera.position.z = width < 720 ? 31 : 24;
        camera.position.y = width < 720 ? 9.5 : 8.5;
        camera.updateProjectionMatrix();
      }

      let animationId = 0;
      function animate(time) {
        const t = time * 0.001;
        rig.rotation.x = -0.22 + Math.sin(t * 0.12) * 0.025;
        rig.rotation.y = -0.20 + Math.sin(t * 0.09) * 0.06;
        streamGroup.children.forEach((line, index) => {
          line.position.x = Math.sin(t * 0.28 + line.userData.phase) * 0.38;
          line.position.y = Math.cos(t * 0.22 + index) * 0.08;
        });
        nodes.rotation.y = t * 0.025;
        renderer.render(scene, camera);
        animationId = window.requestAnimationFrame(animate);
      }

      function handleVisibility() {
        if (document.hidden && animationId) {
          window.cancelAnimationFrame(animationId);
          animationId = 0;
        } else if (!document.hidden && !animationId) {
          animationId = window.requestAnimationFrame(animate);
        }
      }

      resize();
      window.addEventListener("resize", resize, { passive: true });
      document.addEventListener("visibilitychange", handleVisibility);
      document.documentElement.classList.add("three-ready");
      animationId = window.requestAnimationFrame(animate);
    })
    .catch(() => {
      document.documentElement.classList.add("three-fallback");
    });
}
</script>
