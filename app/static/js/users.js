document.addEventListener('DOMContentLoaded', () => {
  const panel = document.getElementById('user-panel'); if (!panel) return;
  const modal = document.getElementById('user-modal'); const form = document.getElementById('user-form'); const list = document.getElementById('user-list');
  const close = () => { modal.classList.add('hidden'); modal.classList.remove('flex'); };
  const load = async () => { const response = await csrfFetch('/api/users'); const data = await response.json(); list.replaceChildren(); for (const user of data.items) { const row = document.createElement('div'); row.className = 'flex items-center justify-between py-3'; const text = document.createElement('div'); const name = document.createElement('p'); name.className = 'font-semibold'; name.textContent = user.username; const detail = document.createElement('p'); detail.className = 'text-sm text-slate-500'; detail.textContent = user.role; text.append(name, detail); const badge = document.createElement('span'); badge.className = `rounded-full px-2.5 py-1 text-xs font-bold ${user.active ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'}`; badge.textContent = user.active ? 'Active' : 'Inactive'; row.append(text, badge); list.appendChild(row); } };
  document.getElementById('add-user').addEventListener('click', () => { form.reset(); modal.classList.remove('hidden'); modal.classList.add('flex'); });
  document.querySelectorAll('.user-modal-close').forEach(button => button.addEventListener('click', close));
  form.addEventListener('submit', async event => { event.preventDefault(); const payload = Object.fromEntries(new FormData(form)); payload.active = true; const response = await csrfFetch('/api/users', { method: 'POST', body: JSON.stringify(payload) }); const data = await response.json(); if (!response.ok) return showToast(data.error, 'error'); close(); showToast('Login account created.'); load(); });
  load();
});

