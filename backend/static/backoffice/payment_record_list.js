(function () {
  function ready(fn) {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", fn);
    else fn();
  }

  ready(function () {
    var modal = document.getElementById("bb-payment-img-modal");
    if (!modal) return;
    var img = modal.querySelector(".bb-img-modal-img");
    var panel = modal.querySelector(".bb-img-modal-panel");
    var viewport = modal.querySelector(".bb-img-modal-viewport");
    var btnPrev = document.getElementById("bb-img-modal-prev");
    var btnNext = document.getElementById("bb-img-modal-next");
    var counter = document.getElementById("bb-img-modal-counter");
    var navBar = modal.querySelector(".bb-img-modal-nav");

    var gallery = [];
    var index = 0;

    function parseGallery(el) {
      var wrap = el.closest(".bb-payment-imgs");
      if (!wrap) return null;
      var links = wrap.querySelectorAll("a.js-bb-payment-img");
      var urls = [];
      for (var i = 0; i < links.length; i++) {
        var h = links[i].getAttribute("href");
        if (h) urls.push(h);
      }
      if (urls.length) return urls;
      var raw = wrap.getAttribute("data-bb-gallery");
      if (!raw) return null;
      try {
        return JSON.parse(raw);
      } catch (e) {
        return null;
      }
    }

    function updateNav() {
      var n = gallery.length;
      if (navBar) navBar.hidden = n <= 1;
      if (!btnPrev || !btnNext || !counter) return;
      counter.textContent = n ? index + 1 + " / " + n : "";
      btnPrev.disabled = index <= 0;
      btnNext.disabled = index >= n - 1;
    }

    function showIndex(i) {
      if (!gallery.length || !img) return;
      index = Math.max(0, Math.min(i, gallery.length - 1));
      img.src = gallery[index];
      updateNav();
    }

    function openModal(urls, startIndex) {
      gallery = urls && urls.length ? urls.slice() : [];
      if (!gallery.length || !img) return;
      index = Math.max(0, Math.min(startIndex || 0, gallery.length - 1));
      img.src = gallery[index];
      modal.removeAttribute("hidden");
      modal.classList.add("bb-img-modal--open");
      document.body.style.overflow = "hidden";
      updateNav();
    }

    function closeModal() {
      modal.classList.remove("bb-img-modal--open");
      modal.setAttribute("hidden", "");
      if (img) img.src = "";
      gallery = [];
      index = 0;
      document.body.style.overflow = "";
    }

    document.addEventListener("click", function (e) {
      var trigger = e.target.closest("a.js-bb-payment-img");
      if (!trigger) return;
      e.preventDefault();
      var urls = parseGallery(trigger);
      if (!urls || !urls.length) {
        openModal([trigger.getAttribute("href")], 0);
        return;
      }
      var idx = parseInt(trigger.getAttribute("data-bb-idx"), 10);
      if (Number.isNaN(idx)) idx = 0;
      openModal(urls, idx);
    });

    if (btnPrev) {
      btnPrev.addEventListener("click", function (e) {
        e.stopPropagation();
        showIndex(index - 1);
      });
    }
    if (btnNext) {
      btnNext.addEventListener("click", function (e) {
        e.stopPropagation();
        showIndex(index + 1);
      });
    }

    modal.addEventListener("click", function (e) {
      if (e.target.closest("[data-bb-img-modal-close]")) closeModal();
    });

    document.addEventListener("keydown", function (e) {
      if (!modal.classList.contains("bb-img-modal--open")) return;
      if (e.key === "Escape") closeModal();
      else if (e.key === "ArrowLeft" && !btnPrev.disabled) showIndex(index - 1);
      else if (e.key === "ArrowRight" && !btnNext.disabled) showIndex(index + 1);
    });

    if (panel) {
      panel.addEventListener("click", function (e) {
        e.stopPropagation();
      });
    }
    if (viewport) {
      viewport.addEventListener("click", function (e) {
        e.stopPropagation();
      });
    }
  });
})();
