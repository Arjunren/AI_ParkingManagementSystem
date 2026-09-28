(() => {
  const token = document.querySelector('meta[name="csrf-token"]')?.content || '';
  window.csrfFetch = (url, options = {}) => {
    const headers = new Headers(options.headers || {});
    if (!headers.has('Content-Type') && options.body) headers.set('Content-Type', 'application/json');
    if (!['GET', 'HEAD', 'OPTIONS'].includes((options.method || 'GET').toUpperCase())) headers.set('X-CSRFToken', token);
    return fetch(url, { ...options, headers, credentials: 'same-origin' });
  };
  window.showToast = (message, type = 'success') => {
    const host = document.getElementById('toast-container');
    if (!host) return;
    const item = document.createElement('div');
    item.className = `toast rounded-xl border px-4 py-3 text-sm font-semibold shadow-lg ${type === 'error' ? 'border-red-200 bg-red-50 text-red-800' : 'border-emerald-200 bg-white text-emerald-800'}`;
    item.textContent = message;
    host.appendChild(item);
    window.setTimeout(() => item.remove(), 4200);
  };
  const menu = document.getElementById('menu-button');
  const sidebar = document.getElementById('sidebar');
  const backdrop = document.getElementById('mobile-backdrop');
  const close = () => { sidebar?.classList.add('-translate-x-full'); backdrop?.classList.add('hidden'); };
  menu?.addEventListener('click', () => { sidebar?.classList.remove('-translate-x-full'); backdrop?.classList.remove('hidden'); });
  backdrop?.addEventListener('click', close);
})();

