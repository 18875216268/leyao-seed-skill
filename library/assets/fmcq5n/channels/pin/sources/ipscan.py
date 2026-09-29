"""本地 IP 探测（pin 通道的源模块）——原「自建云函数」的原生本地化。

来历（2026-09-28）：把云函数的探测逻辑内置到用户本机——DNS 解析 + TCP 443 测活都在
**本机视角**完成，IP 候选天然适配本机线路（云函数在机房测的可达性 ≠ 本机真实可达性）。
零第三方依赖；出网 = DNS 解析、对 GitHub 官方 IP 的 TCP 443 连接、两个公共 hosts 源
（hosts.gitcdn.top / gitee.com，均已列入 manifest 白名单）。

内部链（pin/README「内部降级链」的事实源）：
  本地探测（53 域 DNS → TCP 443 测活，并发、总时限收口）
  → 外部 hosts 源（gitcdn / gitee 社区清单，解析标准 hosts 行）
  → 合并去重（ip+domain）→ 候选补测速 → 过滤不可达 → 每域 TOP-N
  → {domain: [ip]}（channel_pin.fetch_hosts 直接消费的格式）。

失败纪律：任何一步失败都返回**已得结果**（不抛出、不假装成功）；
`fetch_all` 的 `source` 语义与原云函数 API 对齐（ziyou / waibu / all）。
"""
from __future__ import annotations

import concurrent.futures as _cf
import json
import re
import socket
import time
import urllib.request

SCAN_TIMEOUT = 3.0       # 单 IP TCP 测活超时（秒）——与原云函数一致
# 一轮本地探测总上限（秒）——到点用已得结果。
# 实测定值（2026-09-28，5 轮真机采样）：median 4.79s / max 6.38s / 35~37 域解析成功、
# 69~85 存活 IP——8s 覆盖 P100 并留 ~25% 抖动余量。
SCAN_DEADLINE = 8.0
TOP_N = 10               # 每域最多保留候选数（与原云函数一致）
WORKERS = 32             # 并发线程数（DNS 与 TCP 均为阻塞 IO）
EXT_TIMEOUT = 10.0       # 外部 hosts 源拉取超时（秒）
PORT = 443

# GitHub 相关域清单（源自原云函数 ziyou 探测域，53 个；DNS 解析失败的域会被自然跳过）
DOMAINS = [
    # 核心
    "github.com",
    "gist.github.com",
    "github.io",
    "api.github.com",
    "codeload.github.com",
    "github.githubassets.com",
    "github.global.ssl.fastly.net",
    "github.map.fastly.net",
    "live.github.com",
    "central.github.com",
    # githubusercontent
    "raw.githubusercontent.com",
    "objects.githubusercontent.com",
    "objects-origin.githubusercontent.com",
    "avatars.githubusercontent.com",
    "avatars0.githubusercontent.com",
    "avatars1.githubusercontent.com",
    "avatars2.githubusercontent.com",
    "avatars3.githubusercontent.com",
    "avatars4.githubusercontent.com",
    "avatars5.githubusercontent.com",
    "cloud.githubusercontent.com",
    "media.githubusercontent.com",
    "user-images.githubusercontent.com",
    "release-assets.githubusercontent.com",
    "github-cloud.githubusercontent.com",
    "github-registry-files.githubusercontent.com",
    "github-releases.githubusercontent.com",
    # pkg
    "pkg-containers.githubusercontent.com",
    "pkg.actions.githubusercontent.com",
    "pkg.github.com",
    "npm.pkg.github.com",
    "npm-proxy.pkg.github.com",
    "npm-beta.pkg.github.com",
    "npm-beta-proxy.pkg.github.com",
    # actions
    "pipelines.actions.githubusercontent.com",
    "vstoken.actions.githubusercontent.com",
    "setup-tools.actions.githubusercontent.com",
    # githubapp
    "timestamp.githubapp.com",
    # s3
    "github-cloud.s3.amazonaws.com",
    "github-production-release-asset-2e65be.s3.amazonaws.com",
    "github-production-repository-file-5c1aeb.s3.amazonaws.com",
    "github-production-user-asset-6210df.s3.amazonaws.com",
]

# 外部 hosts 源（原云函数 waibu 的两个社区清单；只读、失败跳过）
EXTERNAL_SOURCES = [
    {"name": "gitcdn", "url": "https://hosts.gitcdn.top/hosts.txt"},
    {"name": "gitee", "url": "https://gitee.com/if-the-wind/github-hosts/raw/main/hosts"},
]

HOSTS_LINE = re.compile(r"^(\d{1,3}(?:\.\d{1,3}){3})\s+(\S+)\s*$")


def _tcp_latency(ip: str, timeout: float = SCAN_TIMEOUT) -> float | None:
    """TCP 443 连通性测试：可达返回延迟 ms，不可达返回 None。"""
    t0 = time.perf_counter()
    try:
        s = socket.create_connection((ip, PORT), timeout=timeout)
        s.close()
        return (time.perf_counter() - t0) * 1000
    except OSError:
        return None


def _resolve4(domain: str) -> list:
    """域名 → 去重后的 IPv4 列表；解析失败返回 []（域不可用，自然跳过）。"""
    try:
        infos = socket.getaddrinfo(domain, PORT, socket.AF_INET, socket.SOCK_STREAM)
        return sorted({i[4][0] for i in infos})
    except OSError:
        return []


def _run_pool(jobs: list, within: float) -> list:
    """并发执行 [(key, fn)]，`within` 秒内完成者才收（到点即收口，未完成的丢弃）。

    返回 [(key, result)]；within<=0 表示不限时（等待全部完成）。
    """
    out = []
    if not jobs:
        return out
    with _cf.ThreadPoolExecutor(max_workers=min(WORKERS, max(1, len(jobs)))) as ex:
        futs = {ex.submit(fn): key for key, fn in jobs}
        try:
            for f in _cf.as_completed(futs, timeout=(None if within <= 0 else max(0.1, within))):
                key = futs[f]
                try:
                    out.append((key, f.result()))
                except Exception:
                    continue
        except TimeoutError:
            pass                      # 到点收口：用已得结果（与重试纪律同一哲学）
    return out


def probe_local(domains: list | None = None, deadline: float = SCAN_DEADLINE) -> list:
    """本地探测：DNS 解析 → TCP 443 测活（并发、deadline 收口）。

    返回 [{"ip","domain","latency"}]（仅可达者）；对齐原云函数 `?source=ziyou`。
    """
    t0 = time.perf_counter()
    doms = list(dict.fromkeys(domains or DOMAINS))
    # 阶段一：DNS（并发；预算的一半）
    resolved = []
    for key, ips in _run_pool([(d, (lambda d=d: _resolve4(d))) for d in doms],
                              within=deadline * 0.5):
        if ips:
            resolved += [(ip, key) for ip in ips]
    # 阶段二：TCP 测活（并发；剩余预算）
    entries = []
    for (ip, dom), latency in _run_pool([( (ip, dom), (lambda ip=ip: _tcp_latency(ip)) )
                                         for ip, dom in resolved],
                                        within=max(0.1, deadline - (time.perf_counter() - t0))):
        if latency is not None:
            entries.append({"ip": ip, "domain": dom, "latency": round(latency)})
    return entries


def _fetch_text(url: str, timeout: float = EXT_TIMEOUT) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "github-web-skill/2.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def probe_external(sources: list | None = None, timeout: float = EXT_TIMEOUT) -> list:
    """外部 hosts 源：拉取并解析标准 hosts 行；对齐原云函数 `?source=waibu`。

    返回 [{"ip","domain"}]（无延迟，由 process_entries 统一补测速）；失败源跳过。
    """
    out = []
    for src in (sources or EXTERNAL_SOURCES):
        try:
            text = _fetch_text(src["url"], timeout)
        except Exception:
            continue
        for line in text.splitlines():
            m = HOSTS_LINE.match(line.strip())
            if m:
                out.append({"ip": m.group(1), "domain": m.group(2)})
    return out


def process_entries(entries: list, top_n: int = TOP_N,
                    deadline: float = 0.0) -> dict:
    """去重（ip+domain）→ 补测速 → 过滤不可达 → 每域 TOP-N → {domain: [ip]}。

    对齐原云函数 `process_entries` 的算法语义（TOP_N/来源序/延迟序）。
    """
    seen, unique = set(), []
    for e in entries:
        key = "%s|%s" % (e.get("ip"), e.get("domain"))
        if key not in seen:
            seen.add(key)
            unique.append(dict(e, order=len(unique)))
    # 补测速：无 latency 的候选统一实测（并发、deadline 收口）
    need = [(e["ip"], e) for e in unique if e.get("latency") is None]
    if need:
        got = {}
        for (ip, e), latency in _run_pool([(ip, (lambda ip=ip: _tcp_latency(ip))) for ip, _e in need],
                                          within=deadline):
            got[ip] = latency
        for e in unique:
            if e.get("latency") is None:
                e["latency"] = got.get(e["ip"])
    valid = [e for e in unique if e.get("latency") is not None]
    valid.sort(key=lambda e: (e.get("order", 0), e["latency"]))
    by_domain = {}
    for e in valid:
        arr = by_domain.setdefault(e["domain"], [])
        if len(arr) < max(1, int(top_n)):
            arr.append(e["ip"])
    return {d: ips for d, ips in sorted(by_domain.items())}


def fetch_all(source: str = "all", keyword: str = "", domains: list | None = None,
              deadline: float = SCAN_DEADLINE) -> dict:
    """总入口（与原云函数 `?source=` 语义对齐）：ziyou=本地探测；waibu=外部源；all=两者。

    keyword：子串过滤域名；domains：精确域过滤（优先于 keyword）。
    返回 {domain: [ip]}；任何失败都返回已得部分（不抛出）。
    """
    entries: list = []
    try:
        if source in ("ziyou", "all"):
            entries += probe_local(deadline=deadline)
        if source in ("waibu", "all"):
            entries += probe_external()
    except Exception:
        pass                       # 已得部分照常进入合并（不假装成功，也不抛给上层）
    dom_set = {d.strip() for d in (domains or []) if d and d.strip()} or None
    if dom_set:
        entries = [e for e in entries if e["domain"] in dom_set]
    elif keyword:
        kw = keyword.lower()
        entries = [e for e in entries if kw in e["domain"].lower()]
    try:
        return process_entries(entries, deadline=deadline)
    except Exception:
        return {}
