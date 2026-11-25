import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const [original, output, branch = 'main'] = process.argv.slice(2);
if (!original || !output || resolve(original) === resolve(output) || !/^[\w.-]+$/.test(branch)) {
  throw new Error('Usage: node apply.mjs PRIVATE-ORIGINAL.yaml NEW-OUTPUT.yaml [branch]');
}

const manifest = JSON.parse(await readFile(new URL('sources.json', import.meta.url), 'utf8'));
const settings = manifest.consumer;
const source = await readFile(original, 'utf8');
const clean = source.replace(/^\uFEFF/, '');
const endline = clean.includes('\r\n') ? '\r\n' : '\n';
const base = 'https://raw.githubusercontent.com/DanknesSIK/shadowrocket-adblock-auto/' +
  branch + '/clash-meta/find-n2/mirror/';
if (clean.includes(settings.adRule) || clean.includes(settings.pikpakGroup)) {
  throw new Error('Use the original unmodified profile to avoid duplicate rules');
}

function prependSequence(input, name, lines) {
  const expression = new RegExp('(^' + name + ':[ \\t]*(?:#.*)?\\r?\\n)([ \\t]*)-(?=\\s)', 'm');
  if (!expression.test(input)) throw new Error('Missing block sequence: ' + name);
  return input.replace(expression, (_, start, indent) =>
    start + lines.map(line => indent + line + endline).join('') + indent + '-');
}

const group = settings.pikpakGroup;
let result = prependSequence(clean, 'proxy-groups', [
  '- name: ' + group,
  '  type: url-test',
  '  include-all: true',
  "  exclude-filter: '" + settings.excludeFilter + "'",
  '  url: ' + settings.healthUrl,
  '  expected-status: 204',
  '  interval: ' + settings.testIntervalSeconds,
  '  tolerance: ' + settings.toleranceMs,
  '  lazy: true',
  '  empty-fallback: REJECT'
]);
result = prependSequence(result, 'rules', [
  '- ' + settings.adRule,
  '- RULE-SET,noir-pikpak,' + group
]);

const ruleBlock = /^rule-providers:[ \t]*\r?\n[\s\S]*?(?=^[A-Za-z][A-Za-z0-9_-]*:|(?![\s\S]))/m;
const match = ruleBlock.exec(result);
if (!match) throw new Error('Missing rule-providers mapping');
let providers = match[0];
for (const path of manifest.acl.paths) {
  const old = 'https://cdn.jsdelivr.net/gh/' + manifest.acl.repo + '@' + manifest.acl.ref + '/' + path;
  if (providers.split(old).length !== 2) throw new Error('Expected exactly one provider source: ' + path);
  providers = providers.replace(old, base + 'acl4ssr/' + path);
}
providers += [
  '  noir-pikpak:',
  '    type: http',
  '    behavior: classical',
  '    format: text',
  '    path: ./ruleset/noir-pikpak.list',
  '    url: ' + base + 'pikpak.list',
  '    interval: ' + settings.refreshSeconds,
  ''
].join(endline);
result = result.slice(0, match.index) + providers + result.slice(match.index + match[0].length);
await writeFile(output, result, { flag: 'wx' });
console.log('Prepared a private local profile with ' + manifest.acl.paths.length + ' ACL4SSR mirrors and PikPak-Auto.');
