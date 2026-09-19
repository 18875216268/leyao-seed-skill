#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
乐药云智库 API 完整封装（AI 友好 CLI / 可 import）
========================================================
本文件负责「业务」：搜索 / 详情 / 翻页 / 下载 / 采集 / AI 问答（全部支持并发，--workers 上限 50）。
登录与凭证已迁至独立登录器 `login_leyou_cloud.py`（单文件自包含；与 BI/PMS 登录器同构）——
本文件的 status / login 命令对登录器做兼容转发，凭证文件（--token-file）与输出结构保持不变。

命令一览：
  status                    检查当前 token 是否有效（登录器校验：本地 + 远端）
  login                     扫码登录并保存凭证（登录器转发；默认弹窗）
  （业务命令 token 失效时：自动重登 → 重试原命令一次；--no-auto-login 时直接报错退出码3）

  search / categories / children / summary / detail / next / prev / jump /
  download / get-attachments / collect / ask

输出规范（AI 友好）：
  * 所有命令输出严格 JSON；--compact 输出单行便于机器解析
  * 退出码：0=成功 1=业务错误 2=参数错误 3=需要登录 4=网络/超时
  * 凭证自动持久化到 token 文件（默认用户区），后续命令自动复用

用法示例：
  python leyou_cloud.py status
  python leyou_cloud.py search 毛利 --page 1 --pagesize 10
  python leyou_cloud.py detail <slug> --html
  python leyou_cloud.py collect 毛利 --workers 12 --download
  python leyou_cloud.py get-attachments <slug> --dir ./files --workers 8
"""
import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter

# 同目录独立登录器（登录实现唯一来源；本文件不再内嵌登录代码）
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from login_leyou_cloud import (                       # noqa: E402
    TENANT_ID, SITE, BASE_GET, DEFAULT_UUID, UA,
    DEFAULT_TOKEN_FILE,
    relogin, verify_credential,
    load_credential, save_credential,
    LeyouLoginError, TokenExpired, LoginRequired,
)

# ---------------- 常量（业务专属；站点常量见 login_leyou_cloud.py） ----------------
BASE_API      = "https://api.helplook.net"              # 写操作 / AI 域名
MAX_WORKERS   = 50                                       # 并发硬上限（用户要求 50）


# ---------------- 工具函数 ----------------
def _plain(html):
    """HTML -> 纯文本（去标签、压缩空白）"""
    if not html:
        return ""
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()

def _kind_of(url):
    """按扩展名判断附件类型"""
    ext = (url.split("?")[0].split("#")[0].split(".")[-1] or "").lower()
    if ext in ("pdf",):                 return "pdf"
    if ext in ("ppt", "pptx", "pps"):   return "ppt"
    if ext in ("png", "jpg", "jpeg", "gif", "webp", "bmp", "svg", "ico"): return "image"
    if ext in ("doc", "docx", "xls", "xlsx", "csv", "txt", "md"):         return "doc"
    if ext in ("zip", "rar", "7z"):     return "archive"
    return "other"

def _extract_resources(html):
    """从正文 HTML 提取全部资源直链（附件 a 标签 + iframe/embed/object 内嵌 PDF/PPT）"""
    out, seen = [], set()
    if not html:
        return out
    patterns = [
        r"<a[^>]+href=['\"]([^'\"]+)['\"][^>]*>([^<]*)</a>",
        r"<iframe[^>]+src=['\"]([^'\"]+)['\"]",
        r"<embed[^>]+src=['\"]([^'\"]+)['\"]",
        r"<object[^>]+data=['\"]([^'\"]+)['\"]",
    ]
    for pat in patterns:
        for m in re.finditer(pat, html, re.I):
            url = m.group(1)
            if url.startswith("//"):
                url = "https:" + url
            if url not in seen:
                seen.add(url)
                name = ""
                if len(m.groups()) > 1 and m.group(2):
                    name = m.group(2).strip()
                if "resource-wangsu" in url or "helplook.net" in url or name:
                    out.append({"name": name or os.path.basename(url.split("?")[0]) or url,
                                "url": url, "kind": _kind_of(url)})
    # 仅保留资源直链（去锚点/去页面链接噪声）
    return [r for r in out if "resource-wangsu" in r["url"] or r["kind"] in ("pdf", "ppt")]

def _emit(out, compact=False):
    s = json.dumps(out, ensure_ascii=False,
                   separators=(",", ":") if compact else None,
                   indent=None if compact else 2)
    print(s)


# ---------------- 主封装类 ----------------
class LeyouCloud:
    def __init__(self, token=None, uuid=None, token_file=DEFAULT_TOKEN_FILE,
                 workers=10, timeout=20, auto_login=True):
        self.token_file = token_file
        self.workers = max(1, min(int(workers or 10), MAX_WORKERS))
        self.timeout = timeout
        self.auto_login = auto_login

        store = load_credential(token_file)
        self.token = token or store.get("token")
        self.uuid = uuid or store.get("uuid") or DEFAULT_UUID
        self.login_at = store.get("login_at")
        self.expires_at = store.get("expires_at")
        self.watermark = store.get("watermark")

        self.session = self._new_session()

    # ---------- 会话 ----------
    def _new_session(self):
        s = requests.Session()
        s.headers.update({
            "User-Agent": UA,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": SITE + "/",
        })
        if self.token:
            s.headers["x-auth-token"] = self.token
        # 连接池调大以支撑并发（上限 50 时留余量）
        ad = HTTPAdapter(pool_connections=100, pool_maxsize=100, max_retries=0)
        s.mount("https://", ad)
        s.mount("http://", ad)
        return s

    def _request(self, url, params=None, headers=None, stream=False, timeout=None):
        """带重试的 GET；业务码 507 抛 TokenExpired"""
        t = timeout or self.timeout
        last = None
        for i in range(3):
            try:
                r = self.session.get(url, params=params, headers=headers,
                                     stream=stream, timeout=t)
                # 解析业务码
                if not stream and "application/json" in (r.headers.get("Content-Type", "") or "") or (r.text or "").lstrip().startswith("{"):
                    try:
                        j = r.json()
                        if isinstance(j, dict) and j.get("code") == 507:
                            raise TokenExpired(j.get("msg", "Invalid token"))
                    except (ValueError, requests.exceptions.JSONDecodeError):
                        pass
                return r
            except TokenExpired:
                raise
            except requests.exceptions.RequestException as e:
                last = e
                time.sleep(0.5 * (i + 1))
        raise last or requests.exceptions.ConnectionError("请求失败")

    def _get(self, url, params=None, headers=None, stream=False):
        return self._request(url, params, headers, stream)

    def _save(self):
        save_credential(self.token_file, {
            "token": self.token, "uuid": self.uuid,
            "login_at": self.login_at, "expires_at": self.expires_at,
            "watermark": self.watermark,
        })

    # ================= 登录 / 凭证（转发独立登录器 login_leyou_cloud.py） =================
    def check_login(self):
        """token 有效性检测（委托独立登录器：本地 + 远端 get-list 200/507 实测协议）"""
        res = verify_credential(token=self.token, uuid=self.uuid,
                                token_file=self.token_file, validate_remote=True,
                                session=self.session)
        if res.get("authenticated"):
            return True, {"categories": res.get("categories", 0),
                          "first_category": res.get("first_category", "")}
        return False, {}

    def login(self, quiet=False):
        """扫码登录（兼容壳）：实现已迁移至 login_leyou_cloud.relogin（原生弹窗）；
        成功后刷新本实例状态并返回 whoami（输出结构与旧版一致）。"""
        cred = relogin(token_file=self.token_file, quiet=quiet)
        self.token = cred["token"]
        self.uuid = cred.get("uuid") or self.uuid
        self.watermark = cred.get("watermark", "")
        self.login_at = cred.get("login_at")
        self.expires_at = cred.get("expires_at")
        self.session.headers["x-auth-token"] = self.token
        return self.whoami()

    def whoami(self):
        """返回当前用户登录信息 / 请求凭证"""
        return {
            "ok": True, "logged_in": bool(self.token),
            "token": self.token,
            "uuid": self.uuid,
            "watermark": self.watermark,
            "login_at": self.login_at,
            "expires_at": self.expires_at,
            "cookies": {
                "hlsdk_token_cp7nb9": self.token or "",
                "hl_siteid_8980": self.token or "",
                "hl_uuid": self.uuid or "",
            },
            "endpoints": {
                "get": BASE_GET, "api": BASE_API, "site": SITE,
            },
        }

    def search(self, keyword, page=1, pagesize=10):
        """关键字搜索（分页）"""
        r = self._get(f"{BASE_GET}/foreground/tannant/search-tannant", {
            "tannant_id": TENANT_ID, "keyword": keyword, "page": page,
            "pagesize": pagesize, "uuid": self.uuid, "search_item": "all",
            "content_ids": "", "tag_names": ""})
        d = r.json().get("data") or {}
        lst = d.get("list") or []
        total = d.get("total") or 0
        items = [{
            "name": it.get("name", ""),
            "slug": it.get("slug", ""),
            "type": it.get("type", ""),          # 1=目录 2=文档
            "summary": _plain(it.get("summary", "") or it.get("description", "")),
        } for it in lst]
        return {"ok": True, "keyword": keyword, "total": total,
                "page": int(d.get("page") or page),
                "page_size": int(d.get("page_size") or pagesize),
                "total_pages": (total + pagesize - 1) // pagesize if total else 0,
                "list": items}

    def _search_page(self, args):
        kw, page, ps = args
        r = self._get(f"{BASE_GET}/foreground/tannant/search-tannant", {
            "tannant_id": TENANT_ID, "keyword": kw, "page": page, "pagesize": ps,
            "uuid": self.uuid, "search_item": "all", "content_ids": "", "tag_names": ""})
        d = r.json().get("data") or {}
        return d.get("list") or [], d.get("total") or 0

    def search_all_pages(self, keyword, pagesize=10):
        """并发搜索全部命中页（阶段2并发能力）"""
        first, total = self._search_page((keyword, 1, pagesize))
        items = list(first)
        pages = (total + pagesize - 1) // pagesize
        if pages > 1:
            with ThreadPoolExecutor(max_workers=self.workers) as ex:
                futs = [ex.submit(self._search_page, (keyword, p, pagesize))
                        for p in range(2, pages + 1)]
                for f in as_completed(futs):
                    lst, _ = f.result()
                    if lst:
                        items.extend(lst)
        return total, items

    def categories(self):
        """获取栏目/搜索目录（get-list data_type=1）"""
        r = self._get(f"{BASE_GET}/foreground/content/get-list",
                      {"tannant_id": TENANT_ID, "data_type": 1})
        lst = (r.json().get("data") or {}).get("list") or []
        return {"ok": True, "categories": [{
            "name": c.get("name", ""), "slug": c.get("slug", ""),
            "type": c.get("type", ""), "id": c.get("id", ""),
        } for c in lst]}

    def children(self, slug, recursive=False, _path="", _depth=0, _seen=None):
        """获取目录子项（get-content 的 child 字段，实测确认）；recursive 递归展开（去重防环）"""
        seen = _seen if _seen is not None else {slug}
        d = self._detail_raw(slug)
        childs = d.get("child") or []
        out = []
        for c in childs:
            node = {"name": c.get("name", ""), "slug": c.get("slug", ""),
                    "type": c.get("type", ""),
                    "path": (_path + "/" + c.get("name", "")) if _path else c.get("name", "")}
            out.append(node)
            cs = c.get("slug")
            if recursive and c.get("type") == "1" and cs and cs not in seen and _depth < 8:
                seen.add(cs)
                try:
                    out.extend(self.children(cs, True, node["path"], _depth + 1, seen)["items"])
                except Exception:
                    pass
        return {"ok": True, "slug": slug, "count": len(out),
                "recursive": recursive, "items": out}

    def summary(self, slug):
        """获取搜索结果摘要/介绍：标题 + 正文前 200 字 + 附件/子项概览"""
        d = self._detail_raw(slug)
        text = _plain((d.get("content") or {}).get("content", ""))
        res = _extract_resources((d.get("content") or {}).get("content", ""))
        childs = d.get("child") or []
        return {"ok": True,
                "name": d.get("name", ""), "slug": slug, "type": d.get("type", ""),
                "summary": text[:200] + ("..." if len(text) > 200 else ""),
                "text_length": len(text),
                "attachments": len(res),
                "children": len(childs),
                "updated_at": d.get("update_time", ""),
                "next_step": {"hint": "查看完整内容: python leyou_cloud.py detail " + slug}}

    def detail(self, slug, with_html=False):
        """获取完整页面内容：标题/正文/附件列表/目录子项"""
        d = self._detail_raw(slug)
        html = (d.get("content") or {}).get("content", "") or ""
        res = _extract_resources(html)
        childs = d.get("child") or []
        out = {"ok": True, "name": d.get("name", ""), "slug": slug,
               "type": d.get("type", ""),
               "text": _plain(html),
               "attachments": res,
               "children": [{"name": c.get("name", ""), "slug": c.get("slug", ""),
                             "type": c.get("type", "")} for c in childs],
               "updated_at": d.get("update_time", "")}
        if with_html:
            out["html"] = html
        return out

    def _detail_raw(self, slug):
        r = self._get(f"{BASE_GET}/foreground/content/get-content",
                      {"tannant_id": TENANT_ID, "slug": slug})
        return r.json().get("data") or {}

    # ---------- 翻页（下一页 / 上一页 / 跳页） ----------
    def next_page(self, keyword, page, pagesize=10):
        return self.search(keyword, page + 1, pagesize)

    def prev_page(self, keyword, page, pagesize=10):
        return self.search(keyword, max(1, page - 1), pagesize)

    def jump(self, keyword, page, pagesize=10):
        return self.search(keyword, max(1, int(page)), pagesize)

    # ---------- 下载 ----------
    def download(self, url, out=None, out_dir=None):
        """下载单个附件（PDF/PPT/图片等）；resource-wangsu 免鉴权带 Referer 最稳"""
        name = os.path.basename(url.split("?")[0].split("#")[0]) or "download.bin"
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
            out = os.path.join(out_dir, name)
        elif not out:
            out = name
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with self.session.get(url, headers={"Referer": SITE + "/"},
                              stream=True, timeout=60) as r:
            r.raise_for_status()
            size = 0
            with open(out, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
                    size += len(chunk)
        return {"ok": True, "url": url, "file": os.path.abspath(out),
                "size": size, "kind": _kind_of(url)}

    def get_attachments(self, slug, out_dir="downloads"):
        """并发下载某文档的全部附件（PDF/PPT/图片等）"""
        d = self._detail_raw(slug)
        html = (d.get("content") or {}).get("content", "") or ""
        res = _extract_resources(html)
        if not res:
            return {"ok": True, "slug": slug, "downloaded": [], "failed": [],
                    "message": "该文档没有附件"}
        dir_slug = re.sub(r"[^\w\-]", "_", slug)
        target = os.path.join(out_dir, dir_slug)
        os.makedirs(target, exist_ok=True)
        results, failed = [], []
        def _dl(item):
            try:
                r = self.download(item["url"], out_dir=target)
                return r, item
            except Exception as e:
                return {"ok": False, "url": item["url"], "error": str(e)}, item
        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            futs = [ex.submit(_dl, it) for it in res]
            for f in as_completed(futs):
                r, it = f.result()
                (results if r.get("ok") else failed).append({**r, "name": it["name"]})
        return {"ok": True, "slug": slug, "attachments": len(res),
                "downloaded": results, "failed": failed,
                "dir": os.path.abspath(target)}

    def collect(self, keyword, out="", download_dir=None, pagesize=10):
        """并发全库采集：并发搜全部页 → 并发抓全部详情 →（可选）并发下载附件"""
        total, items = self.search_all_pages(keyword, pagesize)
        # 去重 slug
        seen, slugs = set(), []
        for it in items:
            s = it.get("slug")
            if s and s not in seen:
                seen.add(s)
                slugs.append(s)

        docs, failed = [], []
        def _detail(sl):
            try:
                d = self._detail_raw(sl)
                if not d.get("name"):
                    return None, sl
                html = (d.get("content") or {}).get("content", "") or ""
                return {"name": d["name"], "slug": sl, "type": d.get("type", ""),
                        "text": _plain(html),
                        "attachments": _extract_resources(html)}, None
            except Exception:
                return None, sl
        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            futs = [ex.submit(_detail, s) for s in slugs]
            for f in as_completed(futs):
                doc, sl = f.result()
                (docs if doc else failed).append(doc or {"slug": sl})

        saved = ""
        if out:
            payload = {"keyword": keyword, "total_hits": total,
                       "fetched": len(docs), "failed": len(failed),
                       "docs": docs}
            with open(out, "w", encoding="utf-8") as fp:
                json.dump(payload, fp, ensure_ascii=False, indent=2)
            saved = os.path.abspath(out)

        att_dl = None
        if download_dir:
            att_dl = []
            def _dl_att(doc):
                try:
                    return self.get_attachments(doc["slug"], out_dir=download_dir)
                except Exception:
                    return None
            with ThreadPoolExecutor(max_workers=self.workers) as ex:
                for f in as_completed([ex.submit(_dl_att, d) for d in docs]):
                    r = f.result()
                    if r and r.get("ok"):
                        att_dl.append({"slug": r["slug"], "downloaded": len(r.get("downloaded", []))})

        return {"ok": True, "keyword": keyword, "total_hits": total,
                "searched_items": len(items), "fetched": len(docs),
                "failed": [f for f in failed if f],
                "saved": saved, "download_dir": os.path.abspath(download_dir) if download_dir else "",
                "attachments_downloaded": att_dl}

    # ---------- AI 问答（SSE） ----------
    def ask(self, question, stream_print=True):
        r = self.session.get(f"{BASE_API}/foreground/chats/stream",
                             params={"tannant_id": TENANT_ID, "token": self.token,
                                     "question": question, "content_ids": ""},
                             stream=True, timeout=120)
        full = []
        for line in r.iter_lines(decode_unicode=True):
            if line:
                full.append(line)
                if stream_print:
                    print(line, flush=True)
        return {"ok": True, "question": question, "raw_lines": full}


# ---------------- CLI ----------------
def _build_parser():
    p = argparse.ArgumentParser(
        prog="leyou_cloud",
        description="乐药云智库 API 完整封装：阶段1登录凭证 + 阶段2搜索/详情/翻页/下载，全功能并发",
        epilog="示例: python leyou_cloud.py search 毛利 --page 1 | python leyou_cloud.py collect 毛利 --workers 12 --download")
    p.add_argument("--token", help="手动指定 token（默认读 token 文件）")
    p.add_argument("--token-file", default=DEFAULT_TOKEN_FILE, help="token 持久化文件路径")
    p.add_argument("--workers", type=int, default=argparse.SUPPRESS, help="并发数 1-50（默认10）")
    p.add_argument("--no-auto-login", action="store_true", default=False, help="token 失效时不自动扫码，直接报错退出码3")
    p.add_argument("--compact", action="store_true", default=argparse.SUPPRESS, help="单行 JSON 输出（机器解析友好）")

    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name, help_, *pos_args):
        sp = sub.add_parser(name, help=help_)
        # 全局参数下沉到子命令，支持 `cmd --compact` 写法。
        # default 用 SUPPRESS：未显式提供时不写 namespace，
        # 避免子解析器(独立 namespace)的 default 覆盖命令前传入的值
        sp.add_argument("--compact", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
        sp.add_argument("--workers", type=int, default=argparse.SUPPRESS, help=argparse.SUPPRESS)
        for a in pos_args:
            sp.add_argument(*a[0], **a[1])
        return sp

    add("status", "检查登录状态（阶段1）")
    add("login", "扫码登录并保存凭证（阶段1）")
    add("search", "关键字搜索", (("keyword",), {"help": "搜索关键词"}),
        (("--page",), {"type": int, "default": 1}),
        (("--pagesize",), {"type": int, "default": 10}))
    add("categories", "获取栏目/搜索目录")
    add("children", "获取目录子项（可递归）", (("slug",), {"help": "目录 slug"}),
        (("--recursive",), {"action": "store_true", "help": "递归展开全部子项"}))
    add("summary", "获取摘要/介绍", (("slug",), {"help": "文档 slug"}))
    add("detail", "获取完整页面内容", (("slug",), {"help": "文档 slug"}),
        (("--html",), {"action": "store_true", "help": "同时输出正文 HTML"}))
    add("next", "下一页", (("keyword",), {}), (("page",), {"type": int, "help": "当前页"}),
        (("--pagesize",), {"type": int, "default": 10}))
    add("prev", "上一页", (("keyword",), {}), (("page",), {"type": int, "help": "当前页"}),
        (("--pagesize",), {"type": int, "default": 10}))
    add("jump", "跳转指定页", (("keyword",), {}), (("page",), {"type": int, "help": "目标页"}),
        (("--pagesize",), {"type": int, "default": 10}))
    add("download", "下载单个附件", (("url",), {"help": "附件直链"}),
        (("--out",), {"default": ""}), (("--out-dir",), {"default": ""}))
    add("get-attachments", "并发下载文档全部附件", (("slug",), {}),
        (("--dir",), {"default": "downloads"}))
    add("collect", "并发全库采集", (("keyword",), {}),
        (("--out",), {"default": "", "help": "保存 JSON 路径"}),
        (("--download",), {"default": "", "help": "附件下载目录"}),
        (("--pagesize",), {"type": int, "default": 10}))
    add("ask", "AI 助手问答（SSE 流式）", (("question",), {}))
    return p


def main(argv=None):
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    args = _build_parser().parse_args(argv)
    # 全局参数兜底归一（default=SUPPRESS 时未显式提供则无属性）
    args.compact = getattr(args, "compact", False)
    args.workers = getattr(args, "workers", 10)
    cloud = LeyouCloud(token=args.token, token_file=args.token_file,
                       workers=args.workers, auto_login=not args.no_auto_login)

    def need_login():
        """阶段1入口：有效直接过；无效自动登录（默认弹窗）；禁止自动登录则抛 LoginRequired"""
        ok, _ = cloud.check_login()
        if not ok and cloud.auto_login:
            cloud.login(quiet=True)
        elif not ok:
            raise LoginRequired
        return cloud.whoami()

    def run2(fn, *a, **kw):
        """阶段2统一执行入口：执行中 token 失效（507）→ 自动回阶段1重登 → 重试原命令一次。
        兑现「失效自动回退重试」承诺；--no-auto-login 时直接抛 TokenExpired（退出码3）。"""
        try:
            return fn(*a, **kw)
        except TokenExpired:
            if not cloud.auto_login:
                raise
            cloud.login(quiet=True)
            return fn(*a, **kw)

    try:
        cmd = args.cmd
        if cmd == "status":
            ok, info = cloud.check_login()
            out = {"ok": True, "logged_in": ok, **info, **cloud.whoami()}
            if not ok:
                out["hint"] = "执行: python leyou_cloud.py login 扫码登录"
        elif cmd == "login":
            out = cloud.login()
        elif cmd == "search":
            need_login(); out = run2(cloud.search, args.keyword, args.page, args.pagesize)
        elif cmd == "categories":
            need_login(); out = run2(cloud.categories)
        elif cmd == "children":
            need_login(); out = run2(cloud.children, args.slug, args.recursive)
        elif cmd == "summary":
            need_login(); out = run2(cloud.summary, args.slug)
        elif cmd == "detail":
            need_login(); out = run2(cloud.detail, args.slug, args.html)
        elif cmd == "next":
            need_login(); out = run2(cloud.next_page, args.keyword, args.page, args.pagesize)
        elif cmd == "prev":
            need_login(); out = run2(cloud.prev_page, args.keyword, args.page, args.pagesize)
        elif cmd == "jump":
            need_login(); out = run2(cloud.jump, args.keyword, args.page, args.pagesize)
        elif cmd == "download":
            need_login(); out = run2(cloud.download, args.url, args.out, args.out_dir)
        elif cmd == "get-attachments":
            need_login(); out = run2(cloud.get_attachments, args.slug, args.dir)
        elif cmd == "collect":
            need_login(); out = run2(cloud.collect, args.keyword, args.out, args.download, args.pagesize)
        elif cmd == "ask":
            need_login(); out = run2(cloud.ask, args.question, not args.compact)
        else:
            out = {"ok": False, "error": "UNKNOWN_COMMAND", "message": "未知命令: " + cmd}
            _emit(out, args.compact)
            return 2

        _emit(out, args.compact)
        return 0

    except TokenExpired:
        _emit({"ok": False, "error": "TOKEN_EXPIRED",
               "message": "token 已失效",
               "hint": "执行: python leyou_cloud.py login 扫码获取新凭证（或 --no-auto-login 时手动处理）"}, args.compact)
        return 3
    except LoginRequired as e:
        _emit({"ok": False, "error": "LOGIN_REQUIRED",
               "message": str(e) or "需要登录",
               "hint": "执行: python leyou_cloud.py login"}, args.compact)
        return 3
    except LeyouLoginError as e:
        _emit({"ok": False, "error": e.to_dict(),
               "hint": "执行: python login_leyou_cloud.py 扫码登录"}, args.compact)
        return 3 if e.code in ("AUTH_REQUIRED", "LOGIN_CANCELLED") else 1
    except requests.exceptions.RequestException as e:
        _emit({"ok": False, "error": "NETWORK_ERROR", "message": repr(e)[:200]}, args.compact)
        return 4
    except (RuntimeError, ValueError, KeyError) as e:
        _emit({"ok": False, "error": "BUSINESS_ERROR", "message": str(e)[:300]}, args.compact)
        return 1


if __name__ == "__main__":
    sys.exit(main())
