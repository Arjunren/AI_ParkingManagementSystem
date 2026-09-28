document.addEventListener('DOMContentLoaded', () => {
  const panel = document.getElementById('ticket-price-panel'); if (!panel) return;
  const grid = document.getElementById('price-grid'); const canEdit = panel.dataset.canEdit === 'true';
  const load = async () => { const response = await csrfFetch('/api/ticket-prices'); const data = await response.json(); grid.replaceChildren(); for (const item of data.items) {
    const card = document.createElement('form'); card.className = 'flex items-center gap-3 rounded-xl border border-slate-200 p-3';
    const label = document.createElement('label'); label.className = 'min-w-0 flex-1 text-sm font-semibold'; label.textContent = item.category;
    const input = document.createElement('input'); input.type = 'number'; input.min = '0'; input.step = '.01'; input.value = item.amount; input.disabled = !canEdit; input.className = 'mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 font-normal'; label.appendChild(input); card.appendChild(label);
    if (canEdit) { const button = document.createElement('button'); button.className = 'rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white'; button.textContent = 'Save'; card.appendChild(button); card.addEventListener('submit', async event => { event.preventDefault(); const result = await csrfFetch('/api/ticket-prices', { method: 'POST', body: JSON.stringify({ category: item.category, amount: input.value }) }); const output = await result.json(); if (!result.ok) return showToast(output.error, 'error'); showToast(`${item.category} price updated.`); }); }
    grid.appendChild(card);
  }};
  load().catch(() => showToast('Ticket prices could not be loaded.', 'error'));
});

