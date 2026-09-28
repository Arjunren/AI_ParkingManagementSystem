document.addEventListener('DOMContentLoaded', () => {
  const app = document.getElementById('resource-app');
  if (!app) return;
  const config = JSON.parse(app.dataset.pageConfig);
  const isAdmin = app.dataset.isAdmin === 'true';
  const modal = document.getElementById('record-modal');
  const form = document.getElementById('record-form');
  const body = document.getElementById('resource-body');
  const head = document.getElementById('resource-head');
  const count = document.getElementById('record-count');
  const empty = document.getElementById('empty-state');
  const search = document.getElementById('table-search');
  const deletable = ['/api/visitors', '/api/facilities', '/api/reservations'].includes(config.endpoint);
  let items = [];

  const escapeDate = value => {
    if (!value) return '—';
    if (/^\d{4}-\d{2}-\d{2}T/.test(String(value))) return new Date(value).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
    return String(value);
  };
  const badgeClass = value => {
    const v = String(value).toLowerCase();
    if (/critical|cancelled|closed|failed|rejected/.test(v)) return 'bg-red-50 text-red-700 ring-red-200';
    if (/high|pending|open|assigned|under maintenance/.test(v)) return 'bg-amber-50 text-amber-800 ring-amber-200';
    if (/approved|available|active|completed|resolved|paid|inside/.test(v)) return 'bg-emerald-50 text-emerald-700 ring-emerald-200';
    return 'bg-slate-100 text-slate-700 ring-slate-200';
  };
  const cell = (value, column) => {
    const td = document.createElement('td'); td.className = 'px-5 py-4 align-top text-slate-700';
    if (column.badge) {
      const span = document.createElement('span'); span.className = `inline-flex rounded-full px-2.5 py-1 text-xs font-bold ring-1 ring-inset ${badgeClass(value)}`; span.textContent = escapeDate(value); td.appendChild(span);
    } else { td.textContent = escapeDate(value); }
    return td;
  };
  const render = () => {
    const term = search.value.trim().toLowerCase();
    const visible = items.filter(item => JSON.stringify(item).toLowerCase().includes(term));
    body.replaceChildren();
    count.textContent = `${visible.length} record${visible.length === 1 ? '' : 's'}`;
    empty.classList.toggle('hidden', visible.length !== 0);
    for (const item of visible) {
      const tr = document.createElement('tr'); tr.className = 'hover:bg-slate-50/70';
      config.columns.forEach(column => tr.appendChild(cell(item[column.key], column)));
      const actions = document.createElement('td'); actions.className = 'whitespace-nowrap px-5 py-4 text-right';
      const edit = document.createElement('button'); edit.className = 'rounded-lg px-3 py-1.5 text-sm font-semibold text-emerald-700 hover:bg-emerald-50'; edit.textContent = 'Edit'; edit.addEventListener('click', () => openModal(item)); actions.appendChild(edit);
      if (config.endpoint === '/api/visitors' && item.status === 'Inside') {
        const exit = document.createElement('button'); exit.className = 'rounded-lg px-3 py-1.5 text-sm font-semibold text-sky-700 hover:bg-sky-50'; exit.textContent = 'Exit'; exit.addEventListener('click', () => markExit(item.id)); actions.appendChild(exit);
      }
      if (deletable && (isAdmin || config.endpoint !== '/api/facilities')) {
        const del = document.createElement('button'); del.className = 'rounded-lg px-3 py-1.5 text-sm font-semibold text-red-700 hover:bg-red-50'; del.textContent = 'Delete'; del.addEventListener('click', () => remove(item)); actions.appendChild(del);
      }
      tr.appendChild(actions); body.appendChild(tr);
    }
  };
  const load = async () => {
    try { const response = await csrfFetch(config.endpoint); const data = await response.json(); if (!response.ok) throw new Error(data.error); items = data.items; render(); }
    catch (error) { showToast(error.message || 'Records could not be loaded.', 'error'); }
  };
  const openModal = (item = null) => {
    form.reset(); form.elements.id.value = item?.id || '';
    document.getElementById('record-modal-title').textContent = item ? 'Edit record' : 'Add record';
    if (item) for (const field of config.fields) {
      const input = form.elements[field.name]; if (!input) continue;
      if (input.type === 'checkbox') input.checked = Boolean(item[field.name]);
      else { let value = item[field.name] ?? ''; if (input.type === 'datetime-local' && value) value = value.slice(0, 16); input.value = value; }
    }
    modal.classList.remove('hidden'); modal.classList.add('flex');
  };
  const closeModal = () => { modal.classList.add('hidden'); modal.classList.remove('flex'); };
  const markExit = async id => { const response = await csrfFetch(`${config.endpoint}/${id}/exit`, { method: 'POST', body: '{}' }); const data = response.status === 204 ? {} : await response.json(); if (!response.ok) return showToast(data.error || 'Exit could not be recorded.', 'error'); showToast('Visitor exit recorded.'); load(); };
  const remove = async item => {
    if (!window.confirm(`Delete this ${config.title.toLowerCase()} record? This cannot be undone.`)) return;
    const response = await csrfFetch(`${config.endpoint}/${item.id}`, { method: 'DELETE' });
    if (!response.ok) { const data = await response.json(); return showToast(data.error || 'Record could not be deleted.', 'error'); }
    showToast('Record deleted.'); load();
  };
  const row = document.createElement('tr');
  config.columns.forEach(column => { const th = document.createElement('th'); th.className = 'px-5 py-3 font-bold'; th.textContent = column.label; row.appendChild(th); });
  const actionHead = document.createElement('th'); actionHead.className = 'px-5 py-3 text-right font-bold'; actionHead.textContent = 'Actions'; row.appendChild(actionHead); head.appendChild(row);
  document.getElementById('add-record')?.addEventListener('click', () => openModal());
  document.querySelectorAll('.modal-close').forEach(button => button.addEventListener('click', closeModal));
  modal.addEventListener('click', event => { if (event.target === modal) closeModal(); });
  search.addEventListener('input', render);
  form.addEventListener('submit', async event => {
    event.preventDefault(); const payload = {};
    for (const field of config.fields) { const input = form.elements[field.name]; payload[field.name] = input.type === 'checkbox' ? input.checked : input.value; }
    const id = form.elements.id.value; const response = await csrfFetch(id ? `${config.endpoint}/${id}` : config.endpoint, { method: id ? 'PUT' : 'POST', body: JSON.stringify(payload) }); const data = await response.json();
    if (!response.ok) return showToast(data.error || 'Record could not be saved.', 'error'); closeModal(); showToast(id ? 'Record updated.' : 'Record added.'); load();
  });
  load();
});

