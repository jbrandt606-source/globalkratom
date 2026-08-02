
document.addEventListener('DOMContentLoaded', () => {
  const menuButton = document.querySelector('.menu-button');
  const menu = document.querySelector('.site-menu');
  if (menuButton && menu) {
    menuButton.addEventListener('click', () => {
      const open = menu.classList.toggle('open');
      menuButton.setAttribute('aria-expanded', String(open));
    });
  }

  document.querySelectorAll('[data-filter-target]').forEach(input => {
    const tableId = input.getAttribute('data-filter-target');
    const table = document.getElementById(tableId);
    const counter = document.querySelector(`[data-count-for="${tableId}"]`);
    if (!table) return;
    const rows = Array.from(table.querySelectorAll('tbody tr'));
    const apply = () => {
      const q = input.value.trim().toLowerCase();
      let visible = 0;
      rows.forEach(row => {
        const match = !q || row.textContent.toLowerCase().includes(q);
        row.hidden = !match;
        if (match) visible++;
      });
      if (counter) counter.textContent = `${visible} matching entries`;
    };
    input.addEventListener('input', apply);
    apply();
  });

  const formatter = new Intl.NumberFormat('en-US');
  document.querySelectorAll('[data-animate-number]').forEach(el => {
    const target = Number(el.dataset.animateNumber);
    const decimals = Number(el.dataset.decimals || 0);
    const duration = 750;
    const start = performance.now();
    const tick = now => {
      const p = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      const value = target * eased;
      el.textContent = decimals ? value.toLocaleString('en-US', {minimumFractionDigits:decimals, maximumFractionDigits:decimals}) : formatter.format(Math.round(value));
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });
});
