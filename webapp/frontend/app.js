/* leo_coord web app — tab 1: chức năng + bản đồ 3D; tab 2: tham luận & tài liệu */
"use strict";

/* ---------------- tab switching ---------------- */
document.querySelectorAll(".tab").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tabpage").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(btn.dataset.tab).classList.add("active");
    if (btn.dataset.tab === "tab1" && window.__globe) window.__globe.resize();
  });
});

/* ---------------- helpers ---------------- */
const $ = id => document.getElementById(id);
const fmtPct = v => (v * 100).toFixed(1) + "%";
function badge(text, cls) { return `<span class="badge ${cls}">${text}</span>`; }

function formParams() {
  const deployed = [];
  ($("f_deployed").value || "").split(",").forEach(s => {
    const [d, n] = s.trim().split(":");
    if (d && n) deployed.push([d.trim(), parseInt(n.trim(), 10)]);
  });
  return {
    name: $("f_name").value || "LEO-WEB",
    alt_km: parseFloat($("f_alt").value) || 550,
    inc_deg: parseFloat($("f_inc").value) || 53,
    n_sats: parseInt($("f_nsats").value, 10) || 120,
    n_planes: parseInt($("f_nplanes").value, 10) || 6,
    kind: $("f_kind").value,
    band_ghz: $("f_band").value,
    eirp_dbw_per_mhz: parseFloat($("f_eirp").value) || 10,
    gso_lon: parseFloat($("f_gsolon").value) || 105.5,
    dish_d_m: parseFloat($("f_dish").value) || 1.2,
    biu_deadline: $("f_biu").value || null,
    deployed,
  };
}

$("preset-demo").addEventListener("click", () => {
  $("f_name").value = "DEMO_LEO_KU"; $("f_alt").value = 550; $("f_inc").value = 53;
  $("f_nsats").value = 120; $("f_nplanes").value = 6; $("f_kind").value = "delta";
  $("f_eirp").value = 10; $("f_band").value = "10.7-12.7";
});
$("preset-big").addEventListener("click", () => {
  $("f_name").value = "MAU_1000VT"; $("f_alt").value = 550; $("f_inc").value = 53;
  $("f_nsats").value = 1000; $("f_nplanes").value = 20; $("f_kind").value = "delta";
  $("f_eirp").value = 10; $("f_band").value = "10.7-12.7";
});

/* ---------------- tab 1: assess ---------------- */
$("btn-assess").addEventListener("click", async () => {
  const btn = $("btn-assess"), st = $("assess-status");
  btn.disabled = true; btn.textContent = "⏳ Đang tính…";
  st.textContent = "Đang lan truyền quỹ đạo và chạy các kiểm tra…";
  try {
    const params = formParams();
    const r = await fetch("/api/assess", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify(params),
    });
    if (!r.ok) throw new Error("API lỗi " + r.status);
    const a = await r.json();
    renderResults(a);
    st.textContent = "Hoàn tất.";
    if (window.__globe) await window.__globe.refresh(params);
  } catch (e) {
    st.textContent = "Lỗi: " + e.message;
  } finally {
    btn.disabled = false; btn.textContent = "▶ Chạy đánh giá";
  }
});

function renderResults(a) {
  const el = $("results");
  const c = a.constellation, cov = a.coverage, p = a.pfd, e = a.epfd, co = a.coordination;
  let h = `<div class="card"><h3>Chòm sao ${esc(a.name)}</h3>
    <table>
    <tr><td>Độ cao / nghiêng</td><td>${c.alt_km.toFixed(0)} km / ${c.inc_deg.toFixed(1)}°</td></tr>
    <tr><td>Vệ tinh / mặt phẳng</td><td>${c.n_sats} / ${c.n_planes} (${c.kind})</td></tr>
    <tr><td>Chu kỳ / bán kính phủ</td><td>${c.period_min.toFixed(1)} phút / ${c.footprint_km.toFixed(0)} km</td></tr>
    <tr><td>Băng tần / EIRP</td><td>${a.downlink.band_ghz} GHz / ${a.downlink.eirp_dbw_per_mhz} dBW/MHz</td></tr>
    </table></div>`;

  h += `<div class="card"><h3>Phủ sóng Việt Nam</h3><table>
    ${cov.points.map(pt => `<tr><td>${esc(pt.name)}</td>
      <td>${fmtPct(pt.fraction_covered)}</td>
      <td>${pt.mean_sats_visible.toFixed(1)} VT</td>
      <td>trống ${pt.max_gap_min.toFixed(1)}′</td></tr>`).join("")}
    </table><p class="hint">Trung bình lưới: ${fmtPct(cov.grid_summary.mean_fraction)},
    thấp nhất: ${fmtPct(cov.grid_summary.min_fraction)} (góc ngẩng ≥ ${cov.min_elev_deg}°).</p></div>`;

  h += `<div class="card"><h3>Kiểm tra PFD (Article 21)</h3>
    ${badge(p.compliant ? "ĐẠT" : "KHÔNG ĐẠT", p.compliant ? "ok" : "bad")}
    <table>
    <tr><td>PFD tại điểm chiếu</td><td>${p.pfd.toFixed(1)} ${esc(p.unit)}</td></tr>
    <tr><td>Giới hạn Table 21-4</td><td>${p.limit.toFixed(1)} ${esc(p.unit)}</td></tr>
    <tr><td>Biên</td><td>${p.margin_db.toFixed(1)} dB</td></tr>
    </table></div>`;

  const pct = Object.entries(e.percentiles).map(([k, v]) =>
    `<tr><td>${esc(k)}</td><td>${v.toFixed(1)}</td></tr>`).join("");
  h += `<div class="card"><h3>Sàng lọc EPFD (Article 22)</h3>
    ${badge(e.screening_pass ? "ĐẠT" : "KHÔNG ĐẠT", e.screening_pass ? "ok" : "bad")}
    <table><tr><th>Phân vị</th><th>dBW/m²/40kHz</th></tr>${pct}</table>
    <p class="hint">Biên so với điểm không-vượt-quá Table 22-1A: ${e.margin_vs_anchor_db.toFixed(1)} dB.</p></div>`;

  h += `<div class="card"><h3>Phối hợp quốc tế</h3>
    ${badge(co.coordination_likely_required ? "CẦN PHỐI HỢP" : "CHƯA THẤY DẤU HIỆU",
            co.coordination_likely_required ? "warn" : "ok")}
    ${co.reasons.map(r => `<p class="hint">• ${esc(r)}</p>`).join("")}
    <p class="hint">Cung Appendix 5: ±${co.coordination_arc_deg}°.</p></div>`;

  if (a.milestones) {
    const cls = {DAT: "ok", TRE_HAN: "bad", CHUA_DEN_HAN: "warn"};
    h += `<div class="card"><h3>Mốc triển khai (Res 35)</h3><table>
      <tr><th>Mốc</th><th>Hạn</th><th>Cần</th><th>Đã có</th><th></th></tr>
      ${a.milestones.map(m => `<tr><td>${m.percent}%</td><td>${esc(m.due)}</td>
        <td>${m.required_n}</td><td>${m.deployed_n}</td>
        <td>${badge(m.status, cls[m.status] || "")}</td></tr>`).join("")}
      </table></div>`;
    if (a.warehousing) {
      const w = a.warehousing;
      const wc = {CAO: "bad", TRUNG_BINH: "warn", THAP: "ok"}[w.risk];
      h += `<div class="card"><h3>Chống “xí phần”</h3>
        ${badge(w.risk, wc)}<p class="hint">${esc(w.message)}
        (${w.deployed}/${w.filed}).</p></div>`;
    }
  }
  el.innerHTML = h;
}

function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/* ---------------- tab 1: 3D globe ---------------- */
async function initGlobe() {
  let THREE, OrbitControls;
  try {
    THREE = await import("three");
    ({OrbitControls} = await import("three/addons/controls/OrbitControls.js"));
  } catch (err) {
    const e = $("globe-error");
    e.textContent = "Không tải được thư viện 3D (cần kết nối mạng tới CDN). Các chức năng tính toán vẫn dùng được.";
    e.classList.remove("hidden");
    return;
  }

  const R_E = 6371.0, R = 1;
  const ecefToScene = (x, y, z) =>
    new THREE.Vector3(x / R_E * R, z / R_E * R, -y / R_E * R);
  const llToScene = (lat, lon, altKm) => {
    const r = R * (1 + altKm / R_E);
    const phi = (90 - lat) * Math.PI / 180, theta = (lon + 180) * Math.PI / 180;
    return new THREE.Vector3(
      -r * Math.sin(phi) * Math.cos(theta), r * Math.cos(phi), r * Math.sin(phi) * Math.sin(theta));
  };

  const container = $("viewport");
  const renderer = new THREE.WebGLRenderer({antialias: true});
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  container.appendChild(renderer.domElement);
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x05080f);
  const camera = new THREE.PerspectiveCamera(45, 1, 0.01, 100);
  camera.position.set(0, 1.2, 3.2);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true; controls.minDistance = 1.4; controls.maxDistance = 30;
  scene.add(new THREE.AmbientLight(0xffffff, 0.9));
  const sun = new THREE.DirectionalLight(0xffffff, 1.6);
  sun.position.set(5, 2, 3); scene.add(sun);

  // Trái Đất
  const earthMat = new THREE.MeshPhongMaterial({color: 0x1c3d6e});
  const earth = new THREE.Mesh(new THREE.SphereGeometry(R, 48, 32), earthMat);
  scene.add(earth);
  new THREE.TextureLoader().load(
    "https://cdn.jsdelivr.net/npm/three-globe/example/img/earth-blue-marble.jpg",
    t => { earthMat.map = t; earthMat.color.set(0xffffff); earthMat.needsUpdate = true; },
    undefined, () => {});
  const wire = new THREE.LineSegments(
    new THREE.WireframeGeometry(new THREE.SphereGeometry(R * 1.002, 24, 16)),
    new THREE.LineBasicMaterial({color: 0x3b82f6, transparent: true, opacity: 0.07}));
  scene.add(wire);
  const glow = new THREE.Mesh(new THREE.SphereGeometry(R * 1.06, 48, 32),
    new THREE.MeshBasicMaterial({color: 0x3a7bd5, transparent: true, opacity: 0.08, side: THREE.BackSide}));
  scene.add(glow);

  // sao nền
  {
    const n = 800, pos = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      const v = new THREE.Vector3().randomDirection().multiplyScalar(40);
      pos.set([v.x, v.y, v.z], i * 3);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    scene.add(new THREE.Points(g, new THREE.PointsMaterial({color: 0x8899bb, size: 0.15})));
  }

  const satGroup = new THREE.Group(), orbitGroup = new THREE.Group(),
        covGroup = new THREE.Group(), markGroup = new THREE.Group();
  scene.add(satGroup, orbitGroup, covGroup, markGroup);

  // điểm tham chiếu VN + vệ tinh GSO + vành GEO
  const VN_PTS = [[21.0285, 105.8542, "Hà Nội"], [16.0544, 108.2022, "Đà Nẵng"], [10.8231, 106.6297, "TP.HCM"]];
  VN_PTS.forEach(([la, lo]) => {
    const m = new THREE.Mesh(new THREE.SphereGeometry(0.012, 12, 12),
      new THREE.MeshBasicMaterial({color: 0xff9f1c}));
    m.position.copy(llToScene(la, lo, 10)); markGroup.add(m);
  });
  let gsoMarker = null, geoRing = null;
  function setGSO(lon) {
    if (gsoMarker) { markGroup.remove(gsoMarker); scene.remove(geoRing); }
    const Rg = 42164 / R_E;
    gsoMarker = new THREE.Mesh(new THREE.SphereGeometry(0.02, 12, 12),
      new THREE.MeshBasicMaterial({color: 0xc26bff}));
    gsoMarker.position.copy(ecefToScene(Rg * R_E * Math.cos(lon * Math.PI / 180),
                                        Rg * R_E * Math.sin(lon * Math.PI / 180), 0));
    markGroup.add(gsoMarker);
    const pts = [];
    for (let i = 0; i <= 128; i++) {
      const a = i / 128 * Math.PI * 2;
      pts.push(new THREE.Vector3(Rg * Math.cos(a), 0, -Rg * Math.sin(a)));
    }
    geoRing = new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts),
      new THREE.LineBasicMaterial({color: 0xc26bff, transparent: true, opacity: 0.25}));
    scene.add(geoRing);
  }

  // trạng thái mô phỏng
  const sim = {tracks: [], period: 6000, nPlanes: 6, nSats: 0,
               playing: true, speed: 120, t: 0, satPoints: null};

  function fracColor(f, out) {
    if (f < 0.5) out.setRGB(0.9, 0.2 + 1.4 * f, 0.2);
    else out.setRGB(0.9 - 1.4 * (f - 0.5), 0.9, 0.2);
    return out;
  }

  async function refresh(params) {
    // vệ tinh + quỹ đạo
    const tr = await (await fetch("/api/tracks", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({...params, samples: 90}),
    })).json();
    sim.tracks = tr.tracks.map(sat => sat.map(p => ecefToScene(p[0], p[1], p[2])));
    sim.period = tr.period_s; sim.nPlanes = tr.n_planes; sim.nSats = tr.n_sats;
    satGroup.clear();
    const pos = new Float32Array(sim.nSats * 3);
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    sim.satPoints = new THREE.Points(g, new THREE.PointsMaterial(
      {color: 0x33d1ff, size: 0.022, transparent: true, opacity: 0.95}));
    satGroup.add(sim.satPoints);
    orbitGroup.clear();
    const perPlane = Math.max(1, Math.round(sim.nSats / sim.nPlanes));
    for (let p = 0; p < sim.nPlanes; p++) {
      const idx = Math.min(sim.nSats - 1, p * perPlane);
      const line = new THREE.LineLoop(
        new THREE.BufferGeometry().setFromPoints(sim.tracks[idx]),
        new THREE.LineBasicMaterial({color: 0x2a6fd6, transparent: true, opacity: 0.3}));
      orbitGroup.add(line);
    }
    // phủ sóng
    const cm = await (await fetch("/api/coverage-map", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify(params),
    })).json();
    covGroup.clear();
    const cells = cm.cells.filter(c => c.fraction > 0.02);
    const cp = new Float32Array(cells.length * 3), cc = new Float32Array(cells.length * 3);
    const col = new THREE.Color();
    cells.forEach((c, i) => {
      const v = llToScene(c.lat, c.lon, 8);
      cp.set([v.x, v.y, v.z], i * 3);
      fracColor(c.fraction, col); cc.set([col.r, col.g, col.b], i * 3);
    });
    const cg = new THREE.BufferGeometry();
    cg.setAttribute("position", new THREE.BufferAttribute(cp, 3));
    cg.setAttribute("color", new THREE.BufferAttribute(cc, 3));
    covGroup.add(new THREE.Points(cg, new THREE.PointsMaterial(
      {size: 0.02, vertexColors: true, transparent: true, opacity: 0.85})));
    setGSO(params.gso_lon || 105.5);
    applyLayers();
  }

  function applyLayers() {
    satGroup.visible = $("layer-sats").checked;
    orbitGroup.visible = $("layer-orbits").checked;
    covGroup.visible = $("layer-cov").checked;
  }
  ["layer-sats", "layer-orbits", "layer-cov"].forEach(id =>
    $(id).addEventListener("change", applyLayers));

  $("btn-play").addEventListener("click", () => {
    sim.playing = !sim.playing;
    $("btn-play").textContent = sim.playing ? "⏸ Tạm dừng" : "▶ Chạy";
  });
  $("speed").addEventListener("input", () => {
    sim.speed = parseInt($("speed").value, 10);
    $("speed-val").textContent = sim.speed + "×";
  });

  function resize() {
    const w = container.clientWidth, h = container.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h); camera.aspect = w / h; camera.updateProjectionMatrix();
  }
  window.addEventListener("resize", resize);

  const clock = new THREE.Clock();
  function fmtT(s) {
    s = Math.floor(s);
    const h = String(Math.floor(s / 3600)).padStart(2, "0"),
          m = String(Math.floor(s / 60) % 60).padStart(2, "0"),
          ss = String(s % 60).padStart(2, "0");
    return `T+${h}:${m}:${ss}`;
  }
  function animate() {
    requestAnimationFrame(animate);
    const dt = Math.min(clock.getDelta(), 0.1);
    if (sim.playing && sim.satPoints) {
      sim.t += dt * sim.speed;
      const N = sim.tracks[0].length;
      const fidx = (sim.t % sim.period) / sim.period * N;
      const i0 = Math.floor(fidx) % N, i1 = (i0 + 1) % N, fr = fidx - Math.floor(fidx);
      const attr = sim.satPoints.geometry.attributes.position;
      for (let s = 0; s < sim.nSats; s++) {
        const a = sim.tracks[s][i0], b = sim.tracks[s][i1];
        attr.setXYZ(s, a.x + (b.x - a.x) * fr, a.y + (b.y - a.y) * fr, a.z + (b.z - a.z) * fr);
      }
      attr.needsUpdate = true;
      $("sim-clock").textContent = fmtT(sim.t);
    }
    controls.update();
    renderer.render(scene, camera);
  }

  resize(); animate();
  const globe = {refresh, resize};
  window.__globe = globe;
  await refresh(formParams());  // tải mặc định lúc mở trang
}

/* ---------------- tab 2: tham luận & tài liệu ---------------- */
const EXT_ICON = {".pdf": "📕", ".doc": "📘", ".docx": "📘", ".xls": "📗",
                  ".xlsx": "📗", ".ppt": "📙", ".pptx": "📙"};
function fmtSize(b) {
  if (b < 1024) return b + " B";
  if (b < 1048576) return (b / 1024).toFixed(1) + " KB";
  return (b / 1048576).toFixed(1) + " MB";
}

async function loadDocs() {
  const body = $("docs-body");
  try {
    const r = await fetch("/api/docs");
    const {documents} = await r.json();
    $("doc-count").textContent = documents.length;
    if (!documents.length) {
      body.innerHTML = `<tr><td colspan="6" class="hint">Chưa có tài liệu nào. Hãy tải lên tham luận đầu tiên.</td></tr>`;
      return;
    }
    body.innerHTML = documents.map(d => `<tr>
      <td class="ficon">${EXT_ICON[d.ext] || "📄"}</td>
      <td><b>${esc(d.title)}</b>${d.description ? `<div class="desc">${esc(d.description)}</div>` : ""}</td>
      <td>${esc(d.filename)}</td>
      <td>${fmtSize(d.size_bytes)}</td>
      <td>${esc(d.uploaded_at.slice(0, 16).replace("T", " "))}</td>
      <td><div class="rowbtns">
        <a class="btn small" href="/api/docs/${d.id}/download">⬇ Tải</a>
        <button class="btn small danger" data-del="${d.id}">🗑 Xóa</button>
      </div></td></tr>`).join("");
    body.querySelectorAll("[data-del]").forEach(b =>
      b.addEventListener("click", async () => {
        if (!confirm("Xóa tài liệu này?")) return;
        await fetch("/api/docs/" + b.dataset.del, {method: "DELETE"});
        loadDocs();
      }));
  } catch (e) {
    body.innerHTML = `<tr><td colspan="6" class="hint">Lỗi tải danh sách: ${esc(e.message)}</td></tr>`;
  }
}

$("btn-upload").addEventListener("click", async () => {
  const st = $("upload-status"), btn = $("btn-upload");
  const file = $("d_file").files[0];
  if (!file) { st.textContent = "Hãy chọn file đính kèm."; return; }
  if (!$("d_title").value.trim()) { st.textContent = "Hãy nhập tiêu đề."; return; }
  btn.disabled = true; st.textContent = "Đang tải lên…";
  try {
    const fd = new FormData();
    fd.append("title", $("d_title").value.trim());
    fd.append("description", $("d_desc").value.trim());
    fd.append("file", file);
    const r = await fetch("/api/docs", {method: "POST", body: fd});
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || ("Lỗi " + r.status));
    }
    st.textContent = "Tải lên thành công.";
    $("d_title").value = ""; $("d_desc").value = ""; $("d_file").value = "";
    loadDocs();
  } catch (e) {
    st.textContent = "Lỗi: " + e.message;
  } finally {
    btn.disabled = false;
  }
});

/* ---------------- khởi động ---------------- */
loadDocs();
initGlobe();
