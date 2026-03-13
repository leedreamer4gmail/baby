/* Baby Tracker – front-end logic
   All data is persisted in localStorage so entries survive page refreshes. */

(function () {
  'use strict';

  const STORAGE_KEY = 'baby_tracker_entries';

  const ICONS = {
    feeding:  '🍼',
    sleep:    '😴',
    diaper:   '🚼',
    play:     '🧸',
    bath:     '🛁',
    medicine: '💊',
  };

  // ── State ────────────────────────────────────────────────────

  function loadEntries() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    } catch (_) {
      return [];
    }
  }

  function saveEntries(entries) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
  }

  // ── Helpers ──────────────────────────────────────────────────

  function formatTime(isoString) {
    const d = new Date(isoString);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function todayEntries(entries) {
    const today = new Date().toDateString();
    return entries.filter(e => new Date(e.timestamp).toDateString() === today);
  }

  // ── Render ───────────────────────────────────────────────────

  function renderList(entries) {
    const list = document.getElementById('activity-list');
    list.innerHTML = '';

    if (entries.length === 0) {
      const li = document.createElement('li');
      li.className = 'empty-state';
      li.textContent = 'No activities logged yet. Add your first entry above!';
      list.appendChild(li);
      return;
    }

    // Newest first
    [...entries].reverse().forEach(entry => {
      const li = document.createElement('li');
      li.dataset.id = entry.id;

      const icon = document.createElement('span');
      icon.className = 'item-icon';
      icon.textContent = ICONS[entry.type] || '📝';

      const type = document.createElement('span');
      type.className = 'item-type';
      type.textContent = entry.type;

      const note = document.createElement('span');
      note.className = 'item-note';
      note.textContent = entry.note || '';

      const time = document.createElement('span');
      time.className = 'item-time';
      time.textContent = formatTime(entry.timestamp);

      const del = document.createElement('button');
      del.className = 'item-del';
      del.textContent = '✕';
      del.setAttribute('aria-label', 'Delete entry');
      del.addEventListener('click', () => deleteEntry(entry.id));

      li.appendChild(icon);
      li.appendChild(type);
      li.appendChild(note);
      li.appendChild(time);
      li.appendChild(del);
      list.appendChild(li);
    });
  }

  function renderSummary(entries) {
    const counts = { feeding: 0, sleep: 0, diaper: 0, play: 0, bath: 0, medicine: 0 };
    todayEntries(entries).forEach(e => {
      if (counts[e.type] !== undefined) counts[e.type]++;
    });
    Object.keys(counts).forEach(type => {
      const el = document.getElementById('count-' + type);
      if (el) el.textContent = counts[type];
    });
  }

  function render() {
    const entries = loadEntries();
    renderList(entries);
    renderSummary(entries);
  }

  // ── Actions ──────────────────────────────────────────────────

  function addEntry(type, note) {
    const entries = loadEntries();
    const entry = {
      id: Date.now().toString(36) + Math.random().toString(36).slice(2),
      type,
      note: note.trim(),
      timestamp: new Date().toISOString(),
    };
    entries.push(entry);
    saveEntries(entries);
    render();
  }

  function deleteEntry(id) {
    const entries = loadEntries().filter(e => e.id !== id);
    saveEntries(entries);
    render();
  }

  function clearAll() {
    if (confirm('Clear all logged activities?')) {
      saveEntries([]);
      render();
    }
  }

  // ── Event listeners ──────────────────────────────────────────

  document.getElementById('activity-form').addEventListener('submit', function (e) {
    e.preventDefault();
    const type = document.getElementById('activity-type').value;
    const note = document.getElementById('activity-note').value;
    if (!type) return;
    addEntry(type, note);
    this.reset();
  });

  document.getElementById('clear-btn').addEventListener('click', clearAll);

  // ── Init ─────────────────────────────────────────────────────
  render();
})();
