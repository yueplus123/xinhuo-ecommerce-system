(function () {
  var PRICE_TYPE_UI = {
    "": {
      hint: "请先选择价格类型，下方将显示对应的填写方式。",
      mode: "none",
      showLabel: false,
      labelText: "档位标签",
      amountText: "人民币（元）",
      showGroupNotice: false,
    },
    cny_single: {
      hint: "单一人民币：只需填写一行「人民币」金额，无需档位名称。",
      mode: "single",
      showLabel: false,
      labelText: "档位标签",
      amountText: "人民币（元）",
      showGroupNotice: false,
    },
    usd_single: {
      hint: "美金（单一）：填一行。左侧写美金金额（如 9.99），右侧写折算人民币。",
      mode: "single",
      showLabel: true,
      labelText: "美金（USD）",
      amountText: "折算人民币（元）",
      showGroupNotice: true,
    },
    usd_tier: {
      hint: "美金（多档）：每行一档。左侧写美金档位，右侧写对应人民币，可添加多行。",
      mode: "multi",
      showLabel: true,
      labelText: "美金档位",
      amountText: "折算人民币（元）",
      showGroupNotice: true,
    },
    package: {
      hint: "套餐：每行一个套餐。左侧写套餐名称，右侧写人民币价格，可添加多行。",
      mode: "multi",
      showLabel: true,
      labelText: "套餐名称",
      amountText: "人民币（元）",
      showGroupNotice: true,
    },
    jpy_recharge: {
      hint: "日元充值：每行一档。左侧写日元数量（如 1000），右侧写人民币，可添加多行。",
      mode: "multi",
      showLabel: true,
      labelText: "日元档位",
      amountText: "人民币（元）",
      showGroupNotice: true,
    },
    usd_proxy: {
      hint: "按美金代付收费：费率见资源池「美金代付价格池」，此处无需填写价格档位。",
      mode: "none",
      showLabel: false,
      labelText: "档位标签",
      amountText: "人民币（元）",
      showGroupNotice: false,
    },
  };

  function qs(sel, root) {
    return (root || document).querySelector(sel);
  }

  function qsa(sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  }

  function rowHasData(row) {
    var amount = qs('input[name$="-rmb_amount"]', row);
    var label = qs('input[name$="-label"]', row);
    var amt = amount && String(amount.value || "").trim();
    var lab = label && String(label.value || "").trim();
    return !!(amt || lab);
  }

  function applyPriceTypeUI() {
    var select = qs("#id_price_type");
    var section = qs("[data-sku-price-section]");
    if (!select || !section) return;

    var type = select.value || "";
    var cfg = PRICE_TYPE_UI[type] || PRICE_TYPE_UI[""];

    var hint = qs("[data-price-type-hint]", section);
    if (hint) hint.textContent = cfg.hint;

    var groupNotice = qs("[data-price-group-notice]", section);
    if (groupNotice) {
      groupNotice.style.display = cfg.showGroupNotice ? "" : "none";
    }

    var labelCol = qs("[data-price-col-label]", section);
    var amountCol = qs("[data-price-col-amount]", section);
    if (labelCol) {
      labelCol.textContent = cfg.labelText;
      labelCol.style.display = cfg.showLabel ? "" : "none";
    }
    if (amountCol) amountCol.textContent = cfg.amountText;

    var rows = qsa(".sku-price-item-row", section);
    var addBtn = qs("[data-price-add-row]", section);
    var itemsWrap = qs(".sku-price-items", section);
    var header = qs(".sku-price-items-header", section);

    rows.forEach(function (row) {
      var labelField = qs(".bb-field-price-label", row);
      if (labelField) {
        if (cfg.showLabel) labelField.classList.remove("hidden-col");
        else labelField.classList.add("hidden-col");
      }
    });

    if (cfg.mode === "none") {
      if (itemsWrap) itemsWrap.style.display = "none";
      if (header) header.style.display = "none";
      if (addBtn) addBtn.style.display = "none";
      return;
    }
    if (header) header.style.display = "";
    if (itemsWrap) itemsWrap.style.display = "";

    rows.forEach(function (row, idx) {
      var deleteCol = qs(".sku-delete-col", row);
      var deleted = qs('input[name$="-DELETE"]', row);
      var isDeleted = deleted && deleted.checked;

      if (cfg.mode === "single") {
        var show = idx === 0 && !isDeleted;
        row.style.display = show ? "" : "none";
        if (deleteCol) deleteCol.style.display = "none";
      } else {
        row.style.display = isDeleted ? "none" : "";
        if (deleteCol) deleteCol.style.display = idx === 0 && !rowHasData(row) ? "none" : "";
      }
    });

    if (addBtn) addBtn.style.display = cfg.mode === "multi" ? "" : "none";
  }

  function addPriceRow() {
    var section = qs("[data-sku-price-section]");
    if (!section) return;
    var totalInput = qs('input[name$="-TOTAL_FORMS"]', section);
    var rows = qsa(".sku-price-item-row", section);
    if (!totalInput || !rows.length) return;

    var template = rows[rows.length - 1];
    var clone = template.cloneNode(true);
    var nextIdx = parseInt(totalInput.value, 10) || rows.length;

    qsa("input, textarea, select", clone).forEach(function (el) {
      if (!el.name) return;
      el.name = el.name.replace(/-\d+-/, "-" + nextIdx + "-");
      el.id = el.id ? el.id.replace(/_\d+_/, "_" + nextIdx + "_") : "";
      if (el.type === "checkbox") el.checked = false;
      else if (el.type === "hidden" && el.name.endsWith("-id")) el.value = "";
      else if (el.tagName === "SELECT") el.selectedIndex = 0;
      else el.value = "";
    });

    qsa("label[for]", clone).forEach(function (lab) {
      var f = lab.getAttribute("for");
      if (f) lab.setAttribute("for", f.replace(/_\d+_/, "_" + nextIdx + "_"));
    });

    clone.style.display = "";
    template.parentNode.appendChild(clone);
    totalInput.value = String(nextIdx + 1);
    applyPriceTypeUI();
  }

  document.addEventListener("DOMContentLoaded", function () {
    var select = qs("#id_price_type");
    if (select) {
      select.addEventListener("change", applyPriceTypeUI);
    }
    var addBtn = qs("[data-price-add-row]");
    if (addBtn) {
      addBtn.addEventListener("click", function (ev) {
        ev.preventDefault();
        addPriceRow();
      });
    }
    qsa('input[name$="-DELETE"]').forEach(function (cb) {
      cb.addEventListener("change", applyPriceTypeUI);
    });
    applyPriceTypeUI();
  });
})();
