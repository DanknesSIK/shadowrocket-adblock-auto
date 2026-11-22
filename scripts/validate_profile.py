#!/usr/bin/env python3
"""Static profile/link/route regression checks, NOT the Shadowrocket compiler.

Uses Python's regex engine for a syntax sanity check. iOS regex behaviour,
DNS/GeoIP/ASN, imported nodes and real app traffic require device testing.
"""
import argparse
import concurrent.futures
import datetime
import hashlib
import ipaddress
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "profiles/FengGe.conf"
BUILTINS = {"PROXY", "DIRECT", "REJECT", "TAILSCALE"}
RULE_TYPES = {"DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "DOMAIN-WILDCARD",
              "USER-AGENT", "URL-REGEX", "IP-CIDR", "IP-CIDR6", "IP-ASN", "GEOIP"}
SOURCE_PREFIX = "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/"
SOURCE_PATTERN = re.compile(re.escape(SOURCE_PREFIX) + r"([0-9a-f]{40})/(rule/Shadowrocket/[A-Za-z0-9_]+/[A-Za-z0-9_]+\.list)")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def active(text):
    return [s for raw in text.splitlines() if (s := raw.strip())
            and not s.startswith(("#", ";", "//"))]


def parse_config(text):
    sections, current = {}, None
    for line in active(text):
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1]
            require(current not in sections, "Duplicate section " + current)
            sections[current] = []
        else:
            require(current is not None, "Line outside section")
            sections[current].append(line)
    require(set(sections) == {"General", "Proxy Group", "Rule", "Host", "MITM"},
            "Unexpected sections; review executable content or node credentials")
    return sections


def check_profile(raw):
    require(not raw.startswith(b"\xef\xbb\xbf"), "UTF-8 BOM")
    require(b"\r" not in raw and b"\0" not in raw, "Not plain LF text")
    text = raw.decode("utf-8")
    require(not re.search(r"(?im)^\s*(ca-p12|ca-passphrase|password|token|auth-key)\s*=", text),
            "Credentials in profile")
    require(not re.search(r"tail[0-9a-f]+\.ts\.net", text, re.I), "Private tailnet identifier")
    sections = parse_config(text)
    general = dict(line.split(" = ", 1) for line in sections["General"])
    require("100.64.0.0/10" not in general["tun-excluded-routes"], "Tailscale route excluded")
    for cidr in general["tun-excluded-routes"].split(","):
        ipaddress.ip_network(cidr.strip())
    require(sections["MITM"] == ["enable = false"], "MITM must be disabled")
    groups, regexes = {}, {}
    for line in sections["Proxy Group"]:
        name, value = line.split(" = ", 1)
        require(name not in groups, "Duplicate group " + name)
        parts = value.split(",")
        require(parts[0] in {"select", "url-test", "fallback"}, "Unsupported group type")
        members = [p for p in parts[1:] if "=" not in p]
        opts = dict(p.split("=", 1) for p in parts[1:] if "=" in p)
        require(set(opts) <= {"policy-select-name", "policy-regex-filter", "url", "interval", "tolerance", "timeout"}, "Unknown group option")
        if "policy-regex-filter" in opts:
            regexes[name] = re.compile(opts["policy-regex-filter"])
        if "policy-select-name" in opts:
            require(opts["policy-select-name"] in members, "Invalid default " + name)
        if parts[0] in {"url-test", "fallback"}:
            require(int(opts["interval"]) >= (600 if name in {"ChatGPT自动", "PikPak自动"} else 1800), "Aggressive testing interval")
        groups[name] = members
    policies = BUILTINS | groups.keys()
    for name, members in groups.items():
        require(all(m in policies for m in members), "Unresolved member " + name)

    def visit(name, stack):
        require(name not in stack, "Group cycle: " + ">".join(stack + [name]))
        for member in groups.get(name, []):
            visit(member, stack + [name])
    for name in groups:
        visit(name, [])
    rules = [line.split(",") for line in sections["Rule"]]
    require(sum(r[0] == "FINAL" for r in rules) == 1 and rules[-1] == ["FINAL", "漏网之鱼"], "Invalid final rule")
    require(len(sections["Rule"]) == len(set(sections["Rule"])), "Duplicate local rule")
    for r in rules:
        require(r[0] in RULE_TYPES | {"RULE-SET", "DOMAIN-SET", "FINAL"}, "Unknown rule type")
        policy = r[1] if r[0] == "FINAL" else r[2]
        require(policy in policies, "Unresolved rule policy " + policy)
        if r[0] in {"IP-CIDR", "IP-CIDR6"}:
            ipaddress.ip_network(r[1])
    for name, sample in {"香港节点": "HK01", "台湾节点": "台湾01", "日本节点": "JP-01",
                         "新加坡节点": "Singapore 01", "美国节点": "US01", "韩国节点": "KR-01"}.items():
        require(regexes[name].search(sample), "Regional regex mismatch " + name)
    for name in ("自动选择", "故障转移", "手动选择"):
        require(not regexes[name].search("剩余流量 30GB"), "Quota entry included")
        require(regexes[name].search("V1-香港HKT01|NF|VLESS"), "Realistic node excluded")
    for sample in ("香港01", "HK01", "hk-02", "Hong Kong 1", "HongKong02", "🇭🇰 01", "深港01", "剩余流量 30GB"):
        require(not regexes["ChatGPT自动"].search(sample), "ChatGPT excluded node admitted: " + sample)
    for sample in ("US01", "日本01", "台湾02", "SG01", "韩国01", "德国01", "新马来西亚3"):
        require(regexes["ChatGPT自动"].search(sample), "ChatGPT eligible node excluded: " + sample)
    require(regexes["PikPak自动"].search("HK01"), "PikPak must include Hong Kong")
    require(not regexes["PikPak自动"].search("剩余流量 30GB"), "PikPak quota entry included")
    return sections, groups, rules


def fetch(url):
    require(SOURCE_PATTERN.fullmatch(url), "Unpinned or unapproved rule source " + url)
    request = urllib.request.Request(url, headers={"User-Agent": "FengGe-Profile-Validator/1.0"})
    with urllib.request.urlopen(request, timeout=35) as response:
        require(response.geturl() == url, "Unexpected rule source redirect")
        data = response.read(4_000_001)
        status = response.status
    require(status == 200 and len(data) < 4_000_001, "Invalid response size/status")
    text = data.decode("utf-8-sig")
    require(not text.lstrip().startswith(("<", "{")), "HTML/JSON instead of rules")
    return data, text, status


def expand(rules):
    refs = [r for r in rules if r[0] in {"RULE-SET", "DOMAIN-SET"}]
    urls = [r[1] for r in refs]
    require(len(urls) == len(set(urls)), "Repeated remote URL")
    require(all(SOURCE_PATTERN.fullmatch(u) for u in urls), "Unpinned remote reference")
    require(len({SOURCE_PATTERN.fullmatch(u).group(1) for u in urls}) == 1,
            "Mixed upstream revisions")
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        fetched = dict(zip(urls, pool.map(fetch, urls)))
    expanded, sources = [], []
    for rule in rules:
        if rule[0] not in {"RULE-SET", "DOMAIN-SET"}:
            expanded.append(rule)
            continue
        kind, url, policy = rule
        data, text, status = fetched[url]
        entries = active(text)
        require(entries, "Empty remote file " + url)
        for line in entries:
            if kind == "DOMAIN-SET":
                require(re.fullmatch(r"\.?[\w-]+(?:\.[\w-]+)*", line), "Malformed domain " + line)
                expanded.append(["DOMAIN-SUFFIX" if line.startswith(".") else "DOMAIN", line.lstrip("."), policy])
            else:
                p = line.split(",")
                require(p[0] in RULE_TYPES and len(p) in (2, 3), "Unsupported upstream row " + line)
                require(len(p) == 2 or p[2] == "no-resolve", "Unexpected upstream policy/option " + line)
                if p[0] in {"IP-CIDR", "IP-CIDR6"}:
                    ipaddress.ip_network(p[1])
                expanded.append(p[:2] + [policy] + p[2:])
        sources.append({"type": kind, "url": url, "http_status": status,
                        "bytes": len(data), "entries": len(entries),
                        "sha256": hashlib.sha256(data).hexdigest()})
    return expanded, sources


def route(rules, host="", ip=None, country=None, asn=None):
    """Domain/IP samples only. Does not look up real DNS, ASN or GeoIP."""
    # Native compilation prioritizes domain rules over IP rules. This remains
    # a sample matcher, not a DNS resolver or a complete native compiler.
    if host:
        for r in rules:
            if r[0] == "DOMAIN" and host == r[1]:
                return r[2]
            if r[0] == "DOMAIN-SUFFIX" and (host == r[1] or host.endswith("." + r[1])):
                return r[2]
            if r[0] == "DOMAIN-KEYWORD" and r[1] in host:
                return r[2]
    address = ipaddress.ip_address(ip) if ip else None
    for r in rules:
        kind = r[0]
        if kind == "FINAL":
            return r[1]
        value, policy = r[1:3]
        if kind == "DOMAIN" and host == value:
            return policy
        if kind == "DOMAIN-SUFFIX" and (host == value or host.endswith("." + value)):
            return policy
        if kind == "DOMAIN-KEYWORD" and value in host:
            return policy
        if kind in {"IP-CIDR", "IP-CIDR6"} and address and address in ipaddress.ip_network(value):
            return policy
        if kind == "IP-ASN" and asn is not None and str(asn) == value:
            return policy
        if kind == "GEOIP" and country == value:
            return policy
    raise ValueError("No matching route")


def validate(raw):
    sections, groups, rules = check_profile(raw)
    expanded, sources = expand(rules)
    samples = {
        "hermes.staru.icu": "TAILSCALE", "secure.staru.icu": "TAILSCALE",
        "nas.local": "DIRECT", "nas.home.arpa": "DIRECT", "demo.tail-example.ts.net": "Hermes内网",
        "quickconnect.to": "DIRECT", "api.10jqka.com.cn": "DIRECT", "push.hexin.cn": "DIRECT",
        "www.10jqka.com": "DIRECT",
        "www.hexin.com.cn": "DIRECT",
        "www.myhexin.com": "DIRECT",
        "www.ths123.com": "DIRECT",
        "www.123ths.com": "DIRECT",
        "www.tonghuashun.com.cn": "DIRECT",
        "www.tonghuashun.cn": "DIRECT",
        "www.iwencai.com": "DIRECT",
        "quote.eastmoney.com": "DIRECT", "pay.alipay.com": "DIRECT", "wx.qq.com": "DIRECT",
        "servicewechat.com": "DIRECT", "api.deepseek.com": "DIRECT", "chat.qwen.ai": "DIRECT",
        "dashscope.aliyuncs.com": "DIRECT", "www.feishu.cn": "DIRECT", "api.kimi.com": "DIRECT",
        "chatgpt.com": "ChatGPT自动", "api.openai.com": "ChatGPT自动", "files.oaiusercontent.com": "ChatGPT自动",
        "api.anthropic.com": "AI服务", "claude.ai": "AI服务", "gemini.google.com": "AI服务",
        "aistudio.google.com": "AI服务", "notebooklm.google.com": "AI服务",
        "copilot.microsoft.com": "AI服务", "api.githubcopilot.com": "AI服务",
        "t.me": "Telegram", "api.telegram.org": "Telegram",
        "www.youtube.com": "YouTube", "rr1.googlevideo.com": "YouTube",
        "www.netflix.com": "国际影视", "www.disneyplus.com": "国际影视",
        "open.spotify.com": "Spotify", "www.tiktok.com": "TikTok",
        "github.com": "海外开发", "raw.githubusercontent.com": "海外开发",
        "www.google.com": "Google", "apple.com": "苹果服务", "www.icloud.com": "苹果服务",
        "outlook.com": "微软服务", "steamcommunity.com": "游戏平台",
        "download.steamcontent.com": "国内服务", "www.jd.com": "国内服务",
        "www.bilibili.com": "国内服务", "www.baidu.com": "国内服务", "www.qq.com": "国内服务",
        "ad.doubleclick.net": "广告拦截",
        "api-drive.mypikpak.com": "PikPak自动", "user.mypikpak.com": "PikPak自动",
        "hub5pnc.sandai.net": "PikPak自动",
        "oaistatic.com": "ChatGPT自动", "withpersona.com": "ChatGPT自动",
        "host.livekit.cloud": "ChatGPT自动",
        "chat.openai.com.cdn.cloudflare.net": "ChatGPT自动",
        "openai-api.arkoselabs.com": "ChatGPT自动", "chatgpt.livekit.cloud": "ChatGPT自动",
        "api.githubcopilotusercontent.com": "AI服务",
        "dns.alidns.com": "DIRECT", "nas.lan": "DIRECT",
    }
    outcomes = []
    for host, expected in samples.items():
        actual = route(expanded, host=host)
        require(actual == expected, f"Route {host}: expected {expected}, got {actual}")
        outcomes.append({"host": host, "expected": expected, "actual": actual})
    for ip, expected in [("100.123.3.89", "TAILSCALE"), ("192.168.8.8", "DIRECT"), ("10.20.30.40", "DIRECT"),
                         ("149.154.167.51", "Telegram")]:
        actual = route(expanded, ip=ip)
        require(actual == expected, f"IP route {ip}: {actual}")
        outcomes.append({"ip": ip, "expected": expected, "actual": actual})
    for country, expected in [("CN", "国内服务"), (None, "漏网之鱼")]:
        actual = route(expanded, host="unclassified.example", country=country)
        require(actual == expected, "Fallback order")
        outcomes.append({"host": "unclassified.example", "simulated_country": country,
                         "expected": expected, "actual": actual})
    # Regression: a non-AI server in AS20473 must not inherit the AI policy.
    actual = route(expanded, ip="108.61.5.82", asn=20473)
    require(actual == "漏网之鱼", "Unrelated cloud server hijacked by AI/other broad policy")
    outcomes.append({"ip": "108.61.5.82", "simulated_asn": 20473,
                     "expected": "漏网之鱼", "actual": actual})
    require(not any(r[0] == "IP-ASN" and r[1] == "20473" and r[2] == "AI服务" for r in expanded),
            "Broad OpenAI ASN rule reintroduced")
    report = {
        "validated_at": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
        "profile": "profiles/FengGe.conf", "profile_bytes": len(raw),
        "profile_sha256": hashlib.sha256(raw).hexdigest(), "groups": len(groups),
        "local_rule_lines": len(rules), "remote_files": len(sources),
        "expanded_rule_entries": len(expanded), "remote_bytes": sum(s["bytes"] for s in sources),
        "sample_checks_passed": len(outcomes), "device_tested": False,
        "upstream_commit": SOURCE_PATTERN.fullmatch(sources[0]["url"]).group(1),
        "limitations": ["Custom static validator, not the Shadowrocket parser/compiler",
                        "No device memory, disconnect, node throughput or service unlock testing",
                        "No real DNS, GeoIP database, ASN or User-Agent evaluation",
                        "All remote rules are pinned to the reported upstream commit; checks do not guarantee device behaviour"],
        "sources": sources, "route_samples": outcomes,
    }
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=Path, default=PROFILE)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = validate(args.profile.read_bytes())
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in {"sources", "route_samples"}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
