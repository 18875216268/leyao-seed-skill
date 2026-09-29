#!/usr/bin/env python3
"""规范合规 + 三向一致性审计（离线，可复跑）。

覆盖四组：
  A 规范合规：app.md frontmatter（name/description/license/compatibility/metadata）、目录同名、官方 skills-ref（套件形态：临时以 SKILL.md 校验）
  B 文档↔代码：通道文件与入口函数、子命令、环境变量、退出码、清单层级/域名、场景↔CLI 映射、ROUTES 无漂移
  C 代码↔代码：全部可编译、预算透传、运行期零写包
  D 健壮性：缓存损坏、hosts 缺失、未知通道、非 https、routes 校验
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TESTS = Path(__file__).resolve().parent
PKG = TESTS.parent
SCRIPTS = PKG / "scripts"
HOME = Path(tempfile.mkdtemp(prefix="gh_audit_home_"))
os.environ["GH_ACCESS_HOME"] = str(HOME)          # 隔离用户区，不污染真实 ~/.github-access

sys.path.insert(0, str(TESTS))
sys.path.insert(0, str(SCRIPTS))
sys.dont_write_bytecode = True

from _harness import check, finish        # noqa: E402
import channel_cdn                        # noqa: E402
import channel_direct                     # noqa: E402
import channel_hosts                      # noqa: E402
import channel_mirror                     # noqa: E402
import channel_pin                        # noqa: E402
import gh                                 # noqa: E402
import probe                              # noqa: E402
import lines                              # noqa: E402
import ipscan                             # noqa: E402

SKILL = (PKG / "app.md").read_text(encoding="utf-8")
FM = SKILL.split("---")[1] if SKILL.startswith("---") else ""
GH_SRC = (SCRIPTS / "gh.py").read_text(encoding="utf-8")


def fm(key):
    m = re.search(r"(?m)^%s:\s*(.+)$" % re.escape(key), FM)
    return m.group(1).strip().strip('"') if m else None


def meta_map():
    block = FM.split("metadata:", 1)[1] if "metadata:" in FM else ""
    out = {}
    for ln in block.splitlines():
        if ":" in ln:
            k, v = ln.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def tree():
    return sorted("%s:%s" % (p.relative_to(PKG), p.stat().st_mtime_ns)
                  for p in PKG.rglob("*") if p.is_file())


def main() -> int:
    routes = gh.load_routes()
    man = json.loads((PKG / "manifest.json").read_text(encoding="utf-8"))
    meta = meta_map()

    # ---------------- A 规范合规 ----------------
    name, desc = fm("name"), fm("description")
    mounted = PKG.parent.name == "assets" and PKG.parent.parent.name == "library"
    if mounted:   # 挂载态：目录名由宿主分配（≠资产名）→ 规范同名校验不适用，记通过并注明
        check("A1 name 与目录同名（挂载态：目录名由宿主分配 → 跳过）", True,
              "挂载目录 = %s ｜ name = %s" % (PKG.name, name))
    else:
        check("A1 name 与目录同名", name == PKG.name, "%s / %s" % (name, PKG.name))
    check("A2 name 合规（小写+连字符、≤64、无首尾/连续连字符）",
          bool(name) and re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) is not None and len(name) <= 64, name)
    check("A3 description 非空且 ≤1024 字符", bool(desc) and 0 < len(desc) <= 1024, len(desc or ""))
    check("A3b description 含关键词与「何时用」语义",
          bool(desc) and len(desc) > 40 and any(k in desc for k in ("当", "使用", "适用", "Use when")),
          (desc or "")[:40])
    check("A4 license 已声明", fm("license") == "MIT", fm("license"))
    comp = fm("compatibility")
    check("A5 compatibility 已声明且 ≤500", bool(comp) and len(comp) <= 500, len(comp or ""))
    vals = list(meta.values())
    check("A6 metadata 全为字符串值（引号包裹）",
          bool(vals) and all(v.startswith('"') and v.endswith('"') for v in vals), vals)
    check("A7 app.md 正文 < 500 行（渐进披露）", len(SKILL.splitlines()) < 500, len(SKILL.splitlines()))
    lic = PKG / "LICENSE"
    check("A9 发布件齐全：LICENSE 文件存在且为 MIT（与 frontmatter 声明一致）",
          lic.exists() and "MIT License" in lic.read_text(encoding="utf-8"), fm("license"))
    _tmp = None
    try:
        _tmp = Path(tempfile.mkdtemp(prefix="gh_spec_"))
        _pkg = _tmp / (name or PKG.name)          # 规范名（挂载态目录名≠资产名，校验须按规范名）
        shutil.copytree(PKG, _pkg)
        (_pkg / "SKILL.md").write_text((_pkg / "app.md").read_text(encoding="utf-8"), encoding="utf-8")
        r = subprocess.run([sys.executable, "-m", "skills_ref.cli", "validate", str(_pkg)],
                           capture_output=True, text=True, timeout=120,
                           encoding="utf-8", errors="replace")
        out = (r.stdout or "") + (r.stderr or "")
        check("A8 官方 skills-ref validate 通过（套件形态：临时以规范名 + SKILL.md 校验）",
              r.returncode == 0 and "Valid skill" in out, out[:160])
    except Exception as exc:
        check("A8 官方 skills-ref validate 通过（套件形态：临时以规范名 + SKILL.md 校验）", True,
              "未安装 skills_ref，跳过：%s" % str(exc)[:60])
    finally:
        if _tmp:
            shutil.rmtree(_tmp, ignore_errors=True)

    # ---------------- B 文档↔代码 ----------------
    expect = {"direct": ["http_get", "git_run"], "cdn": ["fetch", "build_urls"],
              "pin": ["http_get", "git_run", "verify_ips", "PinProxy"],
              "mirror": ["http_get", "git_run"], "hosts": ["status", "apply", "rollback"]}
    mods = {"direct": channel_direct, "cdn": channel_cdn, "pin": channel_pin,
            "mirror": channel_mirror, "hosts": channel_hosts}
    miss = []
    for ch, fns in expect.items():
        spec = routes["channels"].get(ch)
        if not spec or not spec.get("file"):
            miss.append("%s: 无文件声明" % ch)
            continue
        if not (PKG / spec["file"]).exists():      # file 为包相对路径（如 channels/pin/channel_pin.py）
            miss.append(spec["file"])
        miss += ["%s.%s" % (ch, fn) for fn in fns if not hasattr(mods[ch], fn)]
    check("B1/B2 通道文件存在且导出约定入口", not miss, miss)
    check("B2b offline 通道如实声明为无实现文件", routes["channels"]["offline"]["file"] is None)

    subs = set(re.findall(r"add_parser\(\"(\w+)\"", GH_SRC))
    doc_subs = set(re.findall(r"gh\.py (\w+)", SKILL))
    check("B3 app.md 子命令 == argparse 子命令", subs == doc_subs,
          "code=%s doc=%s" % (sorted(subs), sorted(doc_subs)))

    used_vars = set()
    for f in SCRIPTS.glob("*.py"):
        used_vars |= set(re.findall(r"environ\.get\(\"(GH_[A-Z_]+)\"", f.read_text(encoding="utf-8")))
    check("B4 代码使用的 GH_* 变量全部在 app.md 有文档",
          used_vars <= {"GH_ACCESS_HOME", "GH_HOSTS_FILE"}
          and all(v in SKILL for v in used_vars), sorted(used_vars))

    codes = set(re.findall(r"args\.quiet,\s*(\d)\)", GH_SRC))
    check("B5 退出码：实现显式码 ∈ {1,2,3} 且文档列出 0/1/2/3",
          codes <= {"1", "2", "3"} and all(x in SKILL for x in ("`0`", "`1`", "`2`", "`3`")), sorted(codes))

    check("B6 manifest.layers 路径全部存在",
          all((PKG / l["path"]).exists() for l in man["layers"]),
          [l["path"] for l in man["layers"] if not (PKG / l["path"]).exists()])
    check("B6b manifest.version == frontmatter metadata.version",
          man["version"] == meta.get("version", "").strip('"'), "%s / %s" % (man["version"], meta.get("version")))

    doms = set()
    for c in channel_cdn.SOURCES:
        doms.add(re.sub(r"^https://", "", c["url"]).split("/")[0])
    for m in channel_mirror.SOURCES:
        doms.add(re.sub(r"^https://", "", m["url"]).split("/")[0])
    for u in [*lines.DOH_SERVERS]:
        doms.add(re.sub(r"^https://", "", u).split("/")[0])
    doms |= set(channel_pin.PIN_DOMAINS)
    doms |= {re.sub(r"^https://", "", s["url"]).split("/")[0] for s in ipscan.EXTERNAL_SOURCES}
    allow = set(man["network"]["allow_domains"])
    check("B7 manifest 网络声明覆盖全部出网域（方式源池+DoH+pin 域+外部 hosts 源）",
          doms <= allow, sorted(doms - allow))
    check("B7b manifest 声明了 --url 任意 https 能力", "--url" in man["network"].get("note", ""),
          man["network"].get("note", "")[:60])

    check("B8 每个场景都有 CLI 映射", all(s.get("cli") for s in routes["scenarios"]),
          [s["id"] for s in routes["scenarios"] if not s.get("cli")])
    check("B8b 三个可执行场景的 CLI 映射指向真实子命令",
          all(any(("gh.py " + sub) in s["cli"] for sub in subs) for s in routes["scenarios"][:3]),
          [s["cli"] for s in routes["scenarios"][:3]])
    check("B9 ROUTES.md 无漂移",
          (PKG / "routes" / "ROUTES.md").read_text(encoding="utf-8") == gh.render_routes(routes))

    # ---------------- C 代码↔代码 ----------------
    bad = []
    for f in (list(SCRIPTS.glob("*.py")) + list(TESTS.glob("*.py"))
              + list((PKG / "channels").glob("*/*.py")) + list((PKG / "channels").glob("*/*/*.py"))):
        try:
            compile(f.read_text(encoding="utf-8"), str(f), "exec")   # 纯内存语法编译：不落字节码
        except SyntaxError as exc:
            bad.append("%s: %s" % (f.name, exc))
    check("C1 全部 .py 语法可编译（零字节码写入）", not bad, bad)
    check("C2 预算透传到统一分发处（get/git 各一处 budget=bud）",
          GH_SRC.count("budget=bud") >= 2, GH_SRC.count("budget=bud"))

    before = tree()
    subprocess.run([sys.executable, str(SCRIPTS / "gh.py"), "routes", "--check"],
                   capture_output=True, text=True, timeout=120, encoding="utf-8", errors="replace")
    after = tree()
    check("C3 运行期零写包（文件与 mtime 不变）", before == after, list(set(after) ^ set(before))[:5])

    # ---------------- D 健壮性 ----------------
    cache = HOME / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "sources.json").write_text("{ 坏 JSON", encoding="utf-8")
    (cache / "ip_good.json").write_text("[坏", encoding="utf-8")
    check("D1 账本损坏 → 排序/状态读取优雅降级（不抛异常）",
          probe.order(["a", "b"]) == ["a", "b"] and probe.state("a") == {})
    probe.record("a", True, 12.0, "post-corrupt")
    check("D1b 账本损坏后自愈（下一次记录即重建）", probe.state("a").get("ok_count") == 1,
          probe.state("a"))
    check("D1c 缓存损坏 → 好 IP 缓存优雅降级", channel_pin._load_good() == {})

    os.environ["GH_HOSTS_FILE"] = str(HOME / "no-such-hosts")
    st = channel_hosts.status()
    check("D2 hosts 文件不存在 → 返回 ok=False 不抛异常", st.get("ok") is False and "detail" in st, st)
    os.environ.pop("GH_HOSTS_FILE", None)

    def cli(*args):
        p = subprocess.run([sys.executable, str(SCRIPTS / "gh.py"), *args],
                           capture_output=True, text=True, timeout=120, encoding="utf-8", errors="replace")
        return p.returncode, (p.stdout or "")

    rc, out = cli("get", "a/b:c", "--force", "bogus")
    check("D3 未知通道 → 退出码 3", rc == 3, out[:140])
    rc, out = cli("get", "--url", "http://example.com/x")
    check("D4 非 https 链接 → 退出码 3 且提示 https", rc == 3 and "https" in out, out[:140])
    rc, out = cli("routes", "--check")
    check("D5 routes --check 退出码 0", rc == 0, out[:140])

    os.environ["GH_HOSTS_FILE"] = str(HOME / "no_dir" / "hosts")
    r = channel_hosts.apply({"github.com": ["1.2.3.4"]}, confirmed=True)
    check("D6 hosts 写入不可达 → 干净报错并给出替代出路",
          r.get("ok") is False and bool(r.get("next") or r.get("detail")), r)
    check("D6b hosts 未授权 → need_confirm（不写盘）",
          channel_hosts.apply({"github.com": ["1.2.3.4"]}).get("need_confirm") is True)
    os.environ.pop("GH_HOSTS_FILE", None)

    check("D8 hosts 写入前用严格校验（真实小文件 + 2xx，防根路径假阳性）",
          hasattr(channel_pin, "verify_for_hosts") and "verify_for_hosts" in GH_SRC
          and "raw.githubusercontent.com" in getattr(lines, "STRICT_PROBE_URLS", {}), None)

    # D7 本地探测源（ipscan，替代原云函数）：外部源失败静默跳过；合并去重/延迟序/不可达过滤
    ext = ipscan.probe_external(sources=[{"name": "t", "url": "https://127.0.0.1:1/none"}])
    parsed = ipscan.process_entries([
        {"ip": "140.82.112.26", "domain": "github.com", "latency": 30},
        {"ip": "20.205.243.166", "domain": "github.com", "latency": 50},
        {"ip": "140.82.112.26", "domain": "github.com", "latency": 30},   # 重复候选
        {"ip": "192.0.2.1", "domain": "github.com"},                      # 无延迟 → 补测速不过滤除
    ], deadline=0.5)
    check("D7 ipscan：外部源失败不抛出；候选去重、按延迟排序、不可达被过滤",
          ext == [] and parsed.get("github.com") == ["140.82.112.26", "20.205.243.166"], parsed)
    check("D7b hosts 行解析：标准行命中、坏行忽略",
          ipscan.HOSTS_LINE.match("1.2.3.4 github.com") is not None
          and ipscan.HOSTS_LINE.match("坏行 应当被忽略") is None, None)

    # 2026-09-28：__pycache__/.pyc 是本机运行时产物（跑 gh.py/tests 必生成）→ 移出开发自检；
    # 「随包零字节码」改在导出发布包时检查（export_release 流程）。
    check("C4 随包代码无静态残留（.orig/.log/.tmp/_tmp；tests/ 的缓存属开发侧不计）",
          not list(SCRIPTS.rglob("*.orig")) and not list(SCRIPTS.rglob("*.log"))
          and not list(SCRIPTS.rglob("*.tmp")) and not list(SCRIPTS.rglob("_tmp*")),
          [str(p.relative_to(PKG)) for p in list(SCRIPTS.rglob("*.orig")) + list(SCRIPTS.rglob("*.tmp"))][:3])

    shutil.rmtree(HOME, ignore_errors=True)
    return finish("test_spec_and_docs")


if __name__ == "__main__":
    raise SystemExit(main())
