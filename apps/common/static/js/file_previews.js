// static/js/file_previews.js
(() => {
  "use strict";

  function clear(el) {
    while (el.firstChild) el.removeChild(el.firstChild);
  }

  function createImg(url, opts = {}) {
    const img = document.createElement("img");
    img.src = url;
    img.alt = "";
    img.style.width = opts.width || "100%";
    img.style.height = opts.height || "160px";
    img.style.objectFit = "cover";
    img.style.borderRadius = opts.radius || "12px";
    img.style.display = "block";
    return img;
  }

  function createThumbGrid() {
    const wrap = document.createElement("div");
    wrap.style.display = "grid";
    wrap.style.gridTemplateColumns = "repeat(auto-fill, minmax(120px, 1fr))";
    wrap.style.gap = "10px";
    return wrap;
  }

  function bindSingle(input, target) {
    input.addEventListener("change", () => {
      const file = input.files && input.files[0];
      if (!file) return;

      const url = URL.createObjectURL(file);
      clear(target);
      target.appendChild(createImg(url, { height: "220px" }));
    });
  }

  function bindMultiple(input, target) {
    input.addEventListener("change", () => {
      const files = Array.from(input.files || []);
      if (!files.length) return;

      clear(target);
      const grid = createThumbGrid();

      files.forEach((file) => {
        const url = URL.createObjectURL(file);
        const img = createImg(url, { height: "120px", radius: "10px" });
        grid.appendChild(img);
      });

      target.appendChild(grid);
    });
  }

  function bindAll(root = document) {
    // 単体画像: data-preview="single"
    root.querySelectorAll('input[type="file"][data-preview="single"]').forEach((input) => {
      const sel = input.getAttribute("data-preview-target");
      if (!sel) return;
      const target = root.querySelector(sel);
      if (!target) return;
      if (input.dataset.previewBound === "1") return;
      input.dataset.previewBound = "1";
      bindSingle(input, target);
    });

    // 複数画像: data-preview="multi"
    root.querySelectorAll('input[type="file"][data-preview="multi"]').forEach((input) => {
      const sel = input.getAttribute("data-preview-target");
      if (!sel) return;
      const target = root.querySelector(sel);
      if (!target) return;
      if (input.dataset.previewBound === "1") return;
      input.dataset.previewBound = "1";
      bindMultiple(input, target);
    });
  }

  document.addEventListener("DOMContentLoaded", () => bindAll());
  window.bindFilePreviews = bindAll; // AJAXでフォーム差し替えの時用
})();
