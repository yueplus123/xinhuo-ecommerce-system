(function () {
  function qs(sel, root) {
    return (root || document).querySelector(sel);
  }

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

  function bindRemove(card) {
    var btn = qs("[data-remove-payment-image]", card);
    if (!btn) return;
    btn.addEventListener("click", function (ev) {
      ev.preventDefault();
      ev.stopPropagation();
      var mainFlag = qs(".payment-delete-main-flag", card);
      var extraFlag = qs(".payment-delete-extra-flag", card);
      if (mainFlag) {
        card.classList.toggle("is-pending-delete");
        mainFlag.checked = !mainFlag.checked;
        return;
      }
      if (extraFlag && extraFlag.value) {
        card.classList.toggle("is-pending-delete");
        extraFlag.checked = !extraFlag.checked;
        return;
      }
      card.remove();
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
    btn.setAttribute("data-remove-payment-image", "");
    btn.setAttribute("aria-label", "删除截图");
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
    var root = qs("[data-payment-images]");
    if (!root) return;
    var grid = qs("[data-payment-image-grid]", root);
    var uploadLabel = qs("[data-payment-image-upload]", root);
    var fileInput = qs(".sku-image-file-input", root);
    if (!grid || !uploadLabel || !fileInput) return;

    var pendingFiles = [];
    var previewMap = {};

    grid.querySelectorAll("[data-payment-image-card]").forEach(bindRemove);

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
