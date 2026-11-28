import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const [original, output, branch = 'main'] = process.argv.slice(2);
if (!original || !output || resolve(original) === resolve(output) || !/^[\w.-]+$/.test(branch)) {
  throw new Error('Usage: node apply.mjs PRIVATE-PROFILE.yaml NEW-OUTPUT.yaml [branch]');
}

const manifest = JSON.parse(await readFile(new URL('sources.json', import.meta.url), 'utf8'));
const settings = manifest.consumer;
const source = await readFile(original, 'utf8');
const clean = source.replace(/^\uFEFF/, '');
const endline = clean.includes('\r\n') ? '\r\n' : '\n';
const base = 'https://raw.githubusercontent.com/DanknesSIK/shadowrocket-adblock-auto/' + branch + '/clash-meta/';

function topLevelBlock(input, name) {
  const expression = new RegExp('^' + name + ':[ \\t]*(?:#.*)?\\r?\\n[\\s\\S]*?(?=^[A-Za-z][A-Za-z0-9_-]*[ \\t]*:|^\\.\\.\\.|(?![\\s\\S]))', 'm');
  const block = expression.exec(input);
  if (!block) throw new Error('Missing block: ' + name);
  return block;
}

function sequenceValues(block) {
  const first = /^([ \t]*)-[ \t]+/m.exec(block);
  if (!first) throw new Error('Missing block sequence');
  return [...block.matchAll(new RegExp('^' + first[1] + '-[ \\t]+([^\\r\\n]+)', 'gm'))]
    .map(match => match[1].replace(/[ \t]+#.*$/, '').trim().replace(/^(['"])(.*)\1$/, '$2'));
}

function prependSequence(input, name, lines) {
  if (lines.length === 0) return input;
  const expression = new RegExp('(^' + name + ':[ \\t]*(?:#.*)?\\r?\\n)((?:[ \\t]*(?:#.*)?\\r?\\n)*)([ \\t]*)-(?=\\s)', 'm');
  if (!expression.test(input)) throw new Error('Missing block sequence: ' + name);
  return input.replace(expression, (_, header, comments, indent) =>
    header + comments + lines.map(line => indent + line + endline).join('') + indent + '-');
}

function autoGroup(name, policy, lazy) {
  return [
    '- name: ' + name,
    '  type: url-test',
    '  include-all: true',
    "  exclude-filter: '" + policy.excludeFilter + "'",
    '  url: ' + policy.healthUrl,
    '  expected-status: ' + policy.healthStatus,
    '  interval: ' + policy.testIntervalSeconds,
    '  tolerance: ' + policy.toleranceMs,
    '  lazy: ' + lazy,
    '  empty-fallback: REJECT'
  ];
}

const pikpak = settings.pikpakGroup;
const { chatgpt } = settings;
const existingGroups = sequenceValues(topLevelBlock(clean, 'proxy-groups')[0])
  .map(value => {
    const name = /^\{\s*name:\s*([^,}]+)/.exec(value)?.[1] ?? value.replace(/^name:\s*/, '');
    return name.trim().replace(/^(['"])(.*)\1$/, '$2');
  });
const newGroups = [];
if (!existingGroups.includes(pikpak)) newGroups.push(...autoGroup(pikpak, settings, false));
if (!existingGroups.includes(chatgpt.group)) newGroups.push(...autoGroup(chatgpt.group, chatgpt, true));
let result = prependSequence(clean, 'proxy-groups', newGroups);

const existingRules = sequenceValues(topLevelBlock(result, 'rules')[0]);
const managedRules = [settings.adRule, 'RULE-SET,noir-pikpak,' + pikpak, 'RULE-SET,shared-chatgpt,' + chatgpt.group];
const newRules = managedRules.filter(rule => !existingRules.includes(rule));
result = prependSequence(result, 'rules', newRules.map(rule => '- ' + rule));

const match = topLevelBlock(result, 'rule-providers');
let providers = match[0];
for (const path of manifest.acl.paths) {
  const old = 'https://cdn.jsdelivr.net/gh/' + manifest.acl.repo + '@' + manifest.acl.ref + '/' + path;
  providers = providers.replaceAll(old, base + 'find-n2/mirror/acl4ssr/' + path);
}

const providerEntry = /^([ \t]+)[^\s#][^\r\n]*:/m.exec(providers);
if (!providerEntry) throw new Error('Missing rule-providers entries');
const indent = providerEntry[1];
for (const [name, filename, location] of [
  ['noir-pikpak', 'noir-pikpak.list', 'find-n2/mirror/pikpak.list'],
  ['shared-chatgpt', 'shared-chatgpt.list', 'shared/chatgpt.list']
]) {
  const declaration = new RegExp('^' + indent + '["\\\']?' + name + '["\\\']?[ \\t]*:', 'm');
  if (declaration.test(providers)) continue;
  if (!providers.endsWith('\n')) providers += endline;
  providers += [
    name + ':',
    '  type: http',
    '  behavior: classical',
    '  format: text',
    '  path: ./ruleset/' + filename,
    '  url: ' + base + location,
    '  interval: ' + settings.refreshSeconds
  ].map(line => indent + line + endline).join('');
}
result = result.slice(0, match.index) + providers + result.slice(match.index + match[0].length);

await writeFile(output, result, { flag: 'wx' });
console.log('Prepared a private local profile with PikPak-Auto and ChatGPT-NonHK.');
