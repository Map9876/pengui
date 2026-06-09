(function () {
  'use strict';

  let allData = {};

  async function loadData() {
    const resp = await fetch('data.json');
    allData = await resp.json();

    // Build date → isbns index
    const dateMap = {};
    for (const [isbn, entries] of Object.entries(allData)) {
      for (const entry of entries) {
        if (!dateMap[entry.date]) dateMap[entry.date] = [];
        dateMap[entry.date].push(isbn);
      }
    }

    // Sort dates descending (newest first)
    const dates = Object.keys(dateMap).sort().reverse();

    const gallery = document.getElementById('gallery');
    let html = '';

    for (const date of dates) {
      const isbns = [...new Set(dateMap[date])].sort();
      const dateObj = new Date(date + 'T00:00:00');
      const dateLabel = dateObj.toLocaleDateString('zh-CN', {
        year: 'numeric', month: 'long', day: 'numeric'
      });

      html += `<div class="date-group">`;
      html += `<div class="date-header">${dateLabel}<span class="date-count">${isbns.length}</span></div>`;
      html += `<div class="grid">`;

      for (const isbn of isbns) {
        const subdir = getSubdir(isbn);
        html += `<div class="item"><img src="img/${subdir}/${isbn}.avif" alt="${isbn}" loading="lazy" onerror="this.parentElement.style.display='none'"></div>`;
      }

      html += `</div></div>`;
    }

    gallery.innerHTML = html || '<div class="loading">No images available.</div>';
  }

  function getSubdir(isbn) {
    let h = 0;
    for (let i = 0; i < isbn.length; i++) {
      h = (h * 31 + isbn.charCodeAt(i)) & 0x7fffffff;
    }
    return String(h % 1000).padStart(3, '0');
  }

  loadData();
})();
