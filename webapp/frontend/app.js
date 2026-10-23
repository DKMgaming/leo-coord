/* leo_coord web app — tab 1: chức năng + bản đồ 3D (CesiumJS); tab 2: tham luận & tài liệu */
"use strict";

/* ---------------- tab switching ---------------- */
document.querySelectorAll(".tab").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tabpage").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(btn.dataset.tab).classList.add("active");
    if (btn.dataset.tab === "tab1" && window.__globe) window.__globe.resize();
    if (btn.dataset.tab === "tab3") loadDb();
  });
});

/* ---------------- helpers ---------------- */
const $ = id => document.getElementById(id);
const fmtPct = v => (v * 100).toFixed(1) + "%";
function badge(text, cls) { return `<span class="badge ${cls}">${text}</span>`; }
function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

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

/* ---------------- tab 1: bản đồ số 3D (CesiumJS) ---------------- */
async function initGlobe() {
  if (typeof Cesium === "undefined") {
    const e = $("globe-error");
    e.textContent = "Không tải được thư viện CesiumJS (cần kết nối mạng tới CDN). Các chức năng tính toán vẫn dùng được.";
    e.classList.remove("hidden");
    return;
  }

  // địa hình thật (ArcGIS World Elevation) — rớt về ellipsoid nếu không có lớp này.
  // Cesium >= 1.104: provider này phải tạo bằng fromUrl() (bất đồng bộ);
  // khởi tạo trực tiếp bằng new khiến địa cầu không hiển thị gì (lỗi đã sửa).
  let terrainProvider;
  try {
    terrainProvider = await Cesium.ArcGISTiledElevationTerrainProvider.fromUrl(
      "https://elevation3d.arcgis.com/arcgis/rest/services/WorldElevation3D/Terrain3D/ImageServer");
  } catch (err) {
    terrainProvider = new Cesium.EllipsoidTerrainProvider();
  }

  const viewer = new Cesium.Viewer("viewport", {
    imageryProvider: false,
    baseLayerPicker: false,
    geocoder: false,
    timeline: false,
    animation: false,
    infoBox: false,
    selectionIndicator: false,
    navigationHelpButton: false,
    terrainProvider,
  });

  // Lớp ảnh nền chuyển đổi được (giống các lớp GIS của Atlas)
  const BASEMAPS = {
    esri: () => new Cesium.UrlTemplateImageryProvider({
      url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      maximumLevel: 18, credit: "Esri World Imagery" }),
    osm: () => new Cesium.UrlTemplateImageryProvider({
      url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
      maximumLevel: 19, credit: "© OpenStreetMap contributors" }),
    dark: () => new Cesium.UrlTemplateImageryProvider({
      url: "https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
      maximumLevel: 18, credit: "© CARTO · © OpenStreetMap contributors" }),
  };
  const imageryLayers = viewer.imageryLayers;
  let baseLayer = imageryLayers.addImageryProvider(BASEMAPS.esri());
  $("basemap").addEventListener("change", ev => {
    imageryLayers.remove(baseLayer, true);
    baseLayer = imageryLayers.addImageryProvider(BASEMAPS[ev.target.value]());
  });

  viewer.camera.setView({
    destination: Cesium.Cartesian3.fromDegrees(105.8, 15.5, 9000000),
    orientation: { heading: 0.0, pitch: -Math.PI / 2, roll: 0.0 },
  });

  const sim = { tracks: [], period: 6000, nPlanes: 6, nSats: 0,
                playing: true, speed: 120, t: 0,
                satPrims: [], scratch: [] };
  let satPts = null, covPts = null;
  const orbitEntities = [];
  const ecefToCart = p => new Cesium.Cartesian3(p[0] * 1000, p[1] * 1000, p[2] * 1000);
  const fracColor = f => new Cesium.Color(0.9 - 0.7 * f, 0.2 + 0.7 * f, 0.2, 0.9);

  // Điểm tham chiếu Việt Nam (khớp configs/leo_coord.yaml)
  [["Hà Nội", 21.0285, 105.8542], ["Việt Trì", 21.3283, 105.3566],
   ["KS vệ tinh Bắc Ninh", 21.136356, 106.074508],
   ["Đà Nẵng", 16.0544, 108.2022],
   ["TP.HCM", 10.8231, 106.6297]].forEach(([name, la, lo]) => {
    viewer.entities.add({
      name,
      position: Cesium.Cartesian3.fromDegrees(lo, la, 5000),
      point: { pixelSize: 10, color: Cesium.Color.ORANGE,
               outlineColor: Cesium.Color.BLACK, outlineWidth: 1 },
      label: { text: name, font: "13px sans-serif", fillColor: Cesium.Color.WHITE,
               style: Cesium.LabelStyle.FILL_AND_OUTLINE,
               outlineColor: Cesium.Color.BLACK,
               verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
               pixelOffset: new Cesium.Cartesian2(0, -14),
               disableDepthTestDistance: Number.POSITIVE_INFINITY },
    });
  });

  // Vệ tinh GSO + vành GEO
  let gsoEntity = null, geoEntity = null;
  function setGSO(lon) {
    if (gsoEntity) { viewer.entities.remove(gsoEntity); viewer.entities.remove(geoEntity); }
    gsoEntity = viewer.entities.add({
      name: "Vệ tinh GSO",
      position: Cesium.Cartesian3.fromDegrees(lon, 0, 35793000),
      point: { pixelSize: 12, color: Cesium.Color.VIOLET },
      label: { text: "GSO " + lon.toFixed(1) + "°E", font: "12px sans-serif",
               fillColor: Cesium.Color.VIOLET,
               verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
               pixelOffset: new Cesium.Cartesian2(0, -14) },
    });
    const Rg = 42164 * 1000, ring = [];
    for (let i = 0; i <= 128; i++) {
      const a = i / 128 * Math.PI * 2;
      ring.push(new Cesium.Cartesian3(Rg * Math.cos(a), Rg * Math.sin(a), 0));
    }
    geoEntity = viewer.entities.add({
      polyline: { positions: ring, width: 1,
                  material: Cesium.Color.VIOLET.withAlpha(0.3) },
    });
  }

  async function refresh(params) {
    const tr = await (await fetch("/api/tracks", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ ...params, samples: 90 }),
    })).json();
    sim.period = tr.period_s; sim.nPlanes = tr.n_planes; sim.nSats = tr.n_sats;
    sim.tracks = tr.tracks.map(sat => sat.map(ecefToCart));

    if (satPts) viewer.scene.primitives.remove(satPts);
    satPts = viewer.scene.primitives.add(new Cesium.PointPrimitiveCollection());
    sim.satPrims = []; sim.scratch = [];
    for (let s = 0; s < sim.nSats; s++) {
      sim.scratch.push(new Cesium.Cartesian3());
      sim.satPrims.push(satPts.add({
        position: sim.tracks[s][0].clone(),
        color: Cesium.Color.CYAN, pixelSize: 6,
      }));
    }
    orbitEntities.forEach(e => viewer.entities.remove(e));
    orbitEntities.length = 0;
    const perPlane = Math.max(1, Math.round(sim.nSats / sim.nPlanes));
    for (let p = 0; p < sim.nPlanes; p++) {
      const idx = Math.min(sim.nSats - 1, p * perPlane);
      orbitEntities.push(viewer.entities.add({
        polyline: { positions: sim.tracks[idx], width: 1, loop: true,
                    material: Cesium.Color.DODGERBLUE.withAlpha(0.35) },
      }));
    }

    const cm = await (await fetch("/api/coverage-map", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify(params),
    })).json();
    if (covPts) viewer.scene.primitives.remove(covPts);
    covPts = viewer.scene.primitives.add(new Cesium.PointPrimitiveCollection());
    cm.cells.forEach(c => {
      if (c.fraction < 0.02) return;
      covPts.add({
        position: Cesium.Cartesian3.fromDegrees(c.lon, c.lat, 8000),
        color: fracColor(c.fraction), pixelSize: 5,
      });
    });

    setGSO(params.gso_lon || 105.5);
    applyLayers();
  }

  function applyLayers() {
    if (satPts) satPts.show = $("layer-sats").checked;
    orbitEntities.forEach(e => { e.show = $("layer-orbits").checked; });
    if (covPts) covPts.show = $("layer-cov").checked;
  }
  ["layer-sats", "layer-orbits", "layer-cov"].forEach(id =>
    $(id).addEventListener("change", applyLayers));

  /* Click vào bản đồ: tra cứu vệ tinh khả kiến tại điểm đó */
  const pickBox = $("pick-info");
  let pickEntity = null;
  viewer.screenSpaceEventHandler.setInputAction(async click => {
    const cart = viewer.camera.pickEllipsoid(click.position, viewer.scene.globe.ellipsoid);
    if (!cart) return;
    const cc = viewer.scene.globe.ellipsoid.cartesianToCartographic(cart);
    const lat = Cesium.Math.toDegrees(cc.latitude);
    const lon = Cesium.Math.toDegrees(cc.longitude);
    if (pickEntity) viewer.entities.remove(pickEntity);
    pickEntity = viewer.entities.add({
      position: Cesium.Cartesian3.fromDegrees(lon, lat, 5000),
      point: { pixelSize: 12, color: Cesium.Color.YELLOW,
               outlineColor: Cesium.Color.BLACK, outlineWidth: 2 },
    });
    pickBox.classList.remove("hidden");
    pickBox.innerHTML = `<b>Điểm (${lat.toFixed(2)}°, ${lon.toFixed(2)}°)</b><br>
      <span class="hint">Đang tra cứu…</span>`;
    try {
      const r = await fetch("/api/visible-sats", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ ...formParams(), lat, lon, t_s: sim.t }),
      });
      const d = await r.json();
      const rows = d.satellites.map(s =>
        `<tr><td>${esc(s.name)}</td><td>${s.elevation_deg.toFixed(1)}°</td>
         <td>${s.azimuth_deg.toFixed(0)}°</td><td>${s.range_km.toFixed(0)} km</td></tr>`).join("");
      pickBox.innerHTML = `<b>Điểm (${lat.toFixed(2)}°, ${lon.toFixed(2)}°)</b>
        <button class="btn small" id="pick-close">✕</button><br>
        <span>${d.n_visible} vệ tinh khả kiến (ngẩng ≥ ${d.min_elev_deg}°):</span>
        <table><tr><th>Vệ tinh</th><th>Ngẩng</th><th>Phương vị</th><th>Cự ly</th></tr>${
          rows || '<tr><td colspan="4" class="hint">Không có vệ tinh nào</td></tr>'}</table>`;
      $("pick-close").addEventListener("click", () => {
        pickBox.classList.add("hidden");
        if (pickEntity) { viewer.entities.remove(pickEntity); pickEntity = null; }
      });
    } catch (err) {
      pickBox.innerHTML = `<b>Lỗi tra cứu:</b> ${esc(err.message)}`;
    }
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

  /* Animation */
  $("btn-play").addEventListener("click", () => {
    sim.playing = !sim.playing;
    $("btn-play").textContent = sim.playing ? "⏸ Tạm dừng" : "▶ Chạy";
  });
  $("speed").addEventListener("input", () => {
    sim.speed = parseInt($("speed").value, 10);
    $("speed-val").textContent = sim.speed + "×";
  });
  function fmtT(s) {
    s = Math.floor(s);
    const h = String(Math.floor(s / 3600)).padStart(2, "0"),
          m = String(Math.floor(s / 60) % 60).padStart(2, "0"),
          ss = String(s % 60).padStart(2, "0");
    return `T+${h}:${m}:${ss}`;
  }
  let last = performance.now();
  function animate(now) {
    requestAnimationFrame(animate);
    const dt = Math.min((now - last) / 1000, 0.2); last = now;
    if (sim.playing && sim.satPrims.length) {
      sim.t += dt * sim.speed;
      const N = sim.tracks[0].length;
      const fidx = (sim.t % sim.period) / sim.period * N;
      const i0 = Math.floor(fidx) % N, i1 = (i0 + 1) % N, fr = fidx - Math.floor(fidx);
      for (let s = 0; s < sim.nSats; s++) {
        Cesium.Cartesian3.lerp(sim.tracks[s][i0], sim.tracks[s][i1], fr, sim.scratch[s]);
        sim.satPrims[s].position = sim.scratch[s];
      }
      $("sim-clock").textContent = fmtT(sim.t);
    }
  }

  window.__globe = { refresh, resize: () => viewer.resize() };
  await refresh(formParams());
  requestAnimationFrame(animate);
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

/* ---------------- tab 3: CSDL phối hợp quốc gia ---------------- */
const DB_ST_CLS = {DAT: "ok", TRE_HAN: "bad", CHUA_DEN_HAN: "warn"};

async function postDb(url, payload) {
  const r = await fetch(url, {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail || ("Lỗi " + r.status));
  }
  return r.json();
}

function fillNetSelects(names) {
  ["dep_net", "case_net", "cc_net"].forEach(id => {
    const sel = $(id), cur = sel.value;
    sel.innerHTML = names.map(n =>
      `<option value="${esc(n)}">${esc(n)}</option>`).join("");
    if (names.includes(cur)) sel.value = cur;
  });
}

function latestDeployed(deployments, name) {
  const rows = deployments.filter(x => x.network_name === name);
  return rows.length ? rows[0].n_deployed : "—";  // đã xếp mới nhất trước
}

async function loadDb() {
  try {
    const [f, d, c, m, x] = await Promise.all([
      fetch("/api/db/filings").then(r => r.json()),
      fetch("/api/db/deployments").then(r => r.json()),
      fetch("/api/db/cases").then(r => r.json()),
      fetch("/api/db/milestones").then(r => r.json()),
      fetch("/api/db/crosschecks").then(r => r.json()),
    ]);
    renderDb(f.filings, d.deployments, c.cases, m.networks, x.crosschecks);
  } catch (e) {
    $("filings-body").innerHTML =
      `<tr><td colspan="8" class="hint">Lỗi tải CSDL: ${esc(e.message)}</td></tr>`;
  }
}

function renderDb(filings, deployments, cases, networks, crosschecks) {
  $("filing-count").textContent = filings.length;
  fillNetSelects(filings.map(f => f.network_name));
  $("filings-body").innerHTML = filings.length ? filings.map(f => {
    const sub = [f.sns_id && "SNS " + f.sns_id, f.notice_type,
                 f.ific_no && "IFIC " + f.ific_no].filter(Boolean).join(" · ");
    return `<tr>
    <td><b>${esc(f.network_name)}</b>${sub ? `<div class="desc">${esc(sub)}</div>` : ""}</td>
    <td>${esc(f.administration)}</td>
    <td>${esc(f.operator || "")}</td><td>${esc(f.bands || "")}</td>
    <td>${f.n_sats_filed}</td><td>${latestDeployed(deployments, f.network_name)}</td>
    <td>${esc(f.status || "")}</td><td>${esc(f.biu_deadline || "—")}</td></tr>`;
  }).join("")
    : `<tr><td colspan="8" class="hint">Chưa có hồ sơ nào.</td></tr>`;

  const AGREE = {KHOP: ["KHỚP", "ok"], LECH: ["LỆCH", "bad"],
                 CHUA_RO: ["CHƯA RÕ", "warn"]};
  $("cc-body").innerHTML = crosschecks.length ? crosschecks.map(x => {
    const [txt, cls] = AGREE[x.agreement] || ["?", ""];
    return `<tr><td><b>${esc(x.network_name)}</b>
      <div class="desc">↔ ${esc(x.other_system)}</div></td>
      <td>${esc(x.our_result || "")}<div class="desc">${esc(x.official_source || "")}</div></td>
      <td>${esc(x.official_result || "")}</td>
      <td>${badge(txt, cls)}</td><td>${esc(x.checked_date || "")}</td></tr>`;
  }).join("")
    : `<tr><td colspan="5" class="hint">Chưa có bản ghi đối chứng nào.</td></tr>`;

  $("deployments-body").innerHTML = deployments.length ? deployments.map(d => `<tr>
    <td>${esc(d.network_name)}</td><td>${esc(d.report_date)}</td>
    <td>${d.n_deployed}</td><td>${esc(d.source || "")}</td></tr>`).join("")
    : `<tr><td colspan="4" class="hint">Chưa có báo cáo triển khai nào.</td></tr>`;

  $("cases-body").innerHTML = cases.length ? cases.map(c => `<tr>
    <td>${esc(c.network_name)}</td><td>${esc(c.other_system)}</td>
    <td>${esc(c.band || "")}</td><td>${esc(c.trigger || "")}</td>
    <td>${esc(c.status || "")}</td><td>${esc(c.notes || "")}</td></tr>`).join("")
    : `<tr><td colspan="6" class="hint">Chưa có vụ việc phối hợp nào.</td></tr>`;

  $("db-milestones").innerHTML = networks.length ? networks.map(n => `
    <div class="card"><h3>${esc(n.network_name)} — trạng thái mốc Res 35</h3>
    <table class="docs">
    <tr><th>Mốc</th><th>Hạn</th><th>Cần</th><th>Đã có</th><th></th></tr>
    ${n.milestones.map(m => `<tr><td>${m.percent}%</td><td>${esc(m.due)}</td>
      <td>${m.required_n}</td><td>${m.deployed_n}</td>
      <td>${badge(m.status, DB_ST_CLS[m.status] || "")}</td></tr>`).join("")}
    </table></div>`).join("")
    : `<div class="card"><p class="hint">Chưa có hồ sơ nào có hạn BIU để đánh giá mốc Res 35.</p></div>`;
}

$("btn-filing").addEventListener("click", async () => {
  const st = $("filing-status");
  const num = id => { const v = $(id).value; return v === "" ? null : parseFloat(v); };
  try {
    await postDb("/api/db/filings", {
      network_name: $("n_name").value.trim(),
      administration: $("n_admin").value.trim(),
      operator: $("n_operator").value.trim(),
      bands: $("n_bands").value.trim(),
      n_sats_filed: parseInt($("n_nsats").value, 10),
      alt_km: num("n_alt"), inc_deg: num("n_inc"),
      status: $("n_status").value,
      api_date: $("n_apidate").value || null,
      biu_deadline: $("n_biu").value || null,
      sns_id: $("n_sns").value.trim(),
      notice_type: $("n_ntype").value.trim(),
      ific_no: $("n_ific").value.trim(),
      receipt_date: $("n_rcv").value || null,
      notes: $("n_notes").value.trim(),
    });
    st.textContent = "Đã thêm hồ sơ.";
    loadDb();
  } catch (e) { st.textContent = "Lỗi: " + e.message; }
});

$("btn-dep").addEventListener("click", async () => {
  const st = $("dep-status");
  try {
    await postDb("/api/db/deployments", {
      network_name: $("dep_net").value,
      report_date: $("dep_date").value,
      n_deployed: parseInt($("dep_n").value, 10),
      source: $("dep_source").value.trim(),
    });
    st.textContent = "Đã ghi nhận báo cáo triển khai.";
    loadDb();
  } catch (e) { st.textContent = "Lỗi: " + e.message; }
});

$("btn-case").addEventListener("click", async () => {
  const st = $("case-status");
  try {
    await postDb("/api/db/cases", {
      network_name: $("case_net").value,
      other_system: $("case_other").value.trim(),
      band: $("case_band").value.trim(),
      trigger: $("case_trigger").value.trim(),
      status: $("case_st").value.trim() || "MO",
      notes: $("case_notes").value.trim(),
    });
    st.textContent = "Đã thêm vụ việc phối hợp.";
    loadDb();
  } catch (e) { st.textContent = "Lỗi: " + e.message; }
});

$("btn-import").addEventListener("click", async () => {
  const st = $("import-status");
  const file = $("imp_file").files[0];
  if (!file) { st.textContent = "Hãy chọn file CSV."; return; }
  st.textContent = "Đang nhập…";
  try {
    const fd = new FormData();
    fd.append("file", file);
    const r = await fetch("/api/db/import", {method: "POST", body: fd});
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || ("Lỗi " + r.status));
    }
    const d = await r.json();
    st.textContent = `Đã nhập mới ${d.stats.added} hồ sơ; bỏ qua ` +
      `${d.stats.skipped_existing} (đã có), ${d.report.n_skipped_no_name} (thiếu tên). ` +
      `Cột khớp: ${d.report.fields_mapped.join(", ") || "không có"}.`;
    loadDb();
  } catch (e) { st.textContent = "Lỗi: " + e.message; }
});

$("btn-cc").addEventListener("click", async () => {
  const st = $("cc-status");
  try {
    await postDb("/api/db/crosschecks", {
      network_name: $("cc_net").value,
      other_system: $("cc_other").value.trim(),
      our_result: $("cc_our").value.trim(),
      official_source: $("cc_source").value.trim(),
      official_result: $("cc_official").value.trim(),
      agreement: $("cc_agree").value,
      checked_date: $("cc_date").value || null,
      checker: $("cc_checker").value.trim(),
      notes: $("cc_notes").value.trim(),
    });
    st.textContent = "Đã ghi nhận đối chứng.";
    loadDb();
  } catch (e) { st.textContent = "Lỗi: " + e.message; }
});

/* ---------------- khởi động ---------------- */
$("dep_date").value = new Date().toISOString().slice(0, 10);
$("cc_date").value = new Date().toISOString().slice(0, 10);
loadDocs();
loadDb();
initGlobe();
