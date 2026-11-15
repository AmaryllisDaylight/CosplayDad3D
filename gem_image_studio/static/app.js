// app.js — CosplayDad3D Glass Studio Client Logic
const state = {
  currentFolder: "",
  parentFolder: null,
  images: [],
  filteredImages: [],
  subdirs: [],
  bookmarks: [],
  mode: "single", // 'single' | 'multiview'
  selectedPaths: new Set(),
  fourViewSlots: {
    front: null,
    back: null,
    left: null,
    right: null,
  },
  activeTargetSlot: "front",
  inspectorIndex: -1,
  zoom: 1,
  panX: 0,
  panY: 0,
  isPanning: false,
  panStartX: 0,
  panStartY: 0,
};

// DOM Elements
const els = {
  pathInput: document.getElementById("folder-path-input"),
  btnGoPath: document.getElementById("btn-go-path"),
  btnUpDir: document.getElementById("btn-up-dir"),
  btnNativeBrowse: document.getElementById("btn-native-browse"),
  btnOpenExplorer: document.getElementById("btn-open-explorer"),
  balancePill: document.getElementById("tripo-balance-pill"),
  balanceText: document.getElementById("balance-text"),
  bookmarksList: document.getElementById("bookmarks-list"),
  subfoldersList: document.getElementById("subfolders-list"),
  subfolderCount: document.getElementById("subfolder-count"),
  chkAutoConvert: document.getElementById("chk-auto-convert"),
  btnConvertFolder: document.getElementById("btn-convert-folder"),
  unconvertedBadge: document.getElementById("unconverted-badge"),
  btnPullDownloads: document.getElementById("btn-pull-downloads"),
  folderTitle: document.getElementById("current-folder-title"),
  imageCountBadge: document.getElementById("image-count-badge"),
  searchInput: document.getElementById("search-input"),
  sortSelect: document.getElementById("sort-select"),
  gridSizeSlider: document.getElementById("grid-size-slider"),
  btnSelectAll: document.getElementById("btn-select-all"),
  btnClearSelection: document.getElementById("btn-clear-selection"),
  modeHelperText: document.getElementById("mode-helper-text"),
  galleryGrid: document.getElementById("gallery-grid"),
  tabSingle: document.getElementById("tab-single"),
  tabMultiview: document.getElementById("tab-multiview"),
  panelSingle: document.getElementById("panel-single-mode"),
  panelMultiview: document.getElementById("panel-multiview-mode"),
  selectedCount: document.getElementById("selected-count"),
  singlePreview: document.getElementById("single-selection-preview"),
  btnClearSingle: document.getElementById("btn-clear-single"),
  btnAutofill4View: document.getElementById("btn-autofill-4view"),
  btnClear4View: document.getElementById("btn-clear-4view"),
  multiviewTitleInput: document.getElementById("multiview-title-input"),
  modelSelect: document.getElementById("tripo-model-select"),
  qualitySelect: document.getElementById("tripo-quality-select"),
  formatSelect: document.getElementById("tripo-format-select"),
  chkTexture: document.getElementById("chk-tripo-texture"),
  chkFlatten: document.getElementById("chk-tripo-flatten"),
  btnStageTripoWeb: document.getElementById("btn-stage-tripo-web"),
  btnStageTripoWebText: document.getElementById("btn-stage-tripo-web-text"),
  btnSendTripo: document.getElementById("btn-send-tripo"),
  btnSendTripoText: document.getElementById("btn-send-tripo-text"),
  jobsList: document.getElementById("jobs-list"),
  jobsCountPill: document.getElementById("jobs-count-pill"),
  // Inspector Modal
  inspectorModal: document.getElementById("inspector-modal"),
  inspectorBackdrop: document.getElementById("inspector-backdrop"),
  inspectorFilename: document.getElementById("inspector-filename"),
  inspectorMeta: document.getElementById("inspector-meta"),
  inspectorImg: document.getElementById("inspector-img"),
  inspectorViewport: document.getElementById("inspector-viewport"),
  zoomLevelText: document.getElementById("zoom-level-text"),
  btnZoomIn: document.getElementById("btn-zoom-in"),
  btnZoomOut: document.getElementById("btn-zoom-out"),
  btnZoomReset: document.getElementById("btn-zoom-reset"),
  btnInspectSelectSingle: document.getElementById("btn-inspect-select-single"),
  btnInspectRename: document.getElementById("btn-inspect-rename"),
  btnInspectExplorer: document.getElementById("btn-inspect-explorer"),
  btnInspectorClose: document.getElementById("btn-inspector-close"),
  btnInspectPrev: document.getElementById("btn-inspect-prev"),
  btnInspectNext: document.getElementById("btn-inspect-next"),
  dropOverlay: document.getElementById("drop-overlay"),
  toastContainer: document.getElementById("toast-container"),
};

function showToast(msg, duration = 3500) {
  const t = document.createElement("div");
  t.className = "toast";
  t.textContent = msg;
  els.toastContainer.appendChild(t);
  setTimeout(() => {
    t.style.opacity = "0";
    setTimeout(() => t.remove(), 220);
  }, duration);
}

function formatBytes(bytes) {
  if (!bytes || bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

function imageApiUrl(filePath) {
  return `/api/image?path=${encodeURIComponent(filePath)}`;
}

// 1. Load Bookmarks & Balance
async function loadBookmarks() {
  try {
    const res = await fetch("/api/bookmarks");
    const data = await res.json();
    state.bookmarks = data.bookmarks || [];
    renderBookmarks();
  } catch (err) {
    console.error("Failed loading bookmarks:", err);
  }
}

function renderBookmarks() {
  els.bookmarksList.innerHTML = "";
  state.bookmarks.forEach((bm) => {
    const div = document.createElement("div");
    const isActive =
      state.currentFolder &&
      state.currentFolder.toLowerCase() === bm.path.toLowerCase();
    div.className = `bookmark-item ${isActive ? "active" : ""}`;
    div.innerHTML = `
      <span class="bookmark-title">📁 ${bm.name}</span>
      <span class="bookmark-sub">${bm.subtitle}</span>
    `;
    div.addEventListener("click", () => browseFolder(bm.path));
    els.bookmarksList.appendChild(div);
  });
}

async function refreshTripoBalance() {
  try {
    const res = await fetch("/api/tripo/balance");
    const data = await res.json();
    if (data.ok) {
      els.balanceText.textContent = `Tripo API: ${Number(data.balance).toLocaleString()} Credits`;
    } else {
      els.balanceText.textContent = `Tripo API: Connected`;
    }
  } catch (e) {
    els.balanceText.textContent = `Tripo API: Offline`;
  }
}

// 2. Browse Folder
async function browseFolder(folderPath) {
  const autoConv = els.chkAutoConvert.checked;
  const url = `/api/browse?path=${encodeURIComponent(folderPath || "")}&auto_convert=${autoConv}`;
  try {
    const res = await fetch(url);
    const data = await res.json();
    if (!res.ok) {
      showToast(`⚠️ ${data.error || "Could not open folder"}`);
      return;
    }

    state.currentFolder = data.current_folder;
    state.parentFolder = data.parent_folder;
    state.images = data.images || [];
    state.subdirs = data.subdirs || [];

    els.pathInput.value = state.currentFolder;
    els.folderTitle.textContent = data.folder_name;

    if (window.innerWidth <= 960) {
      document.body.setAttribute("data-mobile-view", "gallery");
      document.querySelectorAll(".mobile-nav-tab").forEach((tab) => {
        tab.classList.toggle("active", tab.dataset.tab === "gallery");
      });
    }

    if (data.converted_now && data.converted_now.length > 0) {
      showToast(`⚡ Auto-converted ${data.converted_now.length} image(s) to .JPG`);
    }

    if (data.unconverted_count > 0) {
      els.unconvertedBadge.textContent = data.unconverted_count;
      els.unconvertedBadge.classList.remove("hidden");
    } else {
      els.unconvertedBadge.classList.add("hidden");
    }

    renderBookmarks();
    renderSubfolders();
    applyFiltersAndRenderGallery();
  } catch (err) {
    showToast(`⚠️ Error loading folder: ${err.message}`);
  }
}

function renderSubfolders() {
  els.subfoldersList.innerHTML = "";
  els.subfolderCount.textContent = state.subdirs.length;

  if (state.subdirs.length === 0) {
    els.subfoldersList.innerHTML = `<div class="empty-slot-hint">No subfolders here</div>`;
    return;
  }

  state.subdirs.forEach((sub) => {
    const item = document.createElement("div");
    item.className = "subfolder-item";
    item.innerHTML = `
      <span>📂 ${sub.name}</span>
      <span class="count-pill">${sub.image_count}</span>
    `;
    item.addEventListener("click", () => browseFolder(sub.path));
    els.subfoldersList.appendChild(item);
  });
}

// 3. Filter, Sort & Render Gallery
function applyFiltersAndRenderGallery() {
  const query = els.searchInput.value.trim().toLowerCase();
  const sortBy = els.sortSelect.value;

  let list = state.images.filter((img) =>
    img.name.toLowerCase().includes(query)
  );

  if (sortBy === "name-asc") {
    list.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));
  } else if (sortBy === "newest") {
    list.sort((a, b) => b.mtime - a.mtime);
  } else if (sortBy === "oldest") {
    list.sort((a, b) => a.mtime - b.mtime);
  } else if (sortBy === "size-desc") {
    list.sort((a, b) => b.size_bytes - a.size_bytes);
  }

  state.filteredImages = list;
  els.imageCountBadge.textContent = `${list.length} image${list.length === 1 ? "" : "s"}`;
  renderGalleryGrid();
}

function getSlotForPath(path) {
  for (const [slot, p] of Object.entries(state.fourViewSlots)) {
    if (p === path) return slot;
  }
  return null;
}

function renderGalleryGrid() {
  els.galleryGrid.innerHTML = "";

  if (state.filteredImages.length === 0) {
    els.galleryGrid.innerHTML = `
      <div class="empty-slot-hint" style="grid-column: 1 / -1; padding: 50px;">
        No images found in this folder. Click a subfolder on the left, drop images here, or click "Pull Latest from Downloads".
      </div>
    `;
    return;
  }

  state.filteredImages.forEach((img, idx) => {
    const isSelected =
      state.mode === "single"
        ? state.selectedPaths.has(img.path)
        : Boolean(getSlotForPath(img.path));

    const assignedSlot = getSlotForPath(img.path);

    const card = document.createElement("div");
    card.className = `img-card ${isSelected ? "selected" : ""}`;
    card.dataset.path = img.path;

    const dims = img.width && img.height ? `${img.width}×${img.height}` : "";
    const checkLabel =
      state.mode === "multiview" && assignedSlot
        ? assignedSlot[0].toUpperCase()
        : "✓";

    card.innerHTML = `
      <div class="img-thumb-wrap">
        <img src="${imageApiUrl(img.path)}" alt="${img.name}" loading="lazy" />
        <div class="card-top-bar">
          <div class="select-check">${checkLabel}</div>
          <span class="ext-badge ${img.is_jpg ? "" : "non-jpg"}">${img.ext}</span>
        </div>
        <div class="card-hover-actions">
          <button class="inspect-btn" data-inspect="${idx}">🔍 Inspect</button>
          <div class="quick-slot-pills" title="Assign directly to 4-View Slot (Front / Back / Left / Right)">
            <button class="qslot-btn ${state.fourViewSlots.front === img.path ? "assigned" : ""}" data-qslot="front">F</button>
            <button class="qslot-btn ${state.fourViewSlots.back === img.path ? "assigned" : ""}" data-qslot="back">B</button>
            <button class="qslot-btn ${state.fourViewSlots.left === img.path ? "assigned" : ""}" data-qslot="left">L</button>
            <button class="qslot-btn ${state.fourViewSlots.right === img.path ? "assigned" : ""}" data-qslot="right">R</button>
          </div>
        </div>
      </div>
      <div class="card-meta">
        <div class="card-filename" title="${img.name}">${img.name}</div>
        <div class="card-submeta">
          <span>${dims}</span>
          <span>${formatBytes(img.size_bytes)}</span>
        </div>
      </div>
    `;

    // Card click: select image or assign to active 4-view slot
    card.addEventListener("click", (e) => {
      if (e.target.closest("[data-inspect]") || e.target.closest("[data-qslot]")) {
        return;
      }
      if (state.mode === "single") {
        if (state.selectedPaths.has(img.path)) {
          state.selectedPaths.delete(img.path);
        } else {
          state.selectedPaths.add(img.path);
        }
        updateSingleSelectionUI();
        renderGalleryGrid();
      } else {
        assignToFourViewSlot(state.activeTargetSlot, img.path);
      }
    });

    // Double-click opens Lightbox Inspector
    card.addEventListener("dblclick", () => openInspector(idx));

    // Inspect button
    const inspectBtn = card.querySelector("[data-inspect]");
    inspectBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      openInspector(idx);
    });

    // Quick 4-view slot buttons [F] [B] [L] [R]
    card.querySelectorAll("[data-qslot]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const slot = btn.dataset.qslot;
        if (state.mode !== "multiview") {
          setMode("multiview");
        }
        assignToFourViewSlot(slot, img.path);
      });
    });

    els.galleryGrid.appendChild(card);
  });
}

// 4. Mode Switching & Selection Panels
function setMode(mode) {
  state.mode = mode;
  els.tabSingle.classList.toggle("active", mode === "single");
  els.tabMultiview.classList.toggle("active", mode === "multiview");
  els.panelSingle.classList.toggle("hidden", mode !== "single");
  els.panelMultiview.classList.toggle("hidden", mode !== "multiview");

  if (mode === "single") {
    els.modeHelperText.innerHTML =
      "<strong>1-Image Mode:</strong> Click cards to select one or more images for Tripo 3D generation. Click <strong>🔍 Inspect</strong> (or double-click) to zoom &amp; examine details.";
  } else {
    els.modeHelperText.innerHTML =
      "<strong>4-View Orthographic Mode:</strong> Click a slot on the right (Front, Back, Left, Right) or use the <strong>[F] [B] [L] [R]</strong> buttons on any card, or click <strong>✨ Auto-Fill</strong>.";
  }
  renderGalleryGrid();
  updateSendButtonLabel();
}

function updateSingleSelectionUI() {
  const count = state.selectedPaths.size;
  els.selectedCount.textContent = count;
  els.singlePreview.innerHTML = "";

  if (count === 0) {
    els.singlePreview.innerHTML = `
      <div class="empty-slot-hint">
        Click one or more images in the gallery to queue them for 3D generation.
      </div>
    `;
  } else {
    Array.from(state.selectedPaths).forEach((p) => {
      const name = p.split(/[\\/]/).pop();
      const chip = document.createElement("div");
      chip.className = "mini-thumb-chip";
      chip.innerHTML = `
        <img src="${imageApiUrl(p)}" alt="${name}" />
        <span title="${name}">${name}</span>
      `;
      els.singlePreview.appendChild(chip);
    });
  }
  updateSendButtonLabel();
}

function assignToFourViewSlot(slot, filePath) {
  state.fourViewSlots[slot] = filePath;

  // Advance active target slot automatically to next empty slot
  const order = ["front", "back", "left", "right"];
  const nextEmpty = order.find((s) => !state.fourViewSlots[s]);
  if (nextEmpty) {
    state.activeTargetSlot = nextEmpty;
  }

  // Auto-suggest output STL name from front image
  if (slot === "front" && filePath && !els.multiviewTitleInput.value.trim()) {
    const base = filePath
      .split(/[\\/]/)
      .pop()
      .replace(/\.[^.]+$/, "")
      .replace(/(_front|_back|_left|_right)/i, "");
    els.multiviewTitleInput.value = `${base}_3d`;
  }

  updateFourViewSlotsUI();
  renderGalleryGrid();
}

function updateFourViewSlotsUI() {
  ["front", "back", "left", "right"].forEach((slot) => {
    const slotEl = document.getElementById(`slot-${slot}`);
    const bodyEl = document.getElementById(`slot-body-${slot}`);
    const clearBtn = slotEl.querySelector("[data-clear]");
    const filePath = state.fourViewSlots[slot];

    slotEl.classList.toggle("active-target", state.activeTargetSlot === slot);
    slotEl.classList.toggle("filled", Boolean(filePath));
    clearBtn.classList.toggle("hidden", !filePath);

    if (filePath) {
      const fname = filePath.split(/[\\/]/).pop();
      bodyEl.innerHTML = `<img src="${imageApiUrl(filePath)}" title="${fname}" alt="${slot}" />`;
    } else {
      bodyEl.innerHTML = `<span class="slot-placeholder">${
        state.activeTargetSlot === slot ? "Click an image to assign" : "Click to target"
      }</span>`;
    }
  });
  updateSendButtonLabel();
}

function autoFillFourViews() {
  // Look at currently selected images first, or all filtered images in the folder
  const pool =
    state.selectedPaths.size >= 2
      ? state.images.filter((i) => state.selectedPaths.has(i.path))
      : state.filteredImages;

  let matched = 0;
  ["front", "back", "left", "right"].forEach((slot) => {
    const found = pool.find((img) =>
      img.name.toLowerCase().includes(slot)
    );
    if (found) {
      state.fourViewSlots[slot] = found.path;
      matched++;
    }
  });

  if (matched > 0) {
    if (state.fourViewSlots.front) {
      const base = state.fourViewSlots.front
        .split(/[\\/]/)
        .pop()
        .replace(/\.[^.]+$/, "")
        .replace(/(_front|_back|_left|_right)/i, "");
      els.multiviewTitleInput.value = `${base}_3d`;
    }
    updateFourViewSlotsUI();
    renderGalleryGrid();
    showToast(`✨ Auto-filled ${matched} view slot(s)!`);
  } else {
    showToast("⚠️ Could not find filenames containing 'front', 'back', 'left', 'right'.");
  }
}

function updateSendButtonLabel() {
  const fmt = els.formatSelect.value;
  if (state.mode === "single") {
    const n = state.selectedPaths.size;
    if (els.btnStageTripoWebText) {
      els.btnStageTripoWebText.textContent =
        n > 1
          ? `Stage ${n} Images & Open Tripo Web (3000 Cr)`
          : `Stage & Open Tripo Web (3000 Cr Sub)`;
    }
    els.btnSendTripoText.textContent =
      n > 1
        ? `Direct API: ${n} Images → .${fmt}`
        : `Direct API → Generate .${fmt} ($0.20–$0.40)`;
  } else {
    const filled = Object.values(state.fourViewSlots).filter(Boolean).length;
    if (els.btnStageTripoWebText) {
      els.btnStageTripoWebText.textContent = `Stage 4-View (${filled}/4) & Open Tripo Web`;
    }
    els.btnSendTripoText.textContent = `Direct API: 4-View (${filled}/4) → .${fmt}`;
  }
}

// 5. Lightbox Inspector with Zoom & Pan
function openInspector(index) {
  if (index < 0 || index >= state.filteredImages.length) return;
  state.inspectorIndex = index;
  const img = state.filteredImages[index];

  els.inspectorFilename.textContent = img.name;
  els.inspectorMeta.textContent = `${img.width} × ${img.height} px • ${formatBytes(img.size_bytes)} • ${img.ext}`;
  els.inspectorImg.src = imageApiUrl(img.path);

  resetZoom();
  updateInspectorSelectBtn();
  els.inspectorModal.classList.remove("hidden");
}

function closeInspector() {
  els.inspectorModal.classList.add("hidden");
  state.inspectorIndex = -1;
}

function updateInspectorSelectBtn() {
  if (state.inspectorIndex < 0) return;
  const img = state.filteredImages[state.inspectorIndex];
  const isSel = state.selectedPaths.has(img.path);
  els.btnInspectSelectSingle.textContent = isSel ? "✓ Selected for Tripo" : "+ Select for Tripo";
}

function applyZoomTransform() {
  els.inspectorImg.style.transform = `translate(${state.panX}px, ${state.panY}px) scale(${state.zoom})`;
  els.zoomLevelText.textContent = `${Math.round(state.zoom * 100)}%`;
}

function resetZoom() {
  state.zoom = 1;
  state.panX = 0;
  state.panY = 0;
  applyZoomTransform();
}

// 6. Tripo Web Staging & Direct API Submission
async function stageForTripoWeb() {
  const payload = {
    mode: state.mode,
    export_format: els.formatSelect.value,
    source_folder: state.currentFolder,
    open_studio: true,
  };

  if (state.mode === "single") {
    if (state.selectedPaths.size === 0) {
      showToast("⚠️ Select at least one image in the gallery first.");
      return;
    }
    payload.image_paths = Array.from(state.selectedPaths);
  } else {
    if (!state.fourViewSlots.front) {
      showToast("⚠️ Front view slot is required for 4-View mode.");
      return;
    }
    payload.views = state.fourViewSlots;
    payload.title = els.multiviewTitleInput.value.trim();
  }

  if (els.btnStageTripoWeb) els.btnStageTripoWeb.disabled = true;
  try {
    const res = await fetch("/api/tripo/stage-web", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(`⚠️ ${data.error || "Failed to stage files"}`);
    } else {
      showToast(
        `✅ Staged ${data.staged_files.length} file(s), copied to Clipboard (Ctrl+V), & opened Tripo Studio!`,
        5000
      );
      fetchJobs();
    }
  } catch (err) {
    showToast(`⚠️ Error: ${err.message}`);
  } finally {
    if (els.btnStageTripoWeb) els.btnStageTripoWeb.disabled = false;
  }
}

async function pullStlFromDownloads(jobId) {
  try {
    const res = await fetch(`/api/tripo/pull-stl/${jobId}`, { method: "POST" });
    const data = await res.json();
    if (!res.ok) {
      showToast(`⚠️ ${data.error || "Could not pull .STL from Downloads"}`);
    } else {
      showToast(`📥 Pulled ${data.imported_from} → saved into output_stl!`, 4500);
      fetchJobs();
    }
  } catch (err) {
    showToast(`⚠️ Error: ${err.message}`);
  }
}

async function submitToTripo() {
  const payload = {
    mode: state.mode,
    model: els.modelSelect.value,
    geometry_quality: els.qualitySelect.value,
    export_format: els.formatSelect.value,
    texture: els.chkTexture.checked,
    flatten_bottom: els.chkFlatten.checked,
    source_folder: state.currentFolder,
  };

  if (state.mode === "single") {
    if (state.selectedPaths.size === 0) {
      showToast("⚠️ Select at least one image in the gallery first.");
      return;
    }
    payload.image_paths = Array.from(state.selectedPaths);
  } else {
    if (!state.fourViewSlots.front) {
      showToast("⚠️ Front view slot is required for 4-View mode.");
      return;
    }
    payload.views = state.fourViewSlots;
    payload.title = els.multiviewTitleInput.value.trim();
  }

  els.btnSendTripo.disabled = true;
  try {
    const res = await fetch("/api/tripo/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(`⚠️ ${data.error || "Failed to queue Tripo job"}`);
    } else {
      showToast(`🚀 Queued ${data.count} job(s) to Tripo 3D!`);
      fetchJobs();
      refreshTripoBalance();
    }
  } catch (err) {
    showToast(`⚠️ Error: ${err.message}`);
  } finally {
    els.btnSendTripo.disabled = false;
  }
}

async function fetchJobs() {
  try {
    const res = await fetch("/api/tripo/jobs");
    const data = await res.json();
    renderJobs(data.jobs || []);
  } catch (e) {
    console.error("Failed polling jobs:", e);
  }
}

function renderJobs(jobs) {
  els.jobsCountPill.textContent = jobs.length;
  els.jobsList.innerHTML = "";

  if (jobs.length === 0) {
    els.jobsList.innerHTML = `<div class="empty-slot-hint">No 3D generation jobs yet.</div>`;
    return;
  }

  jobs.forEach((job) => {
    const isDone = job.status === "success";
    const isFailed = job.status === "failed";
    const isStaged = job.status === "staged_web";
    const badgeClass = isDone ? "success" : isFailed ? "failed" : "running";

    const card = document.createElement("div");
    card.className = "job-card";
    card.innerHTML = `
      <div class="job-top">
        <span class="job-title" title="${job.title}">${
          job.mode === "multiview" ? "🧭" : "🖼️"
        } ${job.title}</span>
        <span class="job-badge ${badgeClass}">${job.status_label || job.status}</span>
      </div>
      <div class="progress-track">
        <div class="progress-fill" style="width: ${job.progress || 0}%"></div>
      </div>
      ${
        job.error
          ? `<div class="job-error-text">⚠️ ${job.error}</div>`
          : ""
      }
      <div class="job-actions">
        <span style="font-size: 0.67rem; color: var(--text-muted);">${job.model}</span>
        <div style="display: flex; gap: 5px; flex-wrap: wrap;">
          ${
            isStaged
              ? `
                <button class="glass-btn btn-xs action-accent" data-pull-stl="${job.id}" title="Grab the newest downloaded .STL/.GLB from Downloads and save it as ${job.title}.stl">
                  📥 Pull .STL
                </button>
                <button class="glass-btn btn-xs" data-reveal="${job.staged_dir || ""}" title="Open Staged Images Folder">📂 Staged</button>
              `
              : ""
          }
          ${
            job.stl_path
              ? `
                <a href="/api/download?path=${encodeURIComponent(job.stl_path)}" class="glass-btn btn-xs action-secondary" style="text-decoration:none;">
                  ⬇️ .${job.export_format || "STL"}
                </a>
                <button class="glass-btn btn-xs" data-reveal="${job.stl_path}" title="Show in Explorer">📂</button>
              `
              : ""
          }
          <button class="glass-btn btn-xs" data-del-job="${job.id}" title="Remove from list">✕</button>
        </div>
      </div>
    `;

    const pullBtn = card.querySelector("[data-pull-stl]");
    if (pullBtn) {
      pullBtn.addEventListener("click", () => pullStlFromDownloads(job.id));
    }

    const revealBtn = card.querySelector("[data-reveal]");
    if (revealBtn) {
      revealBtn.addEventListener("click", () => revealInExplorer(revealBtn.dataset.reveal));
    }

    const delBtn = card.querySelector("[data-del-job]");
    if (delBtn) {
      delBtn.addEventListener("click", async () => {
        await fetch(`/api/tripo/jobs/${job.id}`, { method: "DELETE" });
        fetchJobs();
      });
    }

    els.jobsList.appendChild(card);
  });
}

async function revealInExplorer(targetPath) {
  await fetch("/api/reveal", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path: targetPath }),
  });
}

// 7. Event Listeners Setup
function initEventListeners() {
  // Path bar navigation
  els.btnGoPath.addEventListener("click", () => browseFolder(els.pathInput.value));
  els.pathInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") browseFolder(els.pathInput.value);
  });

  els.btnUpDir.addEventListener("click", () => {
    if (state.parentFolder) browseFolder(state.parentFolder);
  });

  els.btnNativeBrowse.addEventListener("click", async () => {
    els.btnNativeBrowse.disabled = true;
    try {
      const res = await fetch("/api/pick-folder", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ initial_dir: state.currentFolder }),
      });
      const data = await res.json();
      if (data.path) browseFolder(data.path);
    } finally {
      els.btnNativeBrowse.disabled = false;
    }
  });

  els.btnOpenExplorer.addEventListener("click", () => {
    if (state.currentFolder) revealInExplorer(state.currentFolder);
  });

  els.balancePill.addEventListener("click", refreshTripoBalance);

  // Convert Folder to JPG button
  els.btnConvertFolder.addEventListener("click", async () => {
    if (!state.currentFolder) return;
    const res = await fetch("/api/convert-folder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ folder: state.currentFolder, archive_originals: true }),
    });
    const data = await res.json();
    if (data.count > 0) {
      showToast(`✅ Converted ${data.count} file(s) to .JPG!`);
      browseFolder(state.currentFolder);
    } else {
      showToast("All images in this folder are already .JPG!");
    }
  });

  // Pull from Downloads
  els.btnPullDownloads.addEventListener("click", async () => {
    els.btnPullDownloads.disabled = true;
    try {
      const res = await fetch("/api/pull-downloads", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dest_folder: state.currentFolder, limit: 15 }),
      });
      const data = await res.json();
      if (data.count > 0) {
        showToast(`📥 Pulled & converted ${data.count} image(s) from Downloads!`);
        browseFolder(state.currentFolder);
      } else {
        showToast("No new unimported images found in Downloads.");
      }
    } finally {
      els.btnPullDownloads.disabled = false;
    }
  });

  // Search, Sort, Grid Size
  els.searchInput.addEventListener("input", applyFiltersAndRenderGallery);
  els.sortSelect.addEventListener("change", applyFiltersAndRenderGallery);
  els.gridSizeSlider.addEventListener("input", (e) => {
    document.documentElement.style.setProperty("--card-min-width", `${e.target.value}px`);
  });

  // Select All / Clear
  els.btnSelectAll.addEventListener("click", () => {
    state.filteredImages.forEach((img) => state.selectedPaths.add(img.path));
    updateSingleSelectionUI();
    renderGalleryGrid();
  });

  els.btnClearSelection.addEventListener("click", () => {
    state.selectedPaths.clear();
    updateSingleSelectionUI();
    renderGalleryGrid();
  });

  els.btnClearSingle.addEventListener("click", () => {
    state.selectedPaths.clear();
    updateSingleSelectionUI();
    renderGalleryGrid();
  });

  // Mode Tabs
  els.tabSingle.addEventListener("click", () => setMode("single"));
  els.tabMultiview.addEventListener("click", () => setMode("multiview"));
  els.formatSelect.addEventListener("change", updateSendButtonLabel);

  // 4-View Slot clicks
  ["front", "back", "left", "right"].forEach((slot) => {
    const slotEl = document.getElementById(`slot-${slot}`);
    slotEl.addEventListener("click", (e) => {
      if (e.target.closest("[data-clear]")) return;
      state.activeTargetSlot = slot;
      updateFourViewSlotsUI();
    });
    const clearBtn = slotEl.querySelector("[data-clear]");
    clearBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      state.fourViewSlots[slot] = null;
      state.activeTargetSlot = slot;
      updateFourViewSlotsUI();
      renderGalleryGrid();
    });
  });

  els.btnAutofill4View.addEventListener("click", autoFillFourViews);
  els.btnClear4View.addEventListener("click", () => {
    state.fourViewSlots = { front: null, back: null, left: null, right: null };
    state.activeTargetSlot = "front";
    els.multiviewTitleInput.value = "";
    updateFourViewSlotsUI();
    renderGalleryGrid();
  });

  if (els.btnStageTripoWeb) {
    els.btnStageTripoWeb.addEventListener("click", stageForTripoWeb);
  }
  els.btnSendTripo.addEventListener("click", submitToTripo);

  // Lightbox Inspector Events
  els.btnInspectorClose.addEventListener("click", closeInspector);
  els.inspectorBackdrop.addEventListener("click", closeInspector);
  els.btnInspectPrev.addEventListener("click", () => {
    if (state.inspectorIndex > 0) openInspector(state.inspectorIndex - 1);
  });
  els.btnInspectNext.addEventListener("click", () => {
    if (state.inspectorIndex < state.filteredImages.length - 1) {
      openInspector(state.inspectorIndex + 1);
    }
  });

  els.btnZoomIn.addEventListener("click", () => {
    state.zoom = Math.min(5, state.zoom + 0.25);
    applyZoomTransform();
  });
  els.btnZoomOut.addEventListener("click", () => {
    state.zoom = Math.max(0.4, state.zoom - 0.25);
    applyZoomTransform();
  });
  els.btnZoomReset.addEventListener("click", resetZoom);

  els.inspectorViewport.addEventListener("wheel", (e) => {
    e.preventDefault();
    const delta = e.deltaY < 0 ? 0.18 : -0.18;
    state.zoom = Math.min(5, Math.max(0.4, state.zoom + delta));
    applyZoomTransform();
  });

  els.inspectorViewport.addEventListener("mousedown", (e) => {
    if (e.target.closest("button")) return;
    state.isPanning = true;
    state.panStartX = e.clientX - state.panX;
    state.panStartY = e.clientY - state.panY;
  });

  window.addEventListener("mousemove", (e) => {
    if (!state.isPanning) return;
    state.panX = e.clientX - state.panStartX;
    state.panY = e.clientY - state.panStartY;
    applyZoomTransform();
  });

  window.addEventListener("mouseup", () => {
    state.isPanning = false;
  });

  // Inspector Action Buttons
  els.btnInspectSelectSingle.addEventListener("click", () => {
    if (state.inspectorIndex < 0) return;
    const img = state.filteredImages[state.inspectorIndex];
    if (state.selectedPaths.has(img.path)) {
      state.selectedPaths.delete(img.path);
    } else {
      state.selectedPaths.add(img.path);
    }
    updateInspectorSelectBtn();
    updateSingleSelectionUI();
    renderGalleryGrid();
  });

  document.querySelectorAll(".assign-slot-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (state.inspectorIndex < 0) return;
      const img = state.filteredImages[state.inspectorIndex];
      const slot = btn.dataset.assign;
      setMode("multiview");
      assignToFourViewSlot(slot, img.path);
      showToast(`Assigned ${img.name} to ${slot.toUpperCase()} slot`);
    });
  });

  els.btnInspectRename.addEventListener("click", async () => {
    if (state.inspectorIndex < 0) return;
    const img = state.filteredImages[state.inspectorIndex];
    const currentStem = img.name.replace(/\.[^.]+$/, "");
    const nextName = prompt("Enter new filename:", currentStem);
    if (!nextName || nextName.trim() === currentStem) return;

    const res = await fetch("/api/rename", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: img.path, new_name: nextName.trim() }),
    });
    const data = await res.json();
    if (res.ok) {
      showToast(`Renamed to ${data.new_name}`);
      await browseFolder(state.currentFolder);
      closeInspector();
    } else {
      showToast(`⚠️ ${data.error}`);
    }
  });

  els.btnInspectExplorer.addEventListener("click", () => {
    if (state.inspectorIndex < 0) return;
    revealInExplorer(state.filteredImages[state.inspectorIndex].path);
  });

  // Keyboard shortcuts
  window.addEventListener("keydown", (e) => {
    if (els.inspectorModal.classList.contains("hidden")) return;
    if (e.key === "Escape") closeInspector();
    if (e.key === "ArrowLeft" && state.inspectorIndex > 0) {
      openInspector(state.inspectorIndex - 1);
    }
    if (e.key === "ArrowRight" && state.inspectorIndex < state.filteredImages.length - 1) {
      openInspector(state.inspectorIndex + 1);
    }
  });

  // Drag & Drop Files Anywhere
  window.addEventListener("dragover", (e) => {
    e.preventDefault();
    els.dropOverlay.classList.remove("hidden");
  });

  els.dropOverlay.addEventListener("dragleave", (e) => {
    if (e.target === els.dropOverlay) {
      els.dropOverlay.classList.add("hidden");
    }
  });

  window.addEventListener("drop", async (e) => {
    e.preventDefault();
    els.dropOverlay.classList.add("hidden");
    const files = e.dataTransfer.files;
    if (!files || files.length === 0) return;

    const formData = new FormData();
    formData.append("folder", state.currentFolder);
    for (const f of files) {
      formData.append("files", f);
    }

    const res = await fetch("/api/upload-drop", {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    if (data.count > 0) {
      showToast(`📥 Imported & converted ${data.count} file(s) to .JPG!`);
      browseFolder(state.currentFolder);
    }
  });

  // Mobile Bottom Tab Bar
  document.querySelectorAll(".mobile-nav-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      const view = tab.dataset.tab;
      document.body.setAttribute("data-mobile-view", view);
      document.querySelectorAll(".mobile-nav-tab").forEach((t) => {
        t.classList.toggle("active", t.dataset.tab === view);
      });
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  });

  // Phone Connect Modal
  const btnPhoneConnect = document.getElementById("btn-phone-connect");
  const phoneModal = document.getElementById("phone-modal");
  const btnPhoneClose = document.getElementById("btn-phone-close");
  const phoneModalBackdrop = document.getElementById("phone-modal-backdrop");

  if (btnPhoneConnect && phoneModal) {
    btnPhoneConnect.addEventListener("click", () => {
      phoneModal.classList.remove("hidden");
    });
  }
  if (btnPhoneClose && phoneModal) {
    btnPhoneClose.addEventListener("click", () => {
      phoneModal.classList.add("hidden");
    });
  }
  if (phoneModalBackdrop && phoneModal) {
    phoneModalBackdrop.addEventListener("click", () => {
      phoneModal.classList.add("hidden");
    });
  }
}

// Initialize App
document.addEventListener("DOMContentLoaded", () => {
  if (window.innerWidth <= 960) {
    document.body.setAttribute("data-mobile-view", "gallery");
  }
  initEventListeners();
  loadBookmarks();
  refreshTripoBalance();
  browseFolder(els.pathInput.value);
  fetchJobs();
  setInterval(fetchJobs, 3500);
});
