// shift-click range selection + select-all for video checkboxes
(function () {
  let lastChecked = null;

  document.addEventListener("click", function (e) {
    const cb = e.target;
    if (!(cb instanceof HTMLInputElement) || cb.type !== "checkbox") return;

    if (cb.name === "video_ids") {
      const boxes = Array.from(
        document.querySelectorAll('input[type="checkbox"][name="video_ids"]')
      );
      if (e.shiftKey && lastChecked && lastChecked !== cb && boxes.includes(lastChecked)) {
        const i = boxes.indexOf(lastChecked);
        const j = boxes.indexOf(cb);
        boxes
          .slice(Math.min(i, j), Math.max(i, j) + 1)
          .forEach(function (b) { b.checked = cb.checked; });
      }
      lastChecked = cb;
    } else if (cb.classList.contains("select-all")) {
      document
        .querySelectorAll('input[type="checkbox"][name="video_ids"]')
        .forEach(function (b) { b.checked = cb.checked; });
      lastChecked = null;
    }
  });

  // the anchor checkbox is gone after htmx swaps in a fresh list
  document.addEventListener("htmx:afterSwap", function () { lastChecked = null; });

  // keep sync log views pinned to the newest line (initial load + every poll swap)
  function pinSyncLogs() {
    document.querySelectorAll(".sync-log").forEach(function (el) {
      el.scrollTop = el.scrollHeight;
    });
  }
  document.addEventListener("htmx:afterSettle", pinSyncLogs);
  document.addEventListener("DOMContentLoaded", pinSyncLogs);
  document.addEventListener("toggle", function (e) {
    if (e.target instanceof HTMLElement && e.target.classList.contains("sync-log-details")) pinSyncLogs();
  }, true);

  // live row filter: <input data-filter-rows="#table-selector"> hides
  // non-matching tbody rows as you type
  document.addEventListener("input", function (e) {
    const el = e.target;
    if (!(el instanceof HTMLInputElement) || !el.hasAttribute("data-filter-rows")) return;
    const table = document.querySelector(el.getAttribute("data-filter-rows"));
    if (!table) return;
    const q = el.value.trim().toLowerCase();
    // optional exact mode: <input data-filter-rows> + a checkbox referenced by
    // data-filter-exact. Like = whole-row contains; exact = a cell equals q.
    const exactSel = el.getAttribute("data-filter-exact");
    const exact = exactSel ? !!document.querySelector(exactSel)?.checked : false;
    let visible = 0;
    table.querySelectorAll("tbody tr").forEach(function (tr) {
      let match = !q;
      if (q) {
        match = exact
          ? Array.from(tr.querySelectorAll("td")).some(function (td) {
              return td.textContent.trim().toLowerCase() === q;
            })
          : tr.textContent.toLowerCase().includes(q);
      }
      tr.style.display = match ? "" : "none";
      if (match) visible++;
    });
    const counterId = el.getAttribute("data-filter-count");
    const counter = counterId ? document.getElementById(counterId) : null;
    if (counter) counter.textContent = q ? visible + " matching" : "";
  });

  // toggling an exact-mode checkbox re-runs the filter it belongs to
  document.addEventListener("change", function (e) {
    const cb = e.target;
    if (!(cb instanceof HTMLInputElement) || !cb.hasAttribute("data-filter-trigger")) return;
    const input = document.querySelector(cb.getAttribute("data-filter-trigger"));
    if (input) input.dispatchEvent(new Event("input", { bubbles: true }));
  });
})();
