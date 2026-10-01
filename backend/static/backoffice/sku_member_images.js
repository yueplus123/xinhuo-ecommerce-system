(function () {
  function fileKey(file) {
    return [file.name, file.size, file.lastModified].join(":");
  }

  function syncFileInput(input, files) {
    var dt = new DataTransfer();
    files.forEach(function (file) {
      dt.items.add(file);
    });
    input.files = dt.files;
  }

  function bindExistingCard(card) {
    var btn = card.querySelector(".sku-image-remove");
    var flag = card.querySelector(".sku-image-delete-flag");
    if (!btn || !flag) return;
    btn.addEventListener("click", function (ev) {
      ev.preventDefault();
      ev.stopPropagation();
      flag.checked = !flag.checked;
      card.classList.toggle("is-pending-delete", flag.checked);
      btn.setAttribute("aria-label", flag.checked ? "撤销删除" : "删除此截图");
    });
  }

  function createPreviewCard(file, onRemove) {
    var card = document.createElement("div");
    card.className = "sku-image-card sku-image-card--new";
    card.dataset.fileKey = fileKey(file);

    var img = document.createElement("img");
    img.alt = "待上传截图";
    img.src = URL.createObjectURL(file);

    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "sku-image-remove";
    btn.setAttribute("aria-label", "删除此截图");
    btn.textContent = "×";
    btn.addEventListener("click", function (ev) {
      ev.preventDefault();
      ev.stopPropagation();
      URL.revokeObjectURL(img.src);
      card.remove();
      onRemove();
    });

    card.appendChild(img);
    card.appendChild(btn);
    return card;
  }

  document.addEventListener("DOMContentLoaded", function () {
    var root = document.querySelector("[data-member-images]");
    if (!root) return;

    var grid = root.querySelector("[data-member-image-grid]");
    var uploadLabel = root.querySelector("[data-member-image-upload]");
    var fileInput = root.querySelector(".sku-image-file-input");
    if (!grid || !uploadLabel || !fileInput) return;

    var pendingFiles = [];
    var previewMap = {};

    grid.querySelectorAll(".sku-image-card[data-existing-id]").forEach(bindExistingCard);

    function addFiles(fileList) {
      Array.from(fileList || []).forEach(function (file) {
        if (!file.type || file.type.indexOf("image/") !== 0) return;
        var key = fileKey(file);
        if (previewMap[key]) return;
        pendingFiles.push(file);
        var card = createPreviewCard(file, function () {
          pendingFiles = pendingFiles.filter(function (f) {
            return fileKey(f) !== key;
          });
          delete previewMap[key];
          syncFileInput(fileInput, pendingFiles);
        });
        previewMap[key] = card;
        grid.insertBefore(card, uploadLabel);
      });
      syncFileInput(fileInput, pendingFiles);
    }

    fileInput.addEventListener("change", function () {
      addFiles(fileInput.files);
    });

    ["dragenter", "dragover"].forEach(function (name) {
      uploadLabel.addEventListener(name, function (ev) {
        ev.preventDefault();
        uploadLabel.classList.add("is-dragover");
      });
    });
    uploadLabel.addEventListener("dragleave", function (ev) {
      ev.preventDefault();
      uploadLabel.classList.remove("is-dragover");
    });
    uploadLabel.addEventListener("drop", function (ev) {
      ev.preventDefault();
      uploadLabel.classList.remove("is-dragover");
      addFiles(ev.dataTransfer && ev.dataTransfer.files);
    });
  });
})();
