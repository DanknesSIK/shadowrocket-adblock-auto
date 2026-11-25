import { createHash } from 'node:crypto';
import { readFile, mkdir, writeFile } from 'node:fs/promises';

const manifest = JSON.parse(await readFile(new URL('sources.json', import.meta.url), 'utf8'));
const mirror = new URL('mirror/', import.meta.url);
const reportPath = new URL('upstream-status.json', import.meta.url);
const allowedAclTypes = /^(DOMAIN(-SUFFIX|-KEYWORD)?|IP-CIDR6?|PROCESS-NAME|URL-REGEX),\S/;
const allowedPikPakTypes = /^DOMAIN(-SUFFIX|-KEYWORD)?,[a-z0-9.-]+$/i;

async function download(url) {
  const response = await fetch(url, { redirect: 'error', signal: AbortSignal.timeout(25000) });
  if (!response.ok) throw new Error('HTTP ' + response.status + ' for ' + url);
  const data = new Uint8Array(await response.arrayBuffer());
  if (data.length === 0 || data.length > 2_000_000) throw new Error('Unexpected size: ' + url);
  return new TextDecoder('utf-8', { fatal: true }).decode(data);
}

async function head(source) {
  const url = new URL('https://api.github.com/repos/' + source.repo + '/commits/' + source.ref);
  const sha = JSON.parse(await download(url)).sha;
  if (!/^[a-f0-9]{40}$/.test(sha)) throw new Error('Invalid source commit: ' + source.repo);
  return sha;
}

function raw(source, sha, path) {
  return new URL('https://raw.githubusercontent.com/' + source.repo + '/' + sha + '/' + path);
}

function checkedAcl(text, path) {
  const rules = text.split(/\r?\n/).map(line => line.trim())
    .filter(line => line && !/^[#!;]/.test(line));
  if (!rules.length || rules.some(rule => !allowedAclTypes.test(rule))) {
    throw new Error('Unexpected ACL4SSR rule format: ' + path);
  }
  return rules.length;
}

function checkedPikPak(text) {
  const lines = text.split(/\r?\n/).map(line => line.trim()).filter(line => line && !line.startsWith('#'));
  if (lines.shift() !== 'payload:' || !lines.length) throw new Error('Missing PikPak payload');
  const rules = lines.map(line => line.replace(/^-\s+/, ''));
  if (!lines.every(line => line.startsWith('- ')) || rules.some(rule => !allowedPikPakTypes.test(rule))) {
    throw new Error('Unexpected PikPak domain rule');
  }
  return [...new Set([...rules, ...manifest.consumer.pikpakRequired])].sort();
}

function record(path, text, rules = null) {
  return { path, rules, sha256: createHash('sha256').update(text).digest('hex') };
}

async function lastSnapshot() {
  try {
    return JSON.parse(await readFile(reportPath, 'utf8'));
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
    return null;
  }
}

const [aclSha, pikpakSha, previous] = await Promise.all([
  head(manifest.acl), head(manifest.pikpak), lastSnapshot()
]);

const files = new Map();
const records = [];
for (let offset = 0; offset < manifest.acl.paths.length; offset += 6) {
  const batch = manifest.acl.paths.slice(offset, offset + 6);
  const values = await Promise.all(batch.map(path => download(raw(manifest.acl, aclSha, path))));
  for (const [index, path] of batch.entries()) {
    const text = values[index];
    const output = 'acl4ssr/' + path;
    files.set(output, text);
    records.push(record(output, text, checkedAcl(text, path)));
  }
}

const [aclLicense, pikpakLicense, pikpakText] = await Promise.all([
  download(raw(manifest.acl, aclSha, 'LICENCE')),
  download(raw(manifest.pikpak, pikpakSha, 'LICENSE')),
  download(raw(manifest.pikpak, pikpakSha, manifest.pikpak.path))
]);
if (!aclLicense.startsWith('Attribution-ShareAlike 4.0 International') ||
    !pikpakLicense.includes('GNU GENERAL PUBLIC LICENSE')) throw new Error('Upstream license changed');

const pikpak = checkedPikPak(pikpakText);
const pikpakOutput = [
  '# PikPak rules derived from blackmatrix7/ios_rule_script; original author: tugepaopao.',
  '# Source: ' + raw(manifest.pikpak, pikpakSha, manifest.pikpak.path).href,
  '# See licenses/blackmatrix7-LICENSE. Two service domains are ensured locally.',
  ...pikpak, ''
].join('\n');
files.set('pikpak.list', pikpakOutput);
files.set('licenses/ACL4SSR-LICENCE', aclLicense);
files.set('licenses/blackmatrix7-LICENSE', pikpakLicense);
records.push(record('pikpak.list', pikpakOutput, pikpak.length));
records.push(record('licenses/ACL4SSR-LICENCE', aclLicense));
records.push(record('licenses/blackmatrix7-LICENSE', pikpakLicense));

// Treat a sudden loss of most of any list as a potential upstream error.
const oldCounts = new Map((previous?.files ?? []).map(entry => [entry.path, entry.rules]));
for (const item of records) {
  const old = oldCounts.get(item.path);
  if (old >= 10 && item.rules < Math.ceil(old / 2)) {
    throw new Error('Rule list shrank by more than half: ' + item.path);
  }
}

for (const [path, text] of files) {
  const address = new URL(path, mirror);
  await mkdir(new URL('./', address), { recursive: true });
  await writeFile(address, text);
}
const report = {
  sources: { [manifest.acl.repo]: aclSha, [manifest.pikpak.repo]: pikpakSha },
  files: records
};
await writeFile(reportPath, JSON.stringify(report, null, 2) + '\n');
console.log('Checked ' + manifest.acl.paths.length + ' ACL4SSR lists and ' + pikpak.length + ' PikPak rules.');
