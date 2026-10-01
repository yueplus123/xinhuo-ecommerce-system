(function () {
  var WEEKDAYS = ["日", "一", "二", "三", "四", "五", "六"];
  var MONTHS = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"];

  function ready(fn) {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", fn);
    else fn();
  }

  function qs(sel, root) {
    return (root || document).querySelector(sel);
  }

  function parseYmd(s) {
    if (!s) return null;
    var m = String(s).match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!m) return null;
    return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  }

  function formatYmd(d) {
    if (!d) return "";
    var y = d.getFullYear();
    var mo = String(d.getMonth() + 1).padStart(2, "0");
    var da = String(d.getDate()).padStart(2, "0");
    return y + "-" + mo + "-" + da;
  }

  function cloneDay(d) {
    return new Date(d.getFullYear(), d.getMonth(), d.getDate());
  }

  function sameDay(a, b) {
    return (
      a &&
      b &&
      a.getFullYear() === b.getFullYear() &&
      a.getMonth() === b.getMonth() &&
      a.getDate() === b.getDate()
    );
  }

  function compareDay(a, b) {
    return (
      a.getFullYear() - b.getFullYear() ||
      a.getMonth() - b.getMonth() ||
      a.getDate() - b.getDate()
    );
  }

  function addMonths(base, delta) {
    return new Date(base.getFullYear(), base.getMonth() + delta, 1);
  }

  function monthTitle(d) {
    return d.getFullYear() + "年 " + MONTHS[d.getMonth()];
  }

  function normalizeRange(a, b) {
    if (compareDay(a, b) <= 0) return [cloneDay(a), cloneDay(b)];
    return [cloneDay(b), cloneDay(a)];
  }

  function buildRangeCalendar(mountEl, options) {
    options = options || {};
    var startDate = null;
    var endDate = null;
    var viewMonth = new Date(new Date().getFullYear(), new Date().getMonth(), 1);
    var pickingEnd = false;
    var hoverDate = null;

    mountEl.innerHTML =
      '<div class="bb-range-cal__toolbar">' +
      '<div class="bb-range-cal__nav-group">' +
      '<button type="button" class="bb-range-cal__nav" data-cal-prev-year aria-label="上一年">&laquo;</button>' +
      '<button type="button" class="bb-range-cal__nav" data-cal-prev-month aria-label="上一月">&lsaquo;</button>' +
      "</div>" +
      '<div class="bb-range-cal__titles">' +
      '<span class="bb-range-cal__title" data-cal-title-left></span>' +
      '<span class="bb-range-cal__title" data-cal-title-right></span>' +
      "</div>" +
      '<div class="bb-range-cal__nav-group">' +
      '<button type="button" class="bb-range-cal__nav" data-cal-next-month aria-label="下一月">&rsaquo;</button>' +
      '<button type="button" class="bb-range-cal__nav" data-cal-next-year aria-label="下一年">&raquo;</button>' +
      "</div>" +
      "</div>" +
      '<div class="bb-range-cal__panes">' +
      '<div class="bb-range-cal__pane" data-cal-pane="0"></div>' +
      '<div class="bb-range-cal__pane" data-cal-pane="1"></div>' +
      "</div>";

    var paneEls = mountEl.querySelectorAll("[data-cal-pane]");
    var titleLeft = qs("[data-cal-title-left]", mountEl);
    var titleRight = qs("[data-cal-title-right]", mountEl);

    function effectiveEnd() {
      if (endDate) return endDate;
      return null;
    }

    function applyCellRangeClasses(cell, cellDate, bounds, today) {
      var classes = ["bb-range-cal-day"];
      var isOther = cellDate.getMonth() !== parseInt(cell.getAttribute("data-cal-month"), 10);
      if (isOther) classes.push("is-other");
      if (sameDay(cellDate, today)) classes.push("is-today");

      var isStart = false;
      var isEnd = false;
      if (bounds) {
        var cmpStart = compareDay(cellDate, bounds[0]);
        var cmpEnd = compareDay(cellDate, bounds[1]);
        isStart = cmpStart === 0;
        isEnd = cmpEnd === 0;
        if (cmpStart >= 0 && cmpEnd <= 0) {
          classes.push("is-in-range");
          if (isStart) classes.push("is-range-start");
          if (isEnd) classes.push("is-range-end");
          if (!isStart && !isEnd) classes.push("is-range-middle");
        }
      }

      cell.className = classes.join(" ");
      var inner = cell.querySelector(".bb-range-cal-day-inner");
      if (inner) {
        inner.className = "bb-range-cal-day-inner" + (isStart || isEnd ? " is-edge" : "");
      }
    }

    function syncHoverHighlight() {
      if (!pickingEnd || !startDate || endDate) return;
      var previewEnd = hoverDate;
      var bounds = previewEnd ? normalizeRange(startDate, previewEnd) : [startDate, startDate];
      var today = new Date();
      today = new Date(today.getFullYear(), today.getMonth(), today.getDate());
      mountEl.querySelectorAll("[data-cal-day]").forEach(function (cell) {
        var day = parseYmd(cell.getAttribute("data-cal-day"));
        if (day) applyCellRangeClasses(cell, day, bounds, today);
      });
    }

    function rangeBounds() {
      if (!startDate) return null;
      var end = effectiveEnd();
      if (!end) return [startDate, startDate];
      return normalizeRange(startDate, end);
    }

    function renderPane(paneEl, monthStart) {
      var year = monthStart.getFullYear();
      var month = monthStart.getMonth();
      var firstWeekday = new Date(year, month, 1).getDay();
      var gridStart = new Date(year, month, 1 - firstWeekday);
      var bounds = rangeBounds();
      var today = new Date();
      today = new Date(today.getFullYear(), today.getMonth(), today.getDate());

      var html = '<table class="bb-range-cal__table"><thead><tr>';
      for (var w = 0; w < 7; w += 1) {
        html += "<th>" + WEEKDAYS[w] + "</th>";
      }
      html += "</tr></thead><tbody>";

      for (var row = 0; row < 6; row += 1) {
        html += "<tr>";
        for (var col = 0; col < 7; col += 1) {
          var offset = row * 7 + col;
          var cellDate = new Date(
            gridStart.getFullYear(),
            gridStart.getMonth(),
            gridStart.getDate() + offset
          );
          var isOther = cellDate.getMonth() !== month;

          var classes = ["bb-range-cal-day"];
          if (isOther) classes.push("is-other");
          if (sameDay(cellDate, today)) classes.push("is-today");

          var isStart = false;
          var isEnd = false;
          if (bounds) {
            var cmpStart = compareDay(cellDate, bounds[0]);
            var cmpEnd = compareDay(cellDate, bounds[1]);
            isStart = cmpStart === 0;
            isEnd = cmpEnd === 0;
            if (cmpStart >= 0 && cmpEnd <= 0) {
              classes.push("is-in-range");
              if (isStart) classes.push("is-range-start");
              if (isEnd) classes.push("is-range-end");
              if (!isStart && !isEnd) classes.push("is-range-middle");
            }
          }

          var innerClass = "bb-range-cal-day-inner";
          if (isStart || isEnd) innerClass += " is-edge";

          html +=
            '<td class="' +
            classes.join(" ") +
            '" data-cal-day="' +
            formatYmd(cellDate) +
            '" data-cal-month="' +
            month +
            '">' +
            '<span class="' +
            innerClass +
            '">' +
            cellDate.getDate() +
            "</span></td>";
        }
        html += "</tr>";
      }
      html += "</tbody></table>";
      paneEl.innerHTML = html;
    }

    function render() {
      var leftMonth = viewMonth;
      var rightMonth = addMonths(viewMonth, 1);
      if (titleLeft) titleLeft.textContent = monthTitle(leftMonth);
      if (titleRight) titleRight.textContent = monthTitle(rightMonth);
      renderPane(paneEls[0], leftMonth);
      renderPane(paneEls[1], rightMonth);
    }

    function resetDraft() {
      startDate = null;
      endDate = null;
      pickingEnd = false;
      hoverDate = null;
      render();
      notifyChange();
    }

    function setRange(from, to) {
      startDate = from ? cloneDay(from) : null;
      endDate = to ? cloneDay(to) : null;
      pickingEnd = Boolean(startDate && !endDate);
      hoverDate = null;
      if (startDate) {
        viewMonth = new Date(startDate.getFullYear(), startDate.getMonth(), 1);
      }
      render();
      notifyChange();
    }

    function getRange() {
      if (!startDate || !endDate) return null;
      return { start: startDate, end: endDate };
    }

    function notifyChange() {
      if (options.onChange) options.onChange(getRange());
    }

    function onDayClick(day) {
      if (!startDate || (startDate && endDate)) {
        startDate = cloneDay(day);
        endDate = null;
        pickingEnd = true;
        hoverDate = null;
      } else {
        var range = normalizeRange(startDate, day);
        startDate = range[0];
        endDate = range[1];
        pickingEnd = false;
        hoverDate = null;
      }
      render();
      notifyChange();
    }

    mountEl.addEventListener("click", function (ev) {
      var btn = ev.target.closest(
        "[data-cal-prev-year], [data-cal-prev-month], [data-cal-next-month], [data-cal-next-year]"
      );
      if (!btn) return;
      ev.preventDefault();
      ev.stopPropagation();
      if (btn.hasAttribute("data-cal-prev-year")) viewMonth = addMonths(viewMonth, -12);
      if (btn.hasAttribute("data-cal-prev-month")) viewMonth = addMonths(viewMonth, -1);
      if (btn.hasAttribute("data-cal-next-month")) viewMonth = addMonths(viewMonth, 1);
      if (btn.hasAttribute("data-cal-next-year")) viewMonth = addMonths(viewMonth, 12);
      render();
    });

    mountEl.addEventListener("mousedown", function (ev) {
      if (ev.button !== 0) return;
      var cell = ev.target.closest("[data-cal-day]");
      if (!cell) return;
      ev.preventDefault();
      ev.stopPropagation();
      var day = parseYmd(cell.getAttribute("data-cal-day"));
      if (day) onDayClick(day);
    });

    mountEl.addEventListener("mouseover", function (ev) {
      if (!pickingEnd || !startDate || endDate) return;
      var cell = ev.target.closest("[data-cal-day]");
      if (!cell) return;
      var day = parseYmd(cell.getAttribute("data-cal-day"));
      if (!day) return;
      hoverDate = cloneDay(day);
      syncHoverHighlight();
    });

    mountEl.addEventListener("mouseleave", function (ev) {
      if (!mountEl.contains(ev.relatedTarget)) {
        hoverDate = null;
        if (pickingEnd && startDate && !endDate) render();
      }
    });

    return {
      render: render,
      resetDraft: resetDraft,
      clear: resetDraft,
      setRange: setRange,
      getRange: getRange,
    };
  }

  ready(function () {
    var root = qs("[data-payment-daterange]");
    if (!root) return;

    var form = document.getElementById("payment-record-filter-form");
    var trigger = qs("[data-daterange-trigger]", root);
    var panel = qs("[data-daterange-panel]", root);
    var labelEl = qs("[data-daterange-label]", root);
    var calMount = qs("[data-range-cal]", root);
    var hiddenFrom = form && form.querySelector('input[name="date_from"]');
    var hiddenTo = form && form.querySelector('input[name="date_to"]');
    var btnApply = qs("[data-daterange-apply]", root);
    var btnClear = qs("[data-daterange-clear]", root);

    var committedFrom = null;
    var committedTo = null;
    var calendar = null;

    function syncHidden() {
      if (hiddenFrom) hiddenFrom.value = committedFrom ? formatYmd(committedFrom) : "";
      if (hiddenTo) hiddenTo.value = committedTo ? formatYmd(committedTo) : "";
    }

    function updateLabel() {
      if (!labelEl) return;
      var a = committedFrom ? formatYmd(committedFrom) : "";
      var b = committedTo ? formatYmd(committedTo) : "";
      if (a && b) labelEl.textContent = a + " 至 " + b;
      else if (a) labelEl.textContent = a + " 起";
      else if (b) labelEl.textContent = "至 " + b;
      else labelEl.textContent = "选择时间区间";
    }

    function updateApplyButton() {
      if (!btnApply || !calendar) return;
      btnApply.disabled = !calendar.getRange();
    }

    function openPanel() {
      if (!panel) return;
      calendar.setRange(
        committedFrom ? cloneDay(committedFrom) : null,
        committedTo ? cloneDay(committedTo) : null
      );
      panel.removeAttribute("hidden");
      if (trigger) trigger.setAttribute("aria-expanded", "true");
      updateApplyButton();
    }

    function closePanel(revertDraft) {
      if (!panel) return;
      if (revertDraft) {
        calendar.setRange(
          committedFrom ? cloneDay(committedFrom) : null,
          committedTo ? cloneDay(committedTo) : null
        );
      }
      panel.setAttribute("hidden", "");
      if (trigger) trigger.setAttribute("aria-expanded", "false");
    }

    committedFrom = hiddenFrom && hiddenFrom.value ? parseYmd(hiddenFrom.value) : null;
    committedTo = hiddenTo && hiddenTo.value ? parseYmd(hiddenTo.value) : null;
    syncHidden();
    updateLabel();

    calendar = buildRangeCalendar(calMount, {
      onChange: updateApplyButton,
    });
    calendar.render();
    updateApplyButton();

    if (trigger) {
      trigger.addEventListener("click", function (ev) {
        ev.stopPropagation();
        if (panel && panel.hasAttribute("hidden")) openPanel();
        else closePanel(true);
      });
    }

    if (btnApply) {
      btnApply.addEventListener("click", function (ev) {
        ev.stopPropagation();
        var range = calendar.getRange();
        if (!range) return;
        committedFrom = range.start;
        committedTo = range.end;
        syncHidden();
        updateLabel();
        closePanel(false);
      });
    }

    if (btnClear) {
      btnClear.addEventListener("click", function (ev) {
        ev.stopPropagation();
        calendar.clear();
      });
    }

    if (panel) {
      panel.addEventListener("click", function (ev) {
        ev.stopPropagation();
      });
    }

    document.addEventListener("click", function (ev) {
      if (!root.contains(ev.target)) closePanel(true);
    });

    if (form) {
      form.addEventListener("submit", syncHidden);
    }
  });
})();
