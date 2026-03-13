/**
 * Basic tests for the Baby Tracker server.
 * Run with: node test/app.test.js
 */

'use strict';

const http = require('http');
const path = require('path');
const fs = require('fs');

let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (condition) {
    console.log('  ✓', message);
    passed++;
  } else {
    console.error('  ✗', message);
    failed++;
  }
}

// ── File existence tests ─────────────────────────────────────
console.log('\nFile structure tests');
const requiredFiles = [
  'package.json',
  'server.js',
  'public/index.html',
  'public/style.css',
  'public/app.js',
];
requiredFiles.forEach(file => {
  const fullPath = path.join(__dirname, '..', file);
  assert(fs.existsSync(fullPath), `${file} exists`);
});

// ── package.json tests ───────────────────────────────────────
console.log('\npackage.json tests');
const pkg = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'package.json'), 'utf8'));
assert(pkg.name === 'baby-tracker', 'package name is baby-tracker');
assert(pkg.scripts && pkg.scripts.start, 'start script is defined');
assert(pkg.scripts && pkg.scripts.test, 'test script is defined');

// ── HTML content tests ───────────────────────────────────────
console.log('\nHTML content tests');
const html = fs.readFileSync(path.join(__dirname, '..', 'public/index.html'), 'utf8');
assert(html.includes('Baby Tracker'), 'HTML contains app title');
assert(html.includes('activity-form'), 'HTML contains activity form');
assert(html.includes('activity-list'), 'HTML contains activity list');
assert(html.includes('app.js'), 'HTML references app.js');
assert(html.includes('style.css'), 'HTML references style.css');

// ── app.js content tests ─────────────────────────────────────
console.log('\napp.js content tests');
const appJs = fs.readFileSync(path.join(__dirname, '..', 'public/app.js'), 'utf8');
assert(appJs.includes('baby_tracker_entries'), 'app.js uses localStorage key');
assert(appJs.includes('addEntry'), 'app.js defines addEntry');
assert(appJs.includes('deleteEntry'), 'app.js defines deleteEntry');
assert(appJs.includes('render'), 'app.js defines render function');

// ── HTTP server integration test ─────────────────────────────
console.log('\nHTTP server tests');
const server = require('../server');

server.listen(0, () => {
  const port = server.address().port;

  const req = http.get(`http://localhost:${port}/`, res => {
    assert(res.statusCode === 200, 'GET / returns 200');
    let body = '';
    res.on('data', chunk => { body += chunk; });
    res.on('end', () => {
      assert(body.includes('Baby Tracker'), 'index.html is served');

      // Path traversal should be rejected
      const traversalReq = http.get(`http://localhost:${port}/../package.json`, res2 => {
        assert(res2.statusCode === 403 || res2.statusCode === 404, 'path traversal is blocked');
        server.close(() => {
          console.log(`\nResults: ${passed} passed, ${failed} failed`);
          process.exit(failed > 0 ? 1 : 0);
        });
      });
      traversalReq.on('error', err => {
        console.error('Traversal request error:', err.message);
        failed++;
        server.close(() => { process.exit(1); });
      });
    });
  });

  req.on('error', err => {
    console.error('HTTP request error:', err.message);
    failed++;
    server.close(() => { process.exit(1); });
  });
});
