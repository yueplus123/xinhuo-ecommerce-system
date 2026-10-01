(function () {
  function csrftoken() {
    var m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
  }

  function getDragAfterElement(container, y, dragged) {
    var rows = [].slice.call(container.querySelectorAll(".bb-sortable-row"));
    var closest = { offset: Number.NEGATIVE_INFINITY, element: null };
    for (var i = 0; i < rows.length; i++) {
      var child = rows[i];
      if (child === dragged) continue;
      var box = child.getBoundingClientRect();
      var offset = y - box.top - box.height / 2;
      if (offset < 0 && offset > closest.offset) {
        closest = { offset: offset, element: child };
      }
    }
    return closest.element;
  }

  function readOrder(tbody) {
    return [].map.call(tbody.querySelectorAll(".bb-sortable-row"), function (tr) {
      return parseInt(tr.getAttribute("data-sort-id"), 10);
    });
  }

  function postOrder(url, order, onDone) {
    fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrftoken(),
      },
      body: JSON.stringify({ order: order }),
    })
      .then(function (r) {
        return r.json().then(function (body) {
          if (!r.ok) throw new Error((body && body.error) || r.statusText);
          return body;
        });
      })
      .then(function () {
        if (onDone) onDone(null);
      })
      .catch(function (e) {
        if (onDone) onDone(e);
      });
  }

  function init() {
    var tbody = document.getElementById("bb-sortable-tbody");
    if (!tbody) return;
    var url = tbody.getAttribute("data-reorder-url");
    if (!url) return;

    var dragged = null;
    /** 对 <tr draggable> 的 dragstart，Chrome 等会把 target 设为 tr 本身，无法用 closest 判断把手；改由把手 mousedown 记录此行。 */
    var dragFromHandleRow = null;
    var isDragging = false;

    document.addEventListener(
      "mouseup",
      function () {
        window.setTimeout(function () {
          if (!isDragging) dragFromHandleRow = null;
        }, 0);
      },
      true
    );

    tbody.querySelectorAll(".bb-drag-handle").forEach(function (handle) {
      handle.addEventListener("mousedown", function () {
        var r = handle.closest(".bb-sortable-row");
        dragFromHandleRow = r || null;
      });
    });

    tbody.addEventListener("dragover", function (e) {
      e.preventDefault();
      if (!dragged) return;
      var after = getDragAfterElement(tbody, e.clientY, dragged);
      if (after == null) {
        tbody.appendChild(dragged);
      } else {
        tbody.insertBefore(dragged, after);
      }
    });

    tbody.addEventListener("drop", function (e) {
      e.preventDefault();
    });

    tbody.querySelectorAll(".bb-sortable-row").forEach(function (row) {
      row.setAttribute("draggable", "true");
      row.addEventListener("dragstart", function (e) {
        if (row !== dragFromHandleRow) {
          e.preventDefault();
          return;
        }
        isDragging = true;
        dragged = row;
        row.classList.add("bb-sort-dragging");
        e.dataTransfer.effectAllowed = "move";
        e.dataTransfer.setData("text/plain", row.getAttribute("data-sort-id") || "");
      });
      row.addEventListener("dragend", function () {
        isDragging = false;
        dragFromHandleRow = null;
        row.classList.remove("bb-sort-dragging");
        var current = dragged;
        dragged = null;
        if (!current) return;
        postOrder(url, readOrder(tbody), function (err) {
          if (err) {
            window.alert("保存排序失败：" + (err.message || String(err)) + "\n将刷新页面。");
            window.location.reload();
            return;
          }
          var hint = document.getElementById("bb-sort-saved-hint");
          if (hint) {
            hint.hidden = false;
            window.clearTimeout(hint._t);
            hint._t = window.setTimeout(function () {
              hint.hidden = true;
            }, 1600);
          }
        });
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
