const assert = require('node:assert/strict');
const test = require('node:test');
const { relativeTime } = require('./ui.js');

test('describes how long ago something happened', () => {
  const now = Date.parse('2026-11-10T12:00:00Z');
  const ago = seconds => new Date(now - seconds * 1000).toISOString();
  assert.equal(relativeTime(ago(20), now), 'just now');
  assert.equal(relativeTime(ago(60), now), '1 minute ago');
  assert.equal(relativeTime(ago(5 * 3600), now), '5 hours ago');
  assert.equal(relativeTime(ago(3 * 86400), now), '3 days ago');
  assert.equal(relativeTime(ago(15 * 86400), now), '2 weeks ago');
  assert.equal(relativeTime(ago(400 * 86400), now), '1 year ago');
  assert.equal(relativeTime('not a date', now), 'unknown');
});
