const assert = require('node:assert/strict');
const test = require('node:test');
const {
  aiSummary, aiTags, changeMarks, changedFields, summarizeRepos, filterRepos, summaryText,
} = require('./repositories.js');

const scan = {
  repos: [
    { path: '~/Projects/app', origin: 'git.example.com/team/app', how: 'cloned', ai: { files: ['CLAUDE.md'] } },
    { path: '~/code/notes', origin: null, how: 'created here', ai: {} },
    { path: '~/src/web', origin: 'git.example.com/team/web', how: 'cloned',
      ai: { mcp_servers: [{ config: '.mcp.json', server: 'github' }] } },
  ],
  changes: { new: ['~/src/web'], not_found: ['~/old'], changed: [{ path: '~/Projects/app', fields: ['ai', 'last_active'] }] },
  previous_scan_at: '2026-11-09T10:00:00+00:00',
};

test('tags the AI configuration of a repository', () => {
  assert.deepEqual(aiTags({
    files: ['AGENTS.md'], folders: { '.cursor/rules': 2 },
    mcp_servers: [{ config: '.mcp.json', server: 'github' }],
    claude_rules: [{ config: '.claude/settings.json', mode: 'default', allow: 1, ask: 0, deny: 2 }],
  }).map(tag => tag.text), ['AGENTS.md', '.cursor/rules ×2', 'MCP: github', 'Rules: 1 allow · 0 ask · 2 deny']);
  assert.deepEqual(aiTags(undefined), []);
});

test('summarizes a repository scan for the tiles', () => {
  assert.deepEqual(summarizeRepos(scan),
    { total: 3, withAi: 2, cloned: 2, createdHere: 1, changed: 2, notFound: 1, firstScan: false });
  assert.equal(summarizeRepos({ repos: [], changes: null }).firstScan, true);
});

test('filters repositories and names what changed', () => {
  assert.deepEqual(filterRepos(scan, 'ai').map(repo => repo.path), ['~/Projects/app', '~/src/web']);
  assert.deepEqual(filterRepos(scan, 'changed').map(repo => repo.path), ['~/Projects/app', '~/src/web']);
  assert.deepEqual(filterRepos(scan, 'all', 'TEAM/WEB').map(repo => repo.path), ['~/src/web']);
  assert.deepEqual(changedFields(scan.changes, '~/Projects/app'), ['AI configuration', 'activity']);
  assert.deepEqual(changedFields(scan.changes, '~/code/notes'), []);
});

test('summarizes the AI configuration of a repository', () => {
  assert.deepEqual(aiSummary({
    files: ['AGENTS.md', 'CLAUDE.md'],
    folders: { '.cursor/rules': 2, '.claude/agents': 1 },
    mcp_servers: [{ config: '.mcp.json', server: 'github' }],
    claude_rules: [{ config: '.claude/settings.json', mode: 'default', allow: 1, ask: 0, deny: 2 }],
  }), [
    'Agent files: AGENTS.md, CLAUDE.md',
    '2 files in .cursor/rules',
    '1 file in .claude/agents',
    'MCP servers: github (.mcp.json)',
    'Claude Code rules (.claude/settings.json): mode default, 1 allow, 0 ask, 2 deny',
  ]);
  assert.deepEqual(aiSummary({}), []);
  assert.deepEqual(aiSummary(undefined), []);
});

test('marks new and changed repositories', () => {
  assert.deepEqual(changeMarks({ new: ['~/a'], not_found: ['~/b'], changed: [{ path: '~/c', fields: ['ai'] }] }),
    { '~/a': 'new', '~/c': 'changed' });
  assert.deepEqual(changeMarks(null), {});
});

test('describes the first scan as a baseline and later scans as changes', () => {
  assert.equal(summaryText({ repos: [{}], changes: null }), '1 repository. First scan: saved as the baseline for the next one.');
  const later = summaryText({
    repos: [{}, {}], previous_scan_at: '2026-11-10T12:00:00+00:00',
    changes: { new: ['~/a'], not_found: [], changed: [] },
  });
  assert.match(later, /^2 repositories\. Since the scan of .+: 1 new, 0 changed, 0 not found\.$/);
});
