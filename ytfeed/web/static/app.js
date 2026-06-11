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

  // live row filter: <input data-filter-rows="#table-selector"> hides
  // non-matching tbody rows as you type
  document.addEventListener("input", function (e) {
    const el = e.target;
    if (!(el instanceof HTMLInputElement) || !el.hasAttribute("data-filter-rows")) return;
    const table = document.querySelector(el.getAttribute("data-filter-rows"));
    if (!table) return;
    const q = el.value.trim().toLowerCase();
    let visible = 0;
    table.querySelectorAll("tbody tr").forEach(function (tr) {
      const match = !q || tr.textContent.toLowerCase().includes(q);
      tr.style.display = match ? "" : "none";
      if (match) visible++;
    });
    const counterId = el.getAttribute("data-filter-count");
    const counter = counterId ? document.getElementById(counterId) : null;
    if (counter) counter.textContent = q ? visible + " matching" : "";
  });
})();
