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
})();
