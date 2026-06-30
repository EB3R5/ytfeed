// Channel categories — master-detail CRUD over the channel_categories lookup.
// Left pane lists Groups; right pane is an editable AG Grid of that group's
// categories. Modelled on money-webapp's categories page, single context.
(function () {
  const COLUMNS = ["Category", "Group", "Type"];
  const ITEM_FIELD = "Category";
  const SECTION_FIELD = "Group";

  let section = null;     // current Group
  let options = {};       // {Group:[...], Type:[...]} for datalist editors
  let api = null;
  let searchQuery = "";   // current search text
  let searchExact = false; // exact (whole-cell) vs like (contains)
  let allGroups = false;  // search across every group, not just the selected one

  const $ = (sel) => document.querySelector(sel);
  const status = (txt) => { $("#categories-status").textContent = txt || ""; };

  const post = (url, body) =>
    fetch(url, { method: "POST", headers: { "Content-Type": "application/json" },
                 body: JSON.stringify(body) }).then((r) => r.json());
  const getJSON = (url) => fetch(url).then((r) => r.json());

  // --- datalist-backed cell editor: pick an existing value or type a new one ----
  function DatalistEditor() {}
  DatalistEditor.prototype.init = function (params) {
    this.field = params.colDef.field;
    this.input = document.createElement("input");
    this.input.className = "cat-editor";
    this.input.value = params.value == null ? "" : params.value;
    const listId = "dl-" + this.field.replace(/\W/g, "_");
    let dl = document.getElementById(listId);
    if (!dl) { dl = document.createElement("datalist"); dl.id = listId; document.body.appendChild(dl); }
    dl.innerHTML = "";
    (options[this.field] || []).forEach((v) => {
      const o = document.createElement("option"); o.value = v; dl.appendChild(o);
    });
    this.input.setAttribute("list", listId);
  };
  DatalistEditor.prototype.getGui = function () { return this.input; };
  DatalistEditor.prototype.afterGuiAttached = function () { this.input.focus(); this.input.select(); };
  DatalistEditor.prototype.getValue = function () { return this.input.value.trim(); };

  // --- grid ---------------------------------------------------------------------
  function columnDefs() {
    const defs = [{ headerName: "", checkboxSelection: true, headerCheckboxSelection: true,
                    width: 44, pinned: "left", sortable: false, resizable: false, editable: false }];
    COLUMNS.forEach((col) => {
      defs.push({
        field: col, editable: true, flex: 1, minWidth: 140, cellClass: "editable-cell",
        cellEditor: col === ITEM_FIELD ? "agTextCellEditor" : DatalistEditor,
      });
    });
    return defs;
  }

  function buildGrid() {
    api = agGrid.createGrid($("#grid"), {
      columnDefs: columnDefs(),
      rowData: [],
      defaultColDef: { sortable: true, resizable: true },
      rowSelection: "multiple",
      suppressRowClickSelection: true,
      getRowId: (p) => String(p.data._id),
      onCellValueChanged: onEdit,
      isExternalFilterPresent: () => searchQuery !== "",
      doesExternalFilterPass: (node) => {
        const q = searchQuery.toLowerCase();
        return COLUMNS.some((col) => {
          const v = (node.data[col] == null ? "" : String(node.data[col])).toLowerCase();
          return searchExact ? v === q : v.includes(q);
        });
      },
    });
  }

  function onEdit(e) {
    const field = e.colDef.field;
    status("Saving…");
    post("/api/channel-categories/update", { id: e.data._id, field, value: e.newValue })
      .then((d) => {
        if (!d.ok) { e.node.setDataValue(field, e.oldValue); status("⚠ " + (d.error || "failed")); return; }
        const n = d.updated || 0;
        status(`✓ saved · ${n} channel${n === 1 ? "" : "s"} use this`);
        // Moving a category to another Group changes the sidebar + this view.
        if (field === SECTION_FIELD) { loadSections(true).then(refreshGrid); }
      })
      .catch(() => { e.node.setDataValue(field, e.oldValue); status("⚠ network error"); });
  }

  // --- data loads ---------------------------------------------------------------
  function loadSections(keep) {
    return getJSON("/api/channel-categories/sections").then((d) => {
      options = d.options || {};
      const list = $("#section-list");
      list.innerHTML = "";
      (d.sections || []).forEach((s) => {
        const li = document.createElement("li");
        li.textContent = s;
        li.className = "section-item" + (s === section ? " active" : "");
        li.addEventListener("click", () => selectSection(s));
        list.appendChild(li);
      });
      if (!keep) {
        const next = (d.sections || []).includes(section) ? section : (d.sections || [])[0] || null;
        selectSection(next);
      }
    });
  }

  function selectSection(s) {
    // an explicit group pick drops out of all-groups mode
    allGroups = false;
    const box = $("#cat-allgroups");
    if (box) box.checked = false;
    section = s;
    document.querySelectorAll("#section-list .section-item").forEach((li) => {
      li.classList.toggle("active", li.textContent === s);
    });
    refreshGrid();
  }

  // load rows for the current view (one group, or every group when allGroups)
  function refreshGrid() {
    if (allGroups) {
      $("#detail-title").textContent = "All groups";
      return loadItems("*");
    }
    $("#detail-title").textContent = section ? `${SECTION_FIELD}: ${section}` : "—";
    if (section) return loadItems(section);
    if (api) api.setGridOption("rowData", []);
    return Promise.resolve();
  }

  function loadItems(s) {
    return getJSON(`/api/channel-categories?section=${encodeURIComponent(s)}`)
      .then((d) => { if (api) api.setGridOption("rowData", d.items || []); });
  }

  // --- add row ------------------------------------------------------------------
  const modal = $("#row-modal");
  const form = $("#row-form");

  function openAdd() {
    const wrap = $("#row-fields");
    wrap.innerHTML = "";
    COLUMNS.forEach((col) => {
      const label = document.createElement("label");
      label.className = "field";
      const span = document.createElement("span"); span.textContent = col;
      const input = document.createElement("input");
      input.type = "text"; input.name = col;
      if (col === SECTION_FIELD && section) input.value = section;
      if (col !== ITEM_FIELD && options[col]) {
        const listId = "addl-" + col.replace(/\W/g, "_");
        let dl = document.getElementById(listId);
        if (!dl) { dl = document.createElement("datalist"); dl.id = listId; document.body.appendChild(dl); }
        dl.innerHTML = "";
        options[col].forEach((v) => { const o = document.createElement("option"); o.value = v; dl.appendChild(o); });
        input.setAttribute("list", listId);
      }
      label.appendChild(span); label.appendChild(input);
      wrap.appendChild(label);
    });
    $("#row-status").textContent = "";
    modal.hidden = false;
    const first = form.elements[ITEM_FIELD];
    if (first) first.focus();
  }
  const closeAdd = () => { modal.hidden = true; };

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const payload = {};
    COLUMNS.forEach((col) => {
      const v = (form.elements[col].value || "").trim();
      if (v !== "") payload[col] = v;
    });
    $("#row-status").textContent = "Adding…";
    post("/api/channel-categories/row", payload).then((d) => {
      if (!d.ok) { $("#row-status").textContent = "Error: " + (d.error || "failed"); return; }
      closeAdd();
      const added = payload[SECTION_FIELD];
      loadSections(true).then(() => selectSection(added || section));
    }).catch(() => { $("#row-status").textContent = "Network error"; });
  });

  // --- delete -------------------------------------------------------------------
  function deleteRow(row, reassign) {
    const body = { id: row._id };
    if (reassign !== undefined) body.reassign_to = reassign;
    return post("/api/channel-categories/delete", body).then((d) => {
      if (d.ok) return true;
      if (d.in_use) {
        const dest = window.prompt(
          `"${row[ITEM_FIELD]}" is used by ${d.in_use} channel(s).\n` +
          `Type another category to reassign them to, leave blank + OK to unassign, or Cancel.`);
        if (dest === null) return false;       // cancelled
        return deleteRow(row, dest.trim() || "0");  // "0" = unassign
      }
      status("⚠ " + (d.error || "delete failed"));
      return false;
    });
  }

  function deleteSelected() {
    const rows = api.getSelectedRows();
    if (!rows.length) { alert("Select one or more rows first."); return; }
    if (!confirm(`Delete ${rows.length} categor${rows.length === 1 ? "y" : "ies"}?`)) return;
    (async () => {
      let n = 0;
      for (const r of rows) { if (await deleteRow(r)) n++; }
      status(`✓ deleted ${n}`);
      loadSections(true).then(refreshGrid);
    })();
  }

  // --- wiring -------------------------------------------------------------------
  $("#add-row").addEventListener("click", openAdd);
  $("#row-close").addEventListener("click", closeAdd);
  $("#row-cancel").addEventListener("click", closeAdd);
  modal.addEventListener("click", (e) => { if (e.target === modal) closeAdd(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !modal.hidden) closeAdd(); });
  $("#delete-rows").addEventListener("click", deleteSelected);
  $("#add-section").addEventListener("click", () => {
    const name = window.prompt("New Group? (becomes a section once you add a category)");
    if (name && name.trim()) { section = name.trim(); selectSection(section); openAdd(); }
  });

  // search: live like/exact filter over the loaded rows
  const applyFilter = () => { if (api) api.onFilterChanged(); };
  $("#cat-search").addEventListener("input", (e) => {
    searchQuery = e.target.value.trim();
    applyFilter();
  });
  $("#cat-exact").addEventListener("change", (e) => {
    searchExact = e.target.checked;
    applyFilter();
  });
  $("#cat-allgroups").addEventListener("change", (e) => {
    allGroups = e.target.checked;
    document.querySelectorAll("#section-list .section-item").forEach((li) =>
      li.classList.toggle("active", !allGroups && li.textContent === section));
    refreshGrid().then(applyFilter);
  });

  buildGrid();
  loadSections();
})();
