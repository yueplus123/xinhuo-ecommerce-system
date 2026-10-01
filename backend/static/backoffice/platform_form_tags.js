(function () {
  function ready(fn) {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", fn);
    else fn();
  }

  ready(function () {
    var modal = document.getElementById("platform-tag-add-modal");
    var openBtn = document.querySelector("[data-open-platform-tag-modal]");
    var closeBtns = document.querySelectorAll("[data-close-platform-tag-modal]");
    if (!modal) return;

    function openModal() {
      modal.removeAttribute("hidden");
      var input = modal.querySelector("#platform-tag-quick-name");
      if (input) input.focus();
    }

    function closeModal() {
      modal.setAttribute("hidden", "");
    }

    if (openBtn) openBtn.addEventListener("click", openModal);
    closeBtns.forEach(function (btn) {
      btn.addEventListener("click", closeModal);
    });
    modal.addEventListener("click", function (ev) {
      if (ev.target === modal) closeModal();
    });

    document.querySelectorAll("[data-platform-chip-grid] .pool-chip-input").forEach(function (input) {
      input.addEventListener("change", function () {
        var chip = input.closest(".pool-chip");
        if (chip) chip.classList.toggle("is-selected", input.checked);
      });
    });
  });
})();
