#!/usr/bin/env python3
"""Validate an immutable upstream snapshot before publishing profile changes.

Only the main configuration's rule URLs move. No fetched scripts are executed.
GitHub publishes the checked configuration and report in one git commit.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

from validate_profile import ROOT, SOURCE_PREFIX, parse_config, require, route, validate

REF_PATTERN = re.compile(re.escape(SOURCE_PREFIX) + r"(?:master|[0-9a-f]{40})/")
MAX_ENTRIES = 65000
MAX_BYTES = 1500000


def digest(data):
    return hashlib.sha256(data).hexdigest()


def current_upstream():
    # Git ref lookup avoids unauthenticated GitHub REST API rate limits and
    # does not need a personal token. The exact ref is checked before use.
    result = subprocess.run(
        ["git", "ls-remote", "--exit-code", "--refs",
         "https://github.com/blackmatrix7/ios_rule_script.git", "refs/heads/master"],
        check=True, capture_output=True, text=True, timeout=40)
    rows = [line.split() for line in result.stdout.splitlines() if line.strip()]
    require(len(rows) == 1 and len(rows[0]) == 2 and rows[0][1] == "refs/heads/master",
            "Unexpected upstream ref response")
    sha = rows[0][0]
    require(re.fullmatch(r"[0-9a-f]{40}", sha), "Invalid upstream commit")
    return sha


def pin(text, sha):
    require(re.fullmatch(r"[0-9a-f]{40}", sha), "Invalid commit")
    result, count = REF_PATTERN.subn(SOURCE_PREFIX + sha + "/", text)
    require(count > 0, "No rule references in template")
    return result.encode("utf-8")


def source_key(source):
    return source["url"].split("/rule/Shadowrocket/", 1)[1]


def check_budget(new, old=None):
    require(0 < new["expanded_rule_entries"] <= MAX_ENTRIES, "Total rule budget exceeded")
    require(0 < new["remote_bytes"] <= MAX_BYTES, "Total byte budget exceeded")
    ads = next((s for s in new["sources"] if source_key(s) == "AdvertisingLite/AdvertisingLite_Domain.list"), None)
    require(ads and 20000 <= ads["entries"] <= 50000, "Advertising source size anomaly")
    if old:
        previous = {source_key(s): s for s in old["sources"]}
        for source in new["sources"]:
            before = previous.get(source_key(source))
            if not before:
                continue  # New sources require a deliberate template edit.
            count = before["entries"]
            require(source["entries"] >= count - max(10, int(count * .25)),
                    "Source shrank unexpectedly: " + source_key(source))
            require(source["entries"] <= count + max(50, int(count * .35)),
                    "Source grew unexpectedly: " + source_key(source))


def emergency_profile(raw):
    """Offline diagnostic fallback, preserving explicit domain/IP routes."""
    sections = parse_config(raw.decode("utf-8"))
    general = [l for l in sections["General"] if not l.startswith(("update-url =", "dns-server ="))]
    general.insert(0, "dns-server = system")
    lines = [
        "# 凤歌应急配置 | 无远程规则、无脚本、无解密、无自动测速",
        "# 首页选择可用节点，全局路由选择配置；停用所有旧模块。",
        "# 仅保留本地基础分流。没有广告过滤，不能替代完整主配置。",
        "# 只使用系统 DNS；不启用或自动关闭客户端全局 Tailscale 设置。",
        "# 局域网 NAS 可用，远程 ts.net 访问被拒绝，避免误送到公共代理。",
        "# 如需排查 Tailscale，请在客户端手动关闭其全局开关。",
        "# 不自动更新本文件；主配置恢复后切回 FengGe.conf。", "",
        "[General]", *general, "", "[Rule]",
    ]
    for line in sections["Rule"]:
        p = line.split(",")
        if p[0] in {"RULE-SET", "DOMAIN-SET"}:
            continue
        if p[0] == "FINAL":
            lines.append("FINAL,PROXY")
            continue
        policy = p[2]
        p[2] = "REJECT" if policy == "Hermes内网" else (
            "DIRECT" if policy in {"DIRECT", "国内服务", "苹果服务", "微软服务"} else "PROXY")
        lines.append(",".join(p))
    # Broad domestic domains provide useful operation even with no remote table.
    pos = lines.index("GEOIP,CN,DIRECT")
    basics = [f"DOMAIN-SUFFIX,{d},DIRECT" for d in (
        "qq.com", "gtimg.com", "taobao.com", "tmall.com", "alicdn.com", "jd.com",
        "360buyimg.com", "baidu.com", "bdstatic.com", "bilibili.com", "bilivideo.com",
        "hdslb.com", "douyin.com", "163.com", "126.com", "netease.com", "weibo.com",
        "apple.com", "icloud.com", "icloud-content.com", "mzstatic.com",
        "microsoft.com", "microsoftonline.com", "live.com", "outlook.com", "office.com",
        "office.net", "office365.com", "windowsupdate.com")]
    lines[pos:pos] = basics
    lines.extend(["", "[Host]", *sections["Host"], "", "[MITM]", "enable = false", ""])
    return "\n".join(lines).encode("utf-8")


def check_emergency(raw):
    text = raw.decode("utf-8")
    require(not raw.startswith(b"\xef\xbb\xbf") and b"\r" not in raw, "Emergency text encoding")
    require(not re.search(r"(?m)^(RULE-SET|DOMAIN-SET|update-url|\[Proxy Group\]|\[Script\])", text),
            "Emergency profile has external dependencies or testing groups")
    section = None
    rules = []
    for line in text.splitlines():
        if line.startswith("["):
            section = line
        elif line and not line.startswith("#") and section == "[Rule]":
            p = line.split(",")
            require((p[1] if p[0] == "FINAL" else p[2]) in {"DIRECT", "PROXY", "REJECT"},
                    "Emergency profile uses undefined policy")
            rules.append(p)
    require(sum(p[0] == "FINAL" for p in rules) == 1 and rules[-1] == ["FINAL", "PROXY"], "Emergency final")
    samples = {"wx.qq.com": "DIRECT", "api.10jqka.com.cn": "DIRECT", "www.jd.com": "DIRECT",
               "nas.local": "DIRECT", "chatgpt.com": "PROXY", "gemini.google.com": "PROXY",
               "copilot.microsoft.com": "PROXY", "outlook.com": "DIRECT", "apple.com": "DIRECT",
               "demo.tail-example.ts.net": "REJECT"}
    for host, expected in samples.items():
        require(route(rules, host=host) == expected, "Emergency sample failed: " + host)
    return len(samples)


def same_sources(a, b):
    return {source_key(s): s["sha256"] for s in a["sources"]} == {
        source_key(s): s["sha256"] for s in b["sources"]}


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_bytes(data)
    os.replace(temp, path)


def update(root=ROOT, sha=None):
    profile = root / "profiles/FengGe.conf"
    report_path = root / "profiles/validation-report.json"
    emergency_path = root / "profiles/FengGe-Emergency.conf"
    old_raw = profile.read_bytes() if profile.exists() else None
    old_report = json.loads(report_path.read_text()) if report_path.exists() else None
    require(bool(old_raw) == bool(old_report), "Missing published profile or validation report")
    if old_report:
        require(digest(old_raw) == old_report["profile_sha256"],
                "Published file differs from its report; edit templates/FengGe.conf instead")
    revision = sha or current_upstream()
    candidate = pin((root / "templates/FengGe.conf").read_text(encoding="utf-8"), revision)
    report = validate(candidate)
    check_budget(report, old_report)
    emergency = emergency_profile(candidate)
    emergency_checks = check_emergency(emergency)
    # Upstream commits unrelated to these rule files do not force phone updates.
    if old_raw and same_sources(report, old_report):
        normalized_old = REF_PATTERN.sub(SOURCE_PREFIX + "master/", old_raw.decode("utf-8"))
        normalized_new = REF_PATTERN.sub(SOURCE_PREFIX + "master/", candidate.decode("utf-8"))
        old_pinned = not (SOURCE_PREFIX + "master/").encode() in old_raw
        if normalized_old == normalized_new and old_pinned and emergency_path.exists() and emergency_path.read_bytes() == emergency:
            print("PASS: sources and configuration unchanged; no publish needed")
            return False
    report["release_guard"] = {"max_rule_entries": MAX_ENTRIES, "max_remote_bytes": MAX_BYTES,
                               "max_large_source_growth": .35, "max_large_source_drop": .25}
    report["emergency_profile"] = {"path": "profiles/FengGe-Emergency.conf", "bytes": len(emergency),
                                   "sha256": digest(emergency), "sample_checks_passed": emergency_checks}
    # No output is changed until every fetch, rule check and budget check passes.
    atomic_write(profile, candidate)
    atomic_write(emergency_path, emergency)
    atomic_write(report_path, (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print(f"PASS: prepared {report['remote_files']} sources, {report['sample_checks_passed']} main + {emergency_checks} emergency samples; upstream {revision}")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream-sha", help="Optional exact revision; default resolves upstream master once")
    args = parser.parse_args()
    update(sha=args.upstream_sha)


if __name__ == "__main__":
    main()
