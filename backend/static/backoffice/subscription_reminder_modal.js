(function () {
  function getCookie(name) {
    var m = document.cookie.match("(?:^|; )" + name.replace(/([.$?*|{}()[\]\\/+^])/g, "\\$1") + "=([^;]*)");
    return m ? decodeURIComponent(m[1]) : "";
  }

  function wireClose(root, overlay) {
    root.querySelectorAll("[data-bb-sub-rem-close]").forEach(function (b) {
      b.addEventListener("click", function () {
        overlay.hidden = true;
      });
    });
  }

  function openModal(overlay, bodyEl, url) {
    if (!url) return;
    overlay.hidden = false;
    bodyEl.innerHTML = "<p class=\"bb-subtitle\">加载中…</p>";
    fetch(url, { headers: { Accept: "text/html" }, credentials: "same-origin" })
      .then(function (r) {
        return r.text();
      })
      .then(function (html) {
        bodyEl.innerHTML = html;
        wireClose(bodyEl, overlay);
      })
      .catch(function () {
        bodyEl.innerHTML = "<p class=\"bb-subtitle\">加载失败，请刷新页面重试。</p>";
        wireClose(bodyEl, overlay);
      });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var overlay = document.getElementById("bb-sub-rem-overlay");
    var bodyEl = document.getElementById("bb-sub-rem-modal-body");
    var btnAdd = document.getElementById("bb-sub-rem-btn-add");
    if (!overlay || !bodyEl) return;

    overlay.addEventListener("click", function (ev) {
      if (ev.target === overlay) overlay.hidden = true;
    });

    overlay.addEventListener("submit", function (ev) {
      var form = ev.target;
      if (!form || form.id !== "bb-sub-rem-modal-form") return;
      ev.preventDefault();
      var fd = new FormData(form);
      fetch(form.action, {
        method: "POST",
        headers: {
          "X-CSRFToken": getCookie("csrftoken"),
          "X-BB-Modal": "1",
          "X-Requested-With": "XMLHttpRequest",
        },
        body: fd,
        credentials: "same-origin",
      }).then(function (r) {
        var ct = (r.headers.get("content-type") || "").toLowerCase();
        return r.text().then(function (t) {
          if (ct.indexOf("application/json") !== -1) {
            try {
              var j = JSON.parse(t);
              if (j.redirect) window.location.href = j.redirect;
            } catch (e) {}
            return;
          }
          bodyEl.innerHTML = t;
          wireClose(bodyEl, overlay);
        });
      });
    });

    if (btnAdd) {
      btnAdd.addEventListener("click", function () {
        openModal(overlay, bodyEl, btnAdd.getAttribute("data-modal-url"));
      });
    }

    document.querySelectorAll(".bb-sub-rem-open-edit").forEach(function (btn) {
      btn.addEventListener("click", function () {
        openModal(overlay, bodyEl, btn.getAttribute("data-modal-url"));
      });
    });

    var auto = overlay.getAttribute("data-auto-open");
    if (auto) openModal(overlay, bodyEl, auto);
  });
})();
