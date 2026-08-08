// Tương tác tối thiểu: toast, đổi theme, menu mobile, xác nhận thao tác nguy hiểm.
// Mọi form vẫn hoạt động khi tắt JavaScript.

(function () {
  "use strict";

  function showToast(message, isError) {
    const container = document.getElementById("toasts");
    if (!container || !message) return;
    const toast = document.createElement("div");
    toast.className = "toast" + (isError ? " error" : "");
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(function () { toast.remove(); }, 5000);
  }

  // Thông báo sau khi redirect từ một action.
  const flashNode = document.getElementById("flash-data");
  if (flashNode) {
    try {
      const flash = JSON.parse(flashNode.textContent);
      showToast(flash.message, flash.error);
      // Bỏ query để F5 không hiện lại thông báo cũ.
      const url = new URL(window.location.href);
      url.searchParams.delete("msg");
      url.searchParams.delete("err");
      window.history.replaceState({}, "", url.pathname + url.search + url.hash);
    } catch (error) {
      /* thông báo hỏng thì bỏ qua */
    }
  }

  // Đổi nền sáng/tối.
  const themeButton = document.querySelector("[data-theme-toggle]");
  if (themeButton) {
    const sync = function () {
      themeButton.textContent = document.documentElement.classList.contains("light") ? "◑" : "◐";
    };
    themeButton.addEventListener("click", function () {
      const light = document.documentElement.classList.toggle("light");
      localStorage.setItem("admin_theme", light ? "light" : "dark");
      sync();
    });
    sync();
  }

  // Menu trên màn hình hẹp.
  const menuButton = document.querySelector("[data-menu-toggle]");
  const nav = document.querySelector("[data-nav]");
  if (menuButton && nav) {
    menuButton.addEventListener("click", function () {
      const open = nav.classList.toggle("is-open");
      menuButton.setAttribute("aria-expanded", String(open));
    });
  }

  // Xác nhận trước khi gửi form có data-confirm.
  document.addEventListener("submit", function (event) {
    const form = event.target.closest("form");
    if (!form || !form.dataset.confirm) return;
    if (!window.confirm(form.dataset.confirm)) {
      event.preventDefault();
      event.stopImmediatePropagation();
    }
  }, true);
})();
