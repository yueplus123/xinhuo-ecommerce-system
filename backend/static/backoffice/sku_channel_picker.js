(function () {
  function qs(sel, root) {
    return (root || document).querySelector(sel);
  }

  function syncChipState(chip) {
    var input = qs(".pool-chip-input", chip);
    if (!input) return;
    chip.classList.toggle("is-selected", input.checked);
  }

  function bindChip(chip) {
    var input = qs(".pool-chip-input", chip);
    if (!input) return;
    chip.addEventListener("click", function (ev) {
      if (ev.target === input) return;
      ev.preventDefault();
      input.checked = !input.checked;
      syncChipState(chip);
    });
    input.addEventListener("change", function () {
      syncChipState(chip);
    });
    syncChipState(chip);
  }

  function createChip(id, name, fieldName) {
    var label = document.createElement("label");
    label.className = "pool-chip is-selected";
    var input = document.createElement("input");
    input.type = "checkbox";
    input.className = "pool-chip-input";
    input.name = fieldName;
    input.value = String(id);
    input.checked = true;
    var text = document.createElement("span");
    text.className = "pool-chip-text";
    text.textContent = name;
    var check = document.createElement("span");
    check.className = "pool-chip-check";
    check.setAttribute("aria-hidden", "true");
    check.textContent = "✓";
    label.appendChild(input);
    label.appendChild(text);
    label.appendChild(check);
    bindChip(label);
    return label;
  }

  function showInlineToast(section, message, isError) {
    if (!section) return;
    var existing = section.querySelector(".tag-inline-toast");
    if (existing) existing.remove();
    var toast = document.createElement("div");
    toast.className = "bb-message tag-inline-toast " + (isError ? "error" : "success");
    toast.textContent = message;
    var grid = section.querySelector(".pool-chip-grid");
    if (grid) section.insertBefore(toast, grid);
    else section.appendChild(toast);
    window.setTimeout(function () {
      toast.remove();
    }, 4000);
  }

  function bindTagPicker(config) {
    var grid = qs(config.gridSelector);
    if (grid) {
      grid.querySelectorAll(".pool-chip:not(.pool-chip--add)").forEach(bindChip);
    }

    var modal = qs(config.modalSelector);
    var openBtn = qs(config.openSelector);
    var closeBtn = qs(config.closeSelector);
    var section = qs(config.sectionSelector);

    function openModal() {
      if (!modal) return;
      modal.removeAttribute("hidden");
      document.body.style.overflow = "hidden";
      var nameInput = qs(config.nameInputSelector, modal);
      if (nameInput) {
        window.setTimeout(function () {
          nameInput.focus();
        }, 50);
      }
    }

    function closeModal() {
      if (!modal) return;
      modal.setAttribute("hidden", "");
      document.body.style.overflow = "";
      var errEl = qs(config.errorSelector, modal);
      if (errEl) {
        errEl.hidden = true;
        errEl.textContent = "";
      }
    }

    function bindQuickAddForm() {
      var form = qs("form", modal);
      if (!form) return;
      form.addEventListener("submit", function (ev) {
        ev.preventDefault();
        var submitBtn = qs('button[type="submit"]', form);
        if (submitBtn) submitBtn.disabled = true;
        var errEl = qs(config.errorSelector, modal);
        if (errEl) {
          errEl.hidden = true;
          errEl.textContent = "";
        }
        fetch(form.action, {
          method: "POST",
          body: new FormData(form),
          headers: { "X-Requested-With": "XMLHttpRequest" },
          credentials: "same-origin",
        })
          .then(function (resp) {
            return resp.json().then(function (data) {
              if (!resp.ok) throw data;
              return data;
            });
          })
          .then(function (data) {
            var addBtn = qs(config.openSelector, grid);
            if (grid && addBtn) {
              var chip = createChip(data.id, data.name, config.fieldName);
              grid.insertBefore(chip, addBtn);
            }
            var nameInput = qs(config.nameInputSelector, modal);
            if (nameInput) nameInput.value = "";
            closeModal();
            showInlineToast(section, data.message || config.successMessage);
          })
          .catch(function (err) {
            var msg = (err && err.error) || "添加失败，请稍后重试。";
            if (errEl) {
              errEl.textContent = msg;
              errEl.hidden = false;
            } else {
              showInlineToast(section, msg, true);
            }
          })
          .finally(function () {
            if (submitBtn) submitBtn.disabled = false;
          });
      });
    }

    if (openBtn && modal) {
      openBtn.addEventListener("click", openModal);
    }
    if (closeBtn && modal) {
      closeBtn.addEventListener("click", closeModal);
    }
    if (modal) {
      bindQuickAddForm();
      modal.addEventListener("click", function (ev) {
        if (ev.target === modal) closeModal();
      });
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    bindTagPicker({
      gridSelector: "[data-channel-chip-grid]",
      modalSelector: "#channel-add-modal",
      openSelector: "[data-open-channel-modal]",
      closeSelector: "[data-close-channel-modal]",
      sectionSelector: "#sku-channel-tags",
      nameInputSelector: "#channel-quick-name",
      errorSelector: "[data-channel-modal-error]",
      fieldName: "channel_tags",
      successMessage: "渠道已加入渠道池。",
    });

    document.addEventListener("keydown", function (ev) {
      if (ev.key !== "Escape") return;
      var modal = qs("#channel-add-modal");
      if (modal && !modal.hasAttribute("hidden")) {
        modal.setAttribute("hidden", "");
        document.body.style.overflow = "";
      }
    });
  });
})();
