(function () {
  function qs(sel, root) {
    return (root || document).querySelector(sel);
  }

  function qsa(sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  }

  function readJson(id) {
    var el = document.getElementById(id);
    if (!el) return [];
    try {
      return JSON.parse(el.textContent);
    } catch (e) {
      return [];
    }
  }

  function escapeHtml(text) {
    return String(text || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function normalize(text) {
    return String(text || "").toLowerCase().trim();
  }

  function matchesQuery(item, query, mode) {
    if (!query) return true;
    var name = normalize(item.name);
    if (name.indexOf(query) !== -1) return true;
    if (mode === "phrase") {
      return normalize(item.content).indexOf(query) !== -1;
    }
    return false;
  }

  document.addEventListener("DOMContentLoaded", function () {
    var section = qs("[data-phrase-tutorial-section]");
    if (!section) return;

    var pickerBoot = window.SKU_POOL_PICKER || {};
    var phrasePool = Array.isArray(pickerBoot.phrasePool) ? pickerBoot.phrasePool : readJson("phrase-pool-data");
    var tutorialPool = Array.isArray(pickerBoot.tutorialPool) ? pickerBoot.tutorialPool : readJson("tutorial-pool-data");
    var phrasePrefix = pickerBoot.phrasePrefix || "quickphrase_set";

    var phraseList = qs("[data-phrase-list]", section);
    var tutorialList = qs("[data-tutorial-list]", section);
    var phraseEmpty = qs("[data-phrase-empty]", section);
    var tutorialEmpty = qs("[data-tutorial-empty]", section);
    var totalFormsInput = document.getElementById("id_" + phrasePrefix + "-TOTAL_FORMS");

    var modal = document.getElementById("pool-picker-modal");
    var searchInput = document.getElementById("pool-picker-search");
    var resultsEl = qs("[data-pool-picker-results]", modal);
    var noResultEl = qs("[data-pool-picker-no-result]", modal);
    var titleEl = document.getElementById("pool-picker-title");
    var descEl = qs("[data-pool-picker-desc]", modal);

    var activeMode = null;
    var pickedIds = {};

    function updatePhraseEmpty() {
      if (!phraseEmpty || !phraseList) return;
      var visible = qsa("[data-phrase-row]", phraseList).filter(function (row) {
        return !row.classList.contains("is-removed");
      });
      phraseEmpty.hidden = visible.length > 0;
    }

    function updateTutorialEmpty() {
      if (!tutorialEmpty || !tutorialList) return;
      tutorialEmpty.hidden = tutorialList.children.length > 0;
    }

    function getPhraseContents() {
      return qsa("[data-phrase-row]", phraseList)
        .filter(function (row) {
          return !row.classList.contains("is-removed");
        })
        .map(function (row) {
          var input = qs('input[name$="-content"]', row);
          return normalize(input && input.value);
        })
        .filter(Boolean);
    }

    function getTutorialIds() {
      return qsa("[data-tutorial-id]", tutorialList).map(function (row) {
        return String(row.dataset.tutorialId);
      });
    }

    function bindPhraseRemove(row) {
      var btn = qs("[data-remove-phrase]", row);
      if (!btn) return;
      btn.addEventListener("click", function () {
        var deleteField = qs(".phrase-delete-field", row);
        var idField = qs('input[name$="-id"]', row);
        if (idField && idField.value) {
          row.classList.add("is-removed");
          row.hidden = true;
          if (deleteField) deleteField.value = "on";
        } else {
          row.remove();
          if (totalFormsInput) {
            totalFormsInput.value = String(qsa("[data-phrase-row]", phraseList).length);
          }
        }
        updatePhraseEmpty();
      });
    }

    function addPhraseRow(content, poolName) {
      if (!phraseList || !totalFormsInput) return;
      var trimmed = String(content || "").trim();
      if (trimmed) {
        var existing = getPhraseContents();
        if (existing.indexOf(normalize(trimmed)) !== -1) return;
      }

      var idx = qsa("[data-phrase-row]", phraseList).length;
      var row = document.createElement("div");
      row.className = "pool-selected-card pool-selected-card--phrase";
      row.dataset.phraseRow = "";
      if (poolName) row.dataset.poolName = poolName;

      var main = document.createElement("div");
      main.className = "pool-selected-card-main";

      if (poolName) {
        var title = document.createElement("div");
        title.className = "pool-selected-card-title";
        title.textContent = poolName;
        main.appendChild(title);
      }

      var contentInput = document.createElement("input");
      contentInput.type = "hidden";
      contentInput.name = phrasePrefix + "-" + idx + "-content";
      contentInput.value = trimmed;
      main.appendChild(contentInput);

      var text = document.createElement("div");
      text.className = "pool-selected-text";
      text.textContent = trimmed;
      main.appendChild(text);

      var orderInput = document.createElement("input");
      orderInput.type = "hidden";
      orderInput.name = phrasePrefix + "-" + idx + "-order";
      orderInput.value = String((idx + 1) * 10);
      main.appendChild(orderInput);

      var deleteInput = document.createElement("input");
      deleteInput.type = "hidden";
      deleteInput.className = "phrase-delete-field";
      deleteInput.name = phrasePrefix + "-" + idx + "-DELETE";
      deleteInput.value = "";
      main.appendChild(deleteInput);

      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "bb-btn bb-btn-danger pool-selected-delete";
      btn.dataset.removePhrase = "";
      btn.textContent = "删除";

      row.appendChild(main);
      row.appendChild(btn);
      phraseList.appendChild(row);
      totalFormsInput.value = String(idx + 1);
      bindPhraseRemove(row);
      updatePhraseEmpty();
    }

    function addTutorialCard(item) {
      if (!tutorialList) return;
      if (getTutorialIds().indexOf(String(item.id)) !== -1) return;

      var row = document.createElement("div");
      row.className = "pool-selected-card pool-selected-card--tutorial";
      row.dataset.tutorialId = String(item.id);

      var main = document.createElement("div");
      main.className = "pool-selected-card-main";

      var title = document.createElement("div");
      title.className = "pool-selected-card-title";
      title.textContent = item.name;
      main.appendChild(title);

      if (item.detail_url) {
        var link = document.createElement("a");
        link.className = "pool-selected-link";
        link.href = item.detail_url;
        link.target = "_blank";
        link.rel = "noopener";
        link.textContent = "查看链接";
        main.appendChild(link);
      }

      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "bb-btn bb-btn-danger pool-selected-delete";
      btn.dataset.removeTutorial = "";
      btn.textContent = "删除";

      var input = document.createElement("input");
      input.type = "checkbox";
      input.name = "tutorial_pool";
      input.value = String(item.id);
      input.checked = true;
      input.hidden = true;
      input.className = "tutorial-pool-input";

      row.appendChild(main);
      row.appendChild(btn);
      row.appendChild(input);
      tutorialList.appendChild(row);
      bindTutorialRemove(row);
      updateTutorialEmpty();
    }

    function bindTutorialRemove(row) {
      var btn = qs("[data-remove-tutorial]", row);
      if (!btn) return;
      btn.addEventListener("click", function () {
        row.remove();
        updateTutorialEmpty();
      });
    }

    qsa("[data-phrase-row]", phraseList).forEach(bindPhraseRemove);
    qsa("[data-tutorial-id]", tutorialList).forEach(bindTutorialRemove);
    updatePhraseEmpty();
    updateTutorialEmpty();

    function renderResults() {
      if (!resultsEl || !searchInput) return;
      var query = normalize(searchInput.value);
      var pool = activeMode === "phrase" ? phrasePool : tutorialPool;
      var selectedPhraseContents = getPhraseContents();
      var selectedTutorialIds = getTutorialIds();

      var html = [];
      pool.forEach(function (item) {
        if (!matchesQuery(item, query, activeMode)) return;
        var id = String(item.id);
        var disabled = false;
        var reason = "";
        if (activeMode === "phrase") {
          if (selectedPhraseContents.indexOf(normalize(item.content)) !== -1) {
            disabled = true;
            reason = "已添加";
          }
        } else if (selectedTutorialIds.indexOf(id) !== -1) {
          disabled = true;
          reason = "已添加";
        }

        var checked = !!pickedIds[id];
        html.push(
          '<label class="pool-picker-result' +
            (disabled ? " is-disabled" : "") +
            '">' +
            '<input type="checkbox" class="pool-picker-result-check" value="' +
            escapeHtml(id) +
            '"' +
            (disabled ? " disabled" : checked ? " checked" : "") +
            ">" +
            '<span class="pool-picker-result-body">' +
            '<span class="pool-picker-result-name">' +
            escapeHtml(item.name) +
            "</span>" +
            (activeMode === "phrase" && item.content
              ? '<span class="pool-picker-result-meta">' + escapeHtml(item.content) + "</span>"
              : activeMode === "tutorial" && item.detail_url
              ? '<span class="pool-picker-result-meta">' + escapeHtml(item.detail_url) + "</span>"
              : "") +
            (reason ? '<span class="pool-picker-result-tag">' + reason + "</span>" : "") +
            "</span></label>"
        );
      });

      resultsEl.innerHTML = html.join("");
      if (noResultEl) noResultEl.hidden = html.length > 0;
    }

    function openModal(mode) {
      if (!modal) return;
      activeMode = mode;
      pickedIds = {};
      if (titleEl) {
        titleEl.textContent = mode === "phrase" ? "从话术池搜索" : "从教程池搜索";
      }
      if (descEl) {
        descEl.textContent =
          mode === "phrase"
            ? "搜索名称或内容，勾选后添加到左侧列表。"
            : "搜索教程名称，勾选后添加到右侧列表。";
      }
      if (searchInput) {
        searchInput.value = "";
        searchInput.placeholder = mode === "phrase" ? "搜索话术名称或内容…" : "搜索教程名称…";
      }
      renderResults();
      modal.removeAttribute("hidden");
      document.body.style.overflow = "hidden";
      window.setTimeout(function () {
        if (searchInput) searchInput.focus();
      }, 50);
    }

    function closeModal() {
      if (!modal) return;
      modal.setAttribute("hidden", "");
      document.body.style.overflow = "";
      activeMode = null;
      pickedIds = {};
    }

    qsa("[data-open-pool-picker]", section).forEach(function (btn) {
      btn.addEventListener("click", function () {
        openModal(btn.getAttribute("data-open-pool-picker"));
      });
    });

    var closeBtn = qs("[data-close-pool-picker]", modal);
    if (closeBtn) closeBtn.addEventListener("click", closeModal);

    if (modal) {
      modal.addEventListener("click", function (ev) {
        if (ev.target === modal) closeModal();
      });
    }

    if (searchInput) {
      searchInput.addEventListener("input", renderResults);
    }

    if (resultsEl) {
      resultsEl.addEventListener("change", function (ev) {
        var input = ev.target;
        if (!input.classList.contains("pool-picker-result-check")) return;
        var id = input.value;
        if (input.checked) pickedIds[id] = true;
        else delete pickedIds[id];
      });
    }

    var confirmBtn = qs("[data-pool-picker-confirm]", modal);
    if (confirmBtn) {
      confirmBtn.addEventListener("click", function () {
        var pool = activeMode === "phrase" ? phrasePool : tutorialPool;
        var byId = {};
        pool.forEach(function (item) {
          byId[String(item.id)] = item;
        });
        Object.keys(pickedIds).forEach(function (id) {
          var item = byId[id];
          if (!item) return;
          if (activeMode === "phrase") addPhraseRow(item.content, item.name);
          else addTutorialCard(item);
        });
        closeModal();
      });
    }

    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape" && modal && !modal.hasAttribute("hidden")) closeModal();
    });
  });
})();
