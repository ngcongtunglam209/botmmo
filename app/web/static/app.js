// Tương tác tối thiểu: toast, đổi nền, thu/mở thanh bên, xác nhận thao tác
// nguy hiểm, và bảng lệnh Ctrl/⌘+K để nhảy trang.
// Mọi form vẫn gửi được bình thường khi tắt JavaScript.

(function () {
  "use strict";

  var doc = document;
  var shell = doc.querySelector("[data-shell]");

  // --- Toast ---------------------------------------------------------------

  function showToast(message, isError) {
    var box = doc.getElementById("toasts");
    if (!box || !message) return;
    var toast = doc.createElement("div");
    toast.className = "toast" + (isError ? " error" : "");
    toast.textContent = message;
    box.appendChild(toast);
    setTimeout(function () { toast.remove(); }, 6000);
  }

  var flashNode = doc.getElementById("flash-data");
  if (flashNode) {
    try {
      var flash = JSON.parse(flashNode.textContent);
      showToast(flash.message, flash.error);
      // Bỏ query để F5 không hiện lại thông báo cũ.
      var url = new URL(window.location.href);
      url.searchParams.delete("msg");
      url.searchParams.delete("err");
      window.history.replaceState({}, "", url.pathname + url.search + url.hash);
    } catch (error) {
      /* thông báo hỏng thì bỏ qua */
    }
  }

  // --- Nền sáng / tối ------------------------------------------------------

  var themeButton = doc.querySelector("[data-theme-toggle]");
  if (themeButton) {
    var themeIcon = themeButton.querySelector("[data-theme-icon]");
    var syncTheme = function () {
      var light = doc.documentElement.classList.contains("light");
      if (themeIcon) themeIcon.setAttribute("href", light ? "#i-sun" : "#i-moon");
      themeButton.setAttribute("aria-pressed", String(light));
    };
    themeButton.addEventListener("click", function () {
      var light = doc.documentElement.classList.toggle("light");
      localStorage.setItem("admin_theme", light ? "light" : "dark");
      syncTheme();
    });
    syncTheme();
  }

  // --- Thanh bên -----------------------------------------------------------

  if (shell && doc.documentElement.classList.contains("rail-collapsed")) {
    shell.classList.add("is-collapsed");
  }

  var collapseButton = doc.querySelector("[data-rail-collapse]");
  if (collapseButton && shell) {
    collapseButton.addEventListener("click", function () {
      var collapsed = shell.classList.toggle("is-collapsed");
      localStorage.setItem("admin_rail", collapsed ? "collapsed" : "open");
      collapseButton.setAttribute("aria-pressed", String(collapsed));
    });
  }

  var railButton = doc.querySelector("[data-rail-toggle]");
  if (railButton && shell) {
    railButton.addEventListener("click", function () {
      var open = shell.classList.toggle("is-open");
      railButton.setAttribute("aria-expanded", String(open));
    });
    // Bấm ra ngoài thanh bên trên màn hình hẹp thì đóng lại.
    doc.addEventListener("click", function (event) {
      if (!shell.classList.contains("is-open")) return;
      if (event.target.closest("[data-rail], [data-rail-toggle]")) return;
      shell.classList.remove("is-open");
      railButton.setAttribute("aria-expanded", "false");
    });
  }

  // --- Xác nhận thao tác nguy hiểm ----------------------------------------

  var pendingForm = null;

  function closeSheet() {
    var sheet = doc.querySelector(".sheet");
    if (sheet) sheet.remove();
    pendingForm = null;
  }

  function askConfirm(form, message) {
    closeSheet();
    var sheet = doc.createElement("div");
    sheet.className = "sheet";
    sheet.setAttribute("role", "dialog");
    sheet.setAttribute("aria-modal", "true");
    sheet.innerHTML =
      '<div class="sheet__box">' +
      '<div class="sheet__body"><h2>Xác nhận thao tác</h2><p></p></div>' +
      '<div class="sheet__foot">' +
      '<button type="button" class="btn btn--ghost" data-sheet-cancel>Hủy</button>' +
      '<button type="button" class="btn btn--danger" data-sheet-ok>Thực hiện</button>' +
      "</div></div>";
    sheet.querySelector("p").textContent = message;
    doc.body.appendChild(sheet);
    pendingForm = form;

    sheet.querySelector("[data-sheet-ok]").focus();
    sheet.addEventListener("click", function (event) {
      if (event.target === sheet || event.target.closest("[data-sheet-cancel]")) {
        closeSheet();
        return;
      }
      if (event.target.closest("[data-sheet-ok]")) {
        var target = pendingForm;
        closeSheet();
        if (target) {
          target.dataset.confirmed = "1";
          // requestSubmit giữ nguyên nút submit và validation của form.
          if (target.requestSubmit) target.requestSubmit();
          else target.submit();
        }
      }
    });
  }

  doc.addEventListener(
    "submit",
    function (event) {
      var form = event.target.closest("form");
      if (!form || !form.dataset.confirm) return;
      if (form.dataset.confirmed === "1") {
        delete form.dataset.confirmed;
        return;
      }
      event.preventDefault();
      event.stopImmediatePropagation();
      askConfirm(form, form.dataset.confirm);
    },
    true
  );

  // --- Bảng lệnh (Ctrl/⌘ + K) ---------------------------------------------

  var navItems = [];
  var navNode = doc.getElementById("nav-data");
  if (navNode) {
    try {
      JSON.parse(navNode.textContent).forEach(function (group) {
        group[1].forEach(function (item) {
          navItems.push({ href: item[0], label: item[1], icon: item[2], group: group[0] });
        });
      });
    } catch (error) {
      /* thiếu dữ liệu điều hướng thì bỏ bảng lệnh */
    }
  }

  var palette = null;
  var paletteIndex = 0;
  var paletteMatches = [];

  // Bỏ dấu để gõ "don hang" vẫn ra "Đơn hàng". NFD không tách được đ/Đ nên
  // xử lý riêng; \p{Diacritic} lo phần dấu thanh và dấu mũ.
  function fold(text) {
    return text
      .normalize("NFD")
      .replace(/\p{Diacritic}/gu, "")
      .replace(/đ/g, "d")
      .replace(/Đ/g, "D")
      .toLowerCase();
  }

  function renderPalette(query) {
    var list = palette.querySelector(".palette__list");
    var needle = fold(query.trim());
    paletteMatches = navItems.filter(function (item) {
      return !needle || fold(item.label + " " + item.group + " " + item.href).indexOf(needle) !== -1;
    });
    paletteIndex = 0;
    if (!paletteMatches.length) {
      list.innerHTML = '<p class="palette__empty">Không có trang nào khớp.</p>';
      return;
    }
    list.innerHTML = paletteMatches
      .map(function (item, index) {
        return (
          '<a class="palette__item" role="option" href="' + item.href + '"' +
          (index === 0 ? ' aria-selected="true"' : "") + ">" +
          '<svg aria-hidden="true"><use href="#i-' + item.icon + '"></use></svg>' +
          "<span></span>" +
          '<span class="hint"></span></a>'
        );
      })
      .join("");
    var nodes = list.querySelectorAll(".palette__item");
    paletteMatches.forEach(function (item, index) {
      nodes[index].querySelectorAll("span")[0].textContent = item.label;
      nodes[index].querySelector(".hint").textContent = item.group;
    });
  }

  function moveSelection(step) {
    if (!paletteMatches.length) return;
    var nodes = palette.querySelectorAll(".palette__item");
    nodes[paletteIndex].removeAttribute("aria-selected");
    paletteIndex = (paletteIndex + step + nodes.length) % nodes.length;
    nodes[paletteIndex].setAttribute("aria-selected", "true");
    nodes[paletteIndex].scrollIntoView({ block: "nearest" });
  }

  function closePalette() {
    if (palette) palette.remove();
    palette = null;
  }

  function openPalette() {
    if (palette || !navItems.length) return;
    palette = doc.createElement("div");
    palette.className = "palette";
    palette.innerHTML =
      '<div class="palette__box">' +
      '<input class="palette__input" type="text" placeholder="Nhảy tới trang…" ' +
      'aria-label="Tìm trang" autocomplete="off" spellcheck="false">' +
      '<div class="palette__list" role="listbox"></div>' +
      "</div>";
    doc.body.appendChild(palette);
    renderPalette("");

    var input = palette.querySelector(".palette__input");
    input.focus();
    input.addEventListener("input", function () { renderPalette(input.value); });

    palette.addEventListener("click", function (event) {
      if (event.target === palette) closePalette();
    });
    palette.addEventListener("keydown", function (event) {
      if (event.key === "ArrowDown") { event.preventDefault(); moveSelection(1); }
      else if (event.key === "ArrowUp") { event.preventDefault(); moveSelection(-1); }
      else if (event.key === "Enter") {
        event.preventDefault();
        var current = palette.querySelectorAll(".palette__item")[paletteIndex];
        if (current) window.location.href = current.getAttribute("href");
      }
    });
  }

  var paletteButton = doc.querySelector("[data-palette-open]");
  if (paletteButton) paletteButton.addEventListener("click", openPalette);

  doc.addEventListener("keydown", function (event) {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      if (palette) closePalette();
      else openPalette();
      return;
    }
    if (event.key === "Escape") {
      closePalette();
      closeSheet();
    }
  });
})();
