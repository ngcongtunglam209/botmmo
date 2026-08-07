(() => {
  const toast = document.querySelector(".toast");
  const showToast = (message = "Đã sao chép") => {
    toast.textContent = message;
    toast.classList.add("show");
    window.setTimeout(() => toast.classList.remove("show"), 1600);
  };

  document.querySelectorAll(".copy").forEach((button) => {
    button.addEventListener("click", async () => {
      const target = button.dataset.copyTarget;
      const value = target
        ? document.getElementById(target)?.innerText
        : button.dataset.copy;
      if (!value) return;
      try {
        await navigator.clipboard.writeText(value);
        showToast();
      } catch {
        showToast("Không thể sao chép");
      }
    });
  });

  document.querySelectorAll("[data-tab]").forEach((button) => {
    button.addEventListener("click", () => {
      const tab = button.dataset.tab;
      document.querySelectorAll("[data-tab]").forEach((item) => item.classList.toggle("active", item === button));
      document.querySelectorAll("[data-panel]").forEach((panel) => panel.classList.toggle("active", panel.dataset.panel === tab));
    });
  });

  const search = document.getElementById("docs-search");
  const searchable = [...document.querySelectorAll("main section[data-search], .endpoint-list article")];
  const runSearch = () => {
    const query = search.value.trim().toLocaleLowerCase("vi");
    searchable.forEach((item) => {
      const haystack = `${item.dataset.search || ""} ${item.textContent}`.toLocaleLowerCase("vi");
      item.classList.toggle("search-hidden", Boolean(query) && !haystack.includes(query));
    });
  };
  search.addEventListener("input", runSearch);
  window.addEventListener("keydown", (event) => {
    if (event.key === "/" && document.activeElement !== search) {
      event.preventDefault();
      search.focus();
    }
    if (event.key === "Escape") {
      search.value = "";
      runSearch();
      search.blur();
    }
  });

  const menuButton = document.querySelector(".menu-button");
  const sidebar = document.querySelector(".sidebar");
  menuButton.addEventListener("click", () => {
    const open = sidebar.classList.toggle("open");
    menuButton.setAttribute("aria-expanded", String(open));
  });
  sidebar.querySelectorAll("a").forEach((link) => link.addEventListener("click", () => {
    sidebar.classList.remove("open");
    menuButton.setAttribute("aria-expanded", "false");
  }));

  const sections = [...document.querySelectorAll("main section[id]")];
  const navLinks = [...document.querySelectorAll(".sidebar nav a")];
  const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) entry.target.classList.add("visible");
    });
  }, { threshold: 0.08 });
  document.querySelectorAll(".reveal").forEach((item) => revealObserver.observe(item));

  const spyObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      navLinks.forEach((link) => link.classList.toggle("active", link.getAttribute("href") === `#${entry.target.id}`));
    });
  }, { rootMargin: "-25% 0px -65% 0px" });
  sections.forEach((section) => spyObserver.observe(section));
})();
