// The page loads these scripts as classic scripts that share one global scope.
// A top-level function declared in two of them silently replaces the earlier
// one (this once broke publisher verification), and a duplicate const/let/class
// stops a script from loading at all. Node tests load each file separately and
// cannot see that, so check the names directly.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const html = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');
const scripts = [...html.matchAll(/<script src="([^"]+)"/g)].map(match => match[1]);

function topLevelNames(source) {
  const names = [];
  for (const line of source.split('\n')) {
    const match = line.match(/^(?:async\s+)?function\s+([A-Za-z_$][\w$]*)|^(?:const|let|var|class)\s+([A-Za-z_$][\w$]*)/);
    if (match) names.push(match[1] ?? match[2]);
  }
  return names;
}

test('the page loads every view script', () => {
  assert.deepEqual(scripts, ['ui.js', 'discovery.js', 'repositories.js', 'passports.js', 'passport.js']);
});

test('page scripts do not declare the same top-level name twice', () => {
  const owners = new Map();
  for (const script of scripts) {
    for (const name of topLevelNames(fs.readFileSync(path.join(__dirname, script), 'utf8'))) {
      assert.ok(!owners.has(name), `"${name}" is declared in both ${owners.get(name)} and ${script}`);
      owners.set(name, script);
    }
  }
});
