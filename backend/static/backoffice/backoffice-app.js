(function () {
  "use strict";

  var bootEl = document.getElementById("bb-boot");
  var boot = { nav: [], activeKey: "", username: "", logoutUrl: "/accounts/logout/", messages: [] };
  if (bootEl && bootEl.textContent) {
    try {
      boot = JSON.parse(bootEl.textContent);
    } catch (err) {
      console.error("backoffice boot JSON parse failed", err);
    }
  }

  var pageTitle = document.title.replace(/\s*·\s*薪火电商\s*$/, "").trim() || "管理后台";
  var collapseKey = "bb-aside-collapsed";
  var savedCollapse = false;
  try {
    savedCollapse = localStorage.getItem(collapseKey) === "1";
  } catch (e) {}

  var VueGlobal = window.Vue;
  var ElementPlus = window.ElementPlus;
  var Icons = window.ElementPlusIconsVue || {};

  if (!VueGlobal || !ElementPlus) {
    console.error("Vue / Element Plus CDN failed to load");
    return;
  }

  var app = VueGlobal.createApp({
    delimiters: ["[[", "]]"],
    data: function () {
      return {
        nav: boot.nav || [],
        activeKey: boot.activeKey || "",
        username: boot.username || "",
        logoutUrl: boot.logoutUrl || "/accounts/logout/",
        isCollapse: savedCollapse,
        pageTitle: pageTitle,
      };
    },
    computed: {
      asideWidth: function () {
        return this.isCollapse ? "64px" : "210px";
      },
    },
    methods: {
      toggleCollapse: function () {
        this.isCollapse = !this.isCollapse;
        try {
          localStorage.setItem(collapseKey, this.isCollapse ? "1" : "0");
        } catch (e) {}
      },
      onNavSelect: function (key) {
        var item = (this.nav || []).find(function (n) {
          return n.key === key;
        });
        if (item && item.url) {
          window.location.href = item.url;
        }
      },
      logout: function () {
        var token = "";
        var csrfInput = document.querySelector("[name=csrfmiddlewaretoken]");
        if (csrfInput && csrfInput.value) {
          token = csrfInput.value;
        } else {
          var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
          if (match) {
            token = decodeURIComponent(match[1]);
          }
        }
        var form = document.createElement("form");
        form.method = "POST";
        form.action = this.logoutUrl;
        form.style.display = "none";
        if (token) {
          var input = document.createElement("input");
          input.type = "hidden";
          input.name = "csrfmiddlewaretoken";
          input.value = token;
          form.appendChild(input);
        }
        document.body.appendChild(form);
        form.submit();
      },
      flashMessages: function () {
        var list = boot.messages || [];
        if (!list.length || !ElementPlus.ElMessage) return;
        list.forEach(function (msg) {
          var level = (msg.level || "info").toLowerCase();
          var text = msg.text || "";
          if (!text) return;
          if (level.indexOf("error") >= 0) ElementPlus.ElMessage.error(text);
          else if (level.indexOf("success") >= 0) ElementPlus.ElMessage.success(text);
          else if (level.indexOf("warning") >= 0) ElementPlus.ElMessage.warning(text);
          else ElementPlus.ElMessage.info(text);
        });
      },
    },
    mounted: function () {
      this.flashMessages();
    },
  });

  app.use(ElementPlus);
  if (Icons.Fold) app.component("Fold", Icons.Fold);
  if (Icons.Expand) app.component("Expand", Icons.Expand);

  app.mount("#bb-app");
})();
