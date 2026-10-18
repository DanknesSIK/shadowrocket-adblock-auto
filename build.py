#!/usr/bin/env python3
"""Safe-by-default aggregator for public Shadowrocket modules.

No third-party JS execution or personal certificates. Network access is only
used to download configured raw.githubusercontent.com rule text.
"""
import collections
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
SECTIONS = ("Rule", "URL Rewrite", "Header Rewrite", "Body Rewrite", "Map Local", "Script")
MITM_HOST = re.compile(r"^(?:\*\.)?(?:[a-z0-9_-]+\.)+[a-z0-9_-]+$", re.I)
REJECT = re.compile(r"(?:^|,)\s*REJECT(?:-[A-Z-]+)?(?:,|$)", re.I)
URL_REJECT = re.compile(r"\s+-\s+reject(?:-200|-dict|-img|-array|-drop)?\s*$", re.I)
BODY_JQ = re.compile(r"^http-(?:response|request)-jq\s+", re.I)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def protected(text, domains):
    normalized = re.sub(r"\\+", "", text.lower().replace("[.]", "."))
    for domain in domains:
        p = re.escape(domain.lower())
        if re.search(r"(?<![a-z0-9_-])(?:[a-z0-9_*.-]+\.)?" + p + r"(?![a-z0-9_-])", normalized):
            return True
    return False


def fetch(url, limit):
    uri = urlparse(url)
    if uri.scheme != "https" or uri.hostname != "raw.githubusercontent.com":
        raise ValueError("Only raw.githubusercontent.com HTTPS sources are allowed")
    request = urllib.request.Request(url, headers={"User-Agent": "Shadowrocket-AdBlock-Auto/1.0"})
    with urllib.request.urlopen(request, timeout=35) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Source exceeds size limit: " + url)
    return data.decode("utf-8-sig"), digest(data)


def parse_shadowrocket(text):
    parsed = collections.defaultdict(list)
    section = None
    unknown = 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", ";", "//")):
            continue
        section_match = re.fullmatch(r"\[([^\]]+)\]", line)
        if section_match:
            section = section_match.group(1).strip()
            continue
        if section in (*SECTIONS, "MITM"):
            parsed[section].append(line)
        else:
            unknown += 1
    return parsed, unknown


def parse_qx(text):
    parsed = collections.defaultdict(list)
    unknown = 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", ";", "//")):
            continue
        if line.lower().startswith("hostname ="):
            parsed["MITM"].append(line)
        else:
            match = re.fullmatch(
                r"(\^https?[^\s]+)\s+url\s+(reject(?:-200|-dict|-img)?)", line, re.I
            )
            if match:
                parsed["URL Rewrite"].append(match.group(1) + " - " + match.group(2).lower())
            else:
                unknown += 1
    return parsed, unknown


def accepts(section, line, cfg):
    if len(line) > 15000:
        return False
    if protected(line, cfg["protected_domain_suffixes"]):
        return False
    if re.search(r"\b(ca-p12|ca-passphrase|password|authorization|set-cookie|cookie)\b", line, re.I):
        return False
    if section == "Rule":
        return bool(REJECT.search(line))
    if section == "URL Rewrite":
        return bool(URL_REJECT.search(line) and re.match(r"^\^?https?", line, re.I))
    if section == "Body Rewrite":
        return bool(BODY_JQ.match(line))
    if section == "Header Rewrite":
        return bool(cfg.get("include_header_rewrite"))
    if section == "Map Local":
        return bool(cfg.get("include_map_local"))
    if section == "Script":
        # Do not let a future upstream change enable executable JavaScript.
        return False
    return False


def mitm_hosts(lines, cfg):
    approved = cfg["mitm_selected_suffixes"]
    domains = cfg["protected_domain_suffixes"]
    result = []
    for line in lines:
        if not re.match(r"^hostname\s*=", line, re.I):
            continue
        values = line.partition("=")[2].replace("%APPEND%", "")
        for part in values.split(","):
            host = part.strip().lower()
            if not MITM_HOST.fullmatch(host) or protected(host, domains):
                continue
            if "*" in host and not host.startswith("*."):
                continue
            clean = host[2:] if host.startswith("*.") else host
            if not any(clean == p or clean.endswith("." + p) for p in approved):
                continue
            result.append(host)
    return result


def assemble(conf, downloaded):
    cfg = conf["settings"]
    enabled = [s for s in conf["sources"] if s["enabled"]]
    if not enabled:
        raise ValueError("At least one source must be enabled")
    combined = collections.defaultdict(list)
    unique = collections.defaultdict(set)
    all_hosts = []
    report_sources = []
    for source in enabled:
        contents, sha = downloaded[source["id"]]
        parser = parse_qx if source["format"] == "qx-basic" else parse_shadowrocket
        parsed, ignored = parser(contents)
        stats = collections.Counter()
        for section, lines in parsed.items():
            if section == "MITM":
                all_hosts.extend(mitm_hosts(lines, cfg))
                continue
            switches = {"Rule": "include_rules", "URL Rewrite": "include_url_rewrite",
                        "Body Rewrite": "include_body_rewrite", "Header Rewrite": "include_header_rewrite",
                        "Map Local": "include_map_local", "Script": "include_remote_scripts"}
            if not cfg.get(switches.get(section, "disabled"), False):
                stats["disabled"] += len(lines)
                continue
            for line in lines:
                if not accepts(section, line, cfg):
                    stats["filtered"] += 1
                    continue
                normalized = re.sub(r"\s+", " ", line).strip()
                if normalized in unique[section]:
                    stats["duplicate"] += 1
                    continue
                unique[section].add(normalized)
                combined[section].append(line)
                stats[section] += 1
        report_sources.append({
            "id": source["id"], "url": source["url"], "sha256": sha,
            "unknown_lines": ignored, "counts": dict(stats)
        })
    hosts = list(dict.fromkeys(all_hosts))
    lines = ["#!name=" + cfg["name"], "#!desc=" + cfg["description"],
             "#!author=Shadowrocket AdBlock Auto (sources credited in README)",
             "# Remote JavaScript is disabled. This is not an advertisement blocking guarantee.", ""]
    for section in SECTIONS:
        if combined[section]:
            lines.extend(["[" + section + "]", *combined[section], ""])
    if hosts:
        lines.extend(["[MITM]", "hostname = %APPEND% " + ",".join(hosts), ""])
    output = "\n".join(lines).rstrip() + "\n"
    output_len = len(output.encode("utf-8"))
    total = sum(len(combined[s]) for s in SECTIONS)
    if total < cfg["min_output_rules"] or output_len > cfg["max_output_bytes"]:
        raise ValueError("Output failed quality/size gate: %s rules / %s bytes" % (total, output_len))
    report = {
        "sources_enabled": len(enabled), "total_rules": total,
        "mitm_hosts": len(hosts), "bytes": output_len,
        "sha256": digest(output.encode("utf-8")),
        "remote_js_enabled": False,
        "warning": "Upstream rules and native rewrites are third party and have not been audited or device-tested.",
        "sources": report_sources
    }
    return output, report


def main():
    cfg = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
    fetched = {}
    for source in cfg["sources"]:
        if not source["enabled"]:
            continue
        print("Fetching " + source["id"], flush=True)
        fetched[source["id"]] = fetch(source["url"], cfg["settings"]["max_source_bytes"])
    content, report = assemble(cfg, fetched)
    destination = ROOT / "dist"
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "AllApps-Auto.sgmodule").write_text(content, encoding="utf-8")
    (destination / "build-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("SUCCESS: %d rules, %d hosts, %d bytes" %
          (report["total_rules"], report["mitm_hosts"], report["bytes"]))


if __name__ == "__main__":
    main()
