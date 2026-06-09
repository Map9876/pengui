(function () {
  'use strict';

  let allData = {};       // {isbn: [{date, md5}, ...]}
  let datesWithChanges = new Set();  // dates that have changes
  let currentMonth;       // Date object for current calendar month
  let selectedDate = null;

  // Build reverse index: date → [{isbn, md5}]
  let dateIndex = {};

  async function loadData() {
    const resp = await fetch('data.json');
    allData = await resp.json();

    // Build date index
    for (const [isbn, entries] of Object.entries(allData)) {
      for (const entry of entries) {
        const d = entry.date;
        if (!dateIndex[d]) dateIndex[d] = [];
        dateIndex[d].push({ isbn, md5: entry.md5 });
        datesWithChanges.add(d);
      }
    }

    // Set calendar to most recent month with data
    const allDates = Array.from(datesWithChanges).sort();
    if (allDates.length > 0) {
      const latest = allDates[allDates.length - 1];
      const [y, m] = latest.split('-').map(Number);
      currentMonth = new Date(y, m - 1, 1);
      selectedDate = latest;
      renderGallery(latest);
    } else {
      currentMonth = new Date();
      currentMonth.setDate(1);
    }
    renderCalendar();
  }

  function renderCalendar() {
    const year = currentMonth.getFullYear();
    const month = currentMonth.getMonth();
    const today = new Date();
    const todayStr = formatDate(today);

    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const startWeekday = firstDay.getDay(); // 0=Sun
    const daysInMonth = lastDay.getDate();

    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December'];

    let html = '<div class="cal-header">';
    html += `<button id="cal-prev">&lt;</button>`;
    html += `<span class="cal-title">${monthNames[month]} ${year}</span>`;
    html += `<button id="cal-next">&gt;</button>`;
    html += '</div>';

    // Weekday headers
    html += '<div class="cal-weekdays">';
    for (const wd of ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa']) {
      html += `<span>${wd}</span>`;
    }
    html += '</div>';

    // Days grid
    html += '<div class="cal-days">';

    // Previous month padding
    const prevMonth = new Date(year, month, 0);
    for (let i = startWeekday - 1; i >= 0; i--) {
      const day = prevMonth.getDate() - i;
      html += `<div class="cal-day other-month">${day}</div>`;
    }

    // Current month days
    for (let day = 1; day <= daysInMonth; day++) {
      const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
      let cls = 'cal-day';
      if (dateStr === todayStr) cls += ' today';
      if (dateStr === selectedDate) cls += ' selected';
      if (datesWithChanges.has(dateStr)) cls += ' has-data';
      html += `<div class="${cls}" data-date="${dateStr}">${day}</div>`;
    }

    // Next month padding
    const totalCells = startWeekday + daysInMonth;
    const remaining = (7 - (totalCells % 7)) % 7;
    for (let i = 1; i <= remaining; i++) {
      html += `<div class="cal-day other-month">${i}</div>`;
    }

    html += '</div>';

    document.getElementById('calendar').innerHTML = html;

    // Event listeners
    document.getElementById('cal-prev').addEventListener('click', () => {
      currentMonth.setMonth(currentMonth.getMonth() - 1);
      renderCalendar();
    });
    document.getElementById('cal-next').addEventListener('click', () => {
      currentMonth.setMonth(currentMonth.getMonth() + 1);
      renderCalendar();
    });
    document.querySelectorAll('.cal-day:not(.other-month)').forEach(el => {
      el.addEventListener('click', () => {
        const date = el.dataset.date;
        if (date) {
          selectedDate = date;
          renderCalendar();
          renderGallery(date);
        }
      });
    });
  }

  function renderGallery(dateStr) {
    const gallery = document.getElementById('gallery');
    const title = document.getElementById('gallery-title');

    const items = dateIndex[dateStr] || [];
    title.textContent = `${dateStr} — ${items.length} cover${items.length !== 1 ? 's' : ''} changed`;

    if (items.length === 0) {
      gallery.innerHTML = '<p style="color:#8b949e">No cover changes on this date.</p>';
      return;
    }

    // Sort by ISBN
    items.sort((a, b) => a.isbn.localeCompare(b.isbn));

    let html = '';
    for (const item of items) {
      const subdir = getSubdir(item.isbn);
      html += `<div class="card">`;
      html += `<img src="img/${subdir}/${item.isbn}.avif" alt="${item.isbn}" loading="lazy" onerror="this.src='img/${item.isbn}.avif'">`;
      html += `<div class="info">`;
      html += `<div class="isbn">${item.isbn}</div>`;
      html += `<div class="date">${dateStr}</div>`;
      html += `</div></div>`;
    }
    gallery.innerHTML = html;
  }

  function getSubdir(isbn) {
    // Distribute files into subdirs: img/000/, img/001/, ... img/999/
    let hash = 0;
    for (let i = 0; i < isbn.length; i++) {
      hash = (hash * 31 + isbn.charCodeAt(i)) & 0x7fffffff;
    }
    return String(hash % 1000).padStart(3, '0');
  }

  function formatDate(d) {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  }

  loadData();
})();
