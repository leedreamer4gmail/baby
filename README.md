# 🍼 Baby Tracker

A lightweight, no-dependency web application for tracking your baby's daily activities — feedings, sleep, diaper changes, play sessions, baths, and medicine.

All data is saved in the browser's `localStorage` so entries survive page refreshes without needing a database.

## Features

- **Activity logging** – quickly log six activity types with an optional free-text note
- **Today's summary** – at-a-glance counts for each activity type
- **Chronological log** – newest entries shown first, each with a timestamp
- **Delete individual entries** or clear the entire log
- **Persistent storage** – data lives in `localStorage` (no sign-up required)
- **Responsive design** – works on mobile and desktop

## Getting Started

### Prerequisites

- [Node.js](https://nodejs.org/) 14 or later

### Run locally

```bash
# Install (no external dependencies needed)
npm install

# Start the server
npm start
```

Then open <http://localhost:3000> in your browser.

### Run tests

```bash
npm test
```

## Project Structure

```
baby/
├── public/
│   ├── index.html   # App shell
│   ├── style.css    # Styles
│   └── app.js       # Front-end logic (localStorage)
├── test/
│   └── app.test.js  # Node.js integration & unit tests
├── server.js        # Minimal static file server
└── package.json
```

## License

MIT
