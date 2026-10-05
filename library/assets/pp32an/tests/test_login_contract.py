#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""登录器契约锁（离线、不弹窗、不触网）：锁 2026-10-05 修复的三处问题。

① state 往返还原 —— 旧实现 f-string 手工拼转义，`/` 被写成 `\\/` 还叠了一层，
   JSON 解析出的 redirect_uri 带反斜杠、不等于登记给服务端的站点地址；
   服务端宽容才没炸，且零测试覆盖。此处锁死「解析后 == SITE + "/"」。
③ 死 import —— math / tempfile / io as _io 曾全文件零引用，此处防回潮。
④ verify_credential 的 info —— 曾只在 validate_remote 分支内赋值，
   函数末尾 `if validate_remote and info` 靠 and 短路才没抛 UnboundLocalError。
   预置 info={} 后，validate_remote=False 路径必须照常返回 dict（不依赖短路求值）。

②（uuid 兜底）经确认为既有设计、不属缺陷，不在本文件管辖内。
"""
import ast
import json
import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
LEYOU = SKILL / "scripts" / "sources" / "leyou"
sys.path.insert(0, str(LEYOU))

import login_leyou_cloud as lg   # noqa: E402


class TestOAuthState(unittest.TestCase):
    """① state 必须能被回调端解析，且 redirect_uri 还原为登记用的站点地址。"""

    def test_state_roundtrip(self):
        raw = lg.build_oauth_state()
        parsed = json.loads(raw)                      # 必须是合法 JSON
        self.assertEqual(parsed["tannant_id"], lg.TENANT_ID)
        self.assertEqual(parsed["source"], "work_wechat")
        # 契约核心：与 _prepare 里 get-auth-url 登记的 redirect_uri（SITE + "/"）一致
        self.assertEqual(parsed["redirect_uri"], lg.SITE + "/")

    def test_state_redirect_uri_has_no_backslash(self):
        """旧 bug 的特征就是解析结果里混进反斜杠——这里直接锁死不得出现。"""
        parsed = json.loads(lg.build_oauth_state())
        self.assertNotIn("\\", parsed["redirect_uri"])

    def test_state_compact_json(self):
        """保持与旧实现的紧凑形态一致（无空格分隔），降低服务端兼容风险。"""
        raw = lg.build_oauth_state()
        self.assertEqual(raw, json.dumps(json.loads(raw), separators=(",", ":"),
                                         ensure_ascii=True))

    def test_prepare_uses_helper(self):
        """_prepare 必须经由 build_oauth_state() 取 state，不允许再回到手拼转义。"""
        src = (LEYOU / "login_leyou_cloud.py").read_text(encoding="utf-8")
        self.assertIn("state = build_oauth_state()", src)
        self.assertNotIn('SITE.replace("https://"', src)   # 旧写法的特征串，禁止回潮


class TestVerifyCredentialNoUnbound(unittest.TestCase):
    """④ validate_remote=False（--no-remote）路径不得依赖 and 短路求值。"""

    def test_no_remote_returns_dict_without_crash(self):
        res = lg.verify_credential(token="contract-test-token", validate_remote=False,
                                   token_file=str(HERE / "no-such-credential.json"))
        self.assertIsInstance(res, dict)
        self.assertTrue(res.get("ok"))            # 本地检查通过（显式给了 token）
        self.assertTrue(res.get("authenticated"))

    def test_missing_token_reports_missing(self):
        res = lg.verify_credential(validate_remote=False,
                                   token_file=str(HERE / "no-such-credential.json"))
        self.assertFalse(res.get("ok"))
        self.assertEqual(res.get("reason"), "missing")


class TestNoDeadImports(unittest.TestCase):
    """③ 登录器本体不得再出现未使用的 import（tkinter 可用性探测除外）。"""

    def test_no_unused_imports(self):
        src = (LEYOU / "login_leyou_cloud.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        imported = {}
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                for a in n.names:
                    imported[(a.asname or a.name).split(".")[0]] = n.lineno
            elif isinstance(n, ast.ImportFrom):
                for a in n.names:
                    imported[a.asname or a.name] = n.lineno
        used = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Name):
                used.add(n.id)
            elif isinstance(n, ast.Attribute):
                x = n
                while isinstance(x, ast.Attribute):
                    x = x.value
                if isinstance(x, ast.Name):
                    used.add(x.id)
        unused = [k for k in imported if k not in used and k != "annotations"
                  and k != "tkinter"]          # tkinter 是 try/except 里的可用性探测，豁免
        self.assertEqual(unused, [], "发现未使用的 import: %s" % unused)


if __name__ == "__main__":
    unittest.main()
