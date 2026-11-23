(function () {
  "use strict";

  function ready(callback) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", callback);
    } else {
      callback();
    }
  }

  function initNavigation() {
    var sidebar = document.getElementById("sidebar");
    var overlay = document.querySelector(".sidebar-overlay");
    var toggle = document.querySelector(".menu-toggle");
    if (toggle && sidebar && overlay) {
      toggle.addEventListener("click", function () {
        sidebar.classList.toggle("open");
        overlay.classList.toggle("visible");
      });
      overlay.addEventListener("click", function () {
        sidebar.classList.remove("open");
        overlay.classList.remove("visible");
      });
    }
    var path = window.location.pathname;
    document.querySelectorAll(".nav-item").forEach(function (item) {
      var href = item.getAttribute("href") || "";
      if (href !== "/" && path.indexOf(href) === 0) {
        item.classList.add("active");
      } else if (href === "/" && path === "/") {
        item.classList.add("active");
      }
    });
  }

  function initDropdown() {
    var toggle = document.querySelector("[data-dropdown-toggle]");
    var dropdown = toggle ? toggle.closest(".dropdown") : null;
    if (!toggle || !dropdown) return;
    toggle.addEventListener("click", function (event) {
      event.stopPropagation();
      dropdown.classList.toggle("open");
    });
    document.addEventListener("click", function () {
      dropdown.classList.remove("open");
    });
  }

  function initAlerts() {
    document.querySelectorAll("[data-dismiss-alert]").forEach(function (alert) {
      var button = alert.querySelector(".alert-action");
      if (button) {
        button.addEventListener("click", function () { alert.remove(); });
      }
    });
  }

  function initChart() {
    var canvas = document.getElementById("severityChart");
    if (!canvas || typeof Chart === "undefined") return;
    var labels = (canvas.dataset.labels || "").split(",").filter(Boolean);
    var values = (canvas.dataset.values || "").split(",").map(Number);
    var styles = getComputedStyle(document.documentElement);
    var colors = [
      styles.getPropertyValue("--red").trim(),
      "#fb923c",
      styles.getPropertyValue("--amber").trim(),
      styles.getPropertyValue("--blue").trim(),
      styles.getPropertyValue("--muted").trim()
    ];
    new Chart(canvas, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [{
          data: values,
          backgroundColor: colors,
          borderColor: colors,
          borderWidth: 1,
          borderRadius: 7,
          borderSkipped: false
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { backgroundColor: "#0c1728", borderColor: "#1c2f49", borderWidth: 1 } },
        scales: {
          x: { grid: { display: false }, ticks: { color: "#8ca3c0", font: { size: 10 } } },
          y: { beginAtZero: true, ticks: { precision: 0, color: "#647b99", font: { size: 10 } }, grid: { color: "rgba(28,47,73,0.7)" } }
        }
      }
    });
  }

  function initCopyButtons() {
    document.querySelectorAll(".copy-btn").forEach(function (button) {
      button.addEventListener("click", function () {
        var target = document.getElementById(button.dataset.copyTarget);
        if (!target) return;
        var text = target.textContent;
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(function () {
            var old = button.textContent;
            button.textContent = "Copied";
            window.setTimeout(function () { button.textContent = old; }, 1400);
          });
        }
      });
    });
  }

  function initFilters() {
    var scanSearch = document.getElementById("scanSearch");
    if (scanSearch) {
      scanSearch.addEventListener("input", function () {
        var term = scanSearch.value.toLowerCase();
        document.querySelectorAll("#scanTable tbody tr").forEach(function (row) {
          row.style.display = row.textContent.toLowerCase().indexOf(term) !== -1 ? "" : "none";
        });
      });
    }
    var findingSearch = document.getElementById("findingSearch");
    if (findingSearch) {
      findingSearch.addEventListener("input", function () {
        var term = findingSearch.value.toLowerCase();
        document.querySelectorAll("[data-finding-search]").forEach(function (card) {
          var haystack = (card.dataset.findingSearch || "").toLowerCase();
          card.style.display = haystack.indexOf(term) !== -1 ? "" : "none";
        });
      });
    }
  }

  function initDropzone() {
    var zone = document.getElementById("dropzone");
    var input = document.getElementById("sourceFile");
    var label = document.getElementById("dropzoneInner");
    if (!zone || !input || !label) return;
    var defaultHtml = label.innerHTML;
    function showFile(file) {
      if (!file) return;
      label.innerHTML = '<span class="dropzone-icon">✓</span><strong class="file-selected">' + file.name + '</strong><span>' + (file.size / 1024 / 1024).toFixed(2) + ' MB selected</span>';
      zone.classList.remove("dragging");
    }
    input.addEventListener("change", function () { showFile(input.files[0]); });
    ["dragenter", "dragover"].forEach(function (event) {
      zone.addEventListener(event, function (e) { e.preventDefault(); zone.classList.add("dragging"); });
    });
    ["dragleave", "drop"].forEach(function (event) {
      zone.addEventListener(event, function (e) { e.preventDefault(); zone.classList.remove("dragging"); });
    });
    zone.addEventListener("drop", function (e) {
      var file = e.dataTransfer && e.dataTransfer.files[0];
      if (!file) return;
      input.files = e.dataTransfer.files;
      showFile(file);
    });
    zone.addEventListener("click", function (e) {
      if (e.target === input) return;
      if (label.innerHTML !== defaultHtml && input.files.length === 0) label.innerHTML = defaultHtml;
    });
  }

  function initScanProgress() {
    var form = document.getElementById("scanForm");
    if (!form) return;
    form.addEventListener("submit", function () {
      var progress = document.getElementById("scanProgress");
      var bar = progress ? progress.querySelector(".scan-progress-bar") : null;
      var caption = document.getElementById("progressCaption");
      var button = document.getElementById("scanSubmit");
      if (progress) progress.classList.add("visible");
      if (caption) caption.textContent = "Uploading source and running static analysers…";
      if (button) { button.disabled = true; button.querySelector("span").textContent = "Analysing…"; }
      if (bar) window.setTimeout(function () { bar.style.width = "82%"; }, 120);
    });
  }

  function initSyntaxHighlighting() {
    if (window.Prism && document.querySelectorAll("pre code[class*=language-]").length) {
      window.Prism.highlightAll();
    }
  }

  ready(function () {
    initNavigation();
    initDropdown();
    initAlerts();
    initChart();
    initCopyButtons();
    initFilters();
    initDropzone();
    initScanProgress();
    initSyntaxHighlighting();
  });
})();
