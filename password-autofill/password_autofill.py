"""
パスワード自動入力ツール - 完全オフライン版
外部ライブラリ不要・Python標準ライブラリのみで動作
Windows専用（ctypes経由でSendInput APIを使用）
"""

import sys
import tkinter as tk
from tkinter import ttk, messagebox
import json
import base64
import threading
import time
import webbrowser
import ctypes
import ctypes.wintypes as wintypes
from pathlib import Path
import os

# ============================================================
# Windows キーボード入力シミュレーション（ctypes / 標準ライブラリのみ）
# ============================================================

PUL = ctypes.POINTER(ctypes.c_ulong)

class _KeyBdInput(ctypes.Structure):
    _fields_ = [
        ("wVk",         wintypes.WORD),
        ("wScan",       wintypes.WORD),
        ("dwFlags",     wintypes.DWORD),
        ("time",        wintypes.DWORD),
        ("dwExtraInfo", PUL),
    ]

class _MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx",          wintypes.LONG),
        ("dy",          wintypes.LONG),
        ("mouseData",   wintypes.DWORD),
        ("dwFlags",     wintypes.DWORD),
        ("time",        wintypes.DWORD),
        ("dwExtraInfo", PUL),
    ]

class _HardwareInput(ctypes.Structure):
    _fields_ = [
        ("uMsg",   wintypes.DWORD),
        ("wParamL",wintypes.WORD),
        ("wParamH",wintypes.WORD),
    ]

class _InputUnion(ctypes.Union):
    _fields_ = [("ki", _KeyBdInput), ("mi", _MouseInput), ("hi", _HardwareInput)]

class _Input(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("ii", _InputUnion)]

KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_KEYUP   = 0x0002
INPUT_KEYBOARD    = 1

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_EXTRA  = ctypes.pointer(ctypes.c_ulong(0))

def _make_key_input(scan, flags):
    inp = _Input()
    inp.type = INPUT_KEYBOARD
    inp.ii.ki.wVk = 0
    inp.ii.ki.wScan = scan
    inp.ii.ki.dwFlags = flags
    inp.ii.ki.time = 0
    inp.ii.ki.dwExtraInfo = _EXTRA
    return inp

def _send(inputs):
    arr = (_Input * len(inputs))(*inputs)
    _user32.SendInput(len(inputs), arr, ctypes.sizeof(_Input))

def type_unicode(text: str, delay: float = 0.03):
    """Unicode文字をそのまま入力（日本語IDにも対応）"""
    for ch in text:
        code = ord(ch)
        _send([
            _make_key_input(code, KEYEVENTF_UNICODE),
            _make_key_input(code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP),
        ])
        time.sleep(delay)

def press_vk(vk: int):
    """仮想キーコードでキーを押す（Tab/Enterなど）"""
    inp_dn = _Input()
    inp_dn.type = INPUT_KEYBOARD
    inp_dn.ii.ki.wVk = vk
    inp_dn.ii.ki.wScan = 0
    inp_dn.ii.ki.dwFlags = 0
    inp_dn.ii.ki.time = 0
    inp_dn.ii.ki.dwExtraInfo = _EXTRA

    inp_up = _Input()
    inp_up.type = INPUT_KEYBOARD
    inp_up.ii.ki.wVk = vk
    inp_up.ii.ki.wScan = 0
    inp_up.ii.ki.dwFlags = KEYEVENTF_KEYUP
    inp_up.ii.ki.time = 0
    inp_up.ii.ki.dwExtraInfo = _EXTRA

    _send([inp_dn, inp_up])

VK_TAB   = 0x09
VK_RETURN= 0x0D

# ============================================================
# データ保存（JSON + Base64、標準ライブラリのみ）
# ============================================================

DATA_FILE = Path(os.path.dirname(os.path.abspath(__file__))) / "autofill_data.json"

def _enc(pw: str) -> str:
    return base64.b64encode(pw.encode("utf-8")).decode("ascii")

def _dec(s: str) -> str:
    return base64.b64decode(s.encode("ascii")).decode("utf-8")

def load_entries():
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_entries(entries):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

# ============================================================
# 自動入力ロジック
# ============================================================

def do_autofill(url, user_id, password, wait_sec, tab_count,
                auto_enter, status_cb, countdown_cb):
    """
    1. ブラウザを開く
    2. カウントダウン（ユーザーがIDフィールドをクリックする時間）
    3. IDを入力 → Tab(n回) → パスワード入力 → (Enter)
    """
    status_cb("ブラウザを起動中...")
    webbrowser.open(url)

    for remaining in range(wait_sec, 0, -1):
        countdown_cb(remaining)
        time.sleep(1)

    countdown_cb(0)
    status_cb("IDを入力中...")
    type_unicode(user_id)

    for _ in range(tab_count):
        time.sleep(0.1)
        press_vk(VK_TAB)

    time.sleep(0.15)
    status_cb("パスワードを入力中...")
    type_unicode(password)

    if auto_enter:
        time.sleep(0.1)
        press_vk(VK_RETURN)

    status_cb("入力完了！")

# ============================================================
# GUI
# ============================================================

COLOR = {
    "bg":     "#f0f2f5",
    "header": "#1a1a2e",
    "blue":   "#0f3460",
    "green":  "#16213e",
    "accent": "#e94560",
    "btn_b":  "#0f3460",
    "btn_g":  "#1a7a4a",
    "btn_r":  "#c0392b",
    "btn_gr": "#555",
    "white":  "#ffffff",
    "text":   "#222222",
    "sub":    "#666666",
}

FONT_TITLE = ("Meiryo UI", 13, "bold")
FONT_LABEL = ("Meiryo UI", 9)
FONT_ENTRY = ("Meiryo UI", 10)
FONT_BTN   = ("Meiryo UI", 9, "bold")
FONT_MONO  = ("Consolas", 9)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("パスワード自動入力ツール")
        self.resizable(False, False)
        self.configure(bg=COLOR["bg"])
        self.geometry("540x600")

        self._entries = load_entries()
        self._sel_idx = None

        self._build()
        self._refresh_list()

    # ----------------------------------------------------------
    # UI構築
    # ----------------------------------------------------------
    def _build(self):
        # ヘッダー
        hdr = tk.Frame(self, bg=COLOR["header"], pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🔐  パスワード自動入力ツール",
                 font=FONT_TITLE, bg=COLOR["header"], fg=COLOR["white"]).pack()
        tk.Label(hdr, text="完全オフライン動作  ／  インストール不要",
                 font=("Meiryo UI", 8), bg=COLOR["header"],
                 fg="#aaaaaa").pack()

        # 入力フォーム
        frm = tk.LabelFrame(self, text=" 新規登録 / 編集 ",
                            bg=COLOR["bg"], font=FONT_LABEL, padx=10, pady=8)
        frm.pack(fill="x", padx=12, pady=(10, 4))

        rows = [
            ("サイト名（任意）:",        "var_name", False),
            ("ホームページアドレス (URL):", "var_url",  False),
            ("ID / メールアドレス:",     "var_id",   False),
            ("パスワード:",             "var_pw",   True),
        ]
        self._widgets = {}
        for i, (lbl, attr, is_pw) in enumerate(rows):
            tk.Label(frm, text=lbl, bg=COLOR["bg"], anchor="w",
                     font=FONT_LABEL).grid(row=i, column=0, sticky="w", pady=3)
            var = tk.StringVar()
            setattr(self, attr, var)
            e = tk.Entry(frm, textvariable=var, width=36,
                         show="●" if is_pw else "",
                         font=FONT_ENTRY)
            e.grid(row=i, column=1, sticky="ew", padx=(6, 0), pady=3)
            self._widgets[attr] = e
            if is_pw:
                self._pw_entry = e
                sv = tk.BooleanVar()
                def _toggle(v=sv, w=e):
                    w.config(show="" if v.get() else "●")
                tk.Checkbutton(frm, text="表示", variable=sv, command=_toggle,
                               bg=COLOR["bg"], font=("Meiryo UI", 8)
                               ).grid(row=i, column=2, sticky="w", padx=4)

        # オプション行
        opt = tk.Frame(frm, bg=COLOR["bg"])
        opt.grid(row=len(rows), column=0, columnspan=3, sticky="w", pady=(6, 2))

        tk.Label(opt, text="待機時間:", bg=COLOR["bg"],
                 font=FONT_LABEL).pack(side="left")
        self.var_wait = tk.IntVar(value=5)
        tk.Spinbox(opt, from_=2, to=30, textvariable=self.var_wait,
                   width=4, font=FONT_LABEL).pack(side="left", padx=2)
        tk.Label(opt, text="秒　Tabキー回数:", bg=COLOR["bg"],
                 font=FONT_LABEL).pack(side="left", padx=(6, 0))
        self.var_tabs = tk.IntVar(value=1)
        tk.Spinbox(opt, from_=1, to=10, textvariable=self.var_tabs,
                   width=4, font=FONT_LABEL).pack(side="left", padx=2)
        tk.Label(opt, text="回", bg=COLOR["bg"],
                 font=FONT_LABEL).pack(side="left")
        self.var_enter = tk.BooleanVar(value=False)
        tk.Checkbutton(opt, text="最後にEnter", variable=self.var_enter,
                       bg=COLOR["bg"], font=FONT_LABEL).pack(side="left", padx=(10, 0))

        # 保存・クリアボタン
        bf = tk.Frame(frm, bg=COLOR["bg"])
        bf.grid(row=len(rows)+1, column=0, columnspan=3, pady=(8, 2))
        self._mk_btn(bf, "保  存", COLOR["btn_g"], self._save).pack(side="left", padx=5)
        self._mk_btn(bf, "クリア", COLOR["btn_gr"], self._clear).pack(side="left", padx=5)

        # サイト一覧
        lf = tk.LabelFrame(self, text=" 保存済みサイト一覧 ",
                            bg=COLOR["bg"], font=FONT_LABEL, padx=10, pady=6)
        lf.pack(fill="both", expand=True, padx=12, pady=4)

        cols = ("name", "url", "id")
        self.tree = ttk.Treeview(lf, columns=cols, show="headings",
                                  height=6, selectmode="browse")
        self.tree.heading("name", text="サイト名")
        self.tree.heading("url",  text="URL")
        self.tree.heading("id",   text="ID")
        self.tree.column("name", width=110)
        self.tree.column("url",  width=200)
        self.tree.column("id",   width=140)
        self.tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(lf, command=self.tree.yview)
        sb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # 操作ボタン
        abf = tk.Frame(self, bg=COLOR["bg"])
        abf.pack(fill="x", padx=12, pady=(0, 6))
        self._mk_btn(abf, "自動入力して開く", COLOR["btn_b"],
                     self._autofill).pack(side="left", padx=4)
        self._mk_btn(abf, "IDをコピー", "#7f8c8d",
                     lambda: self._copy(self.var_id)).pack(side="left", padx=4)
        self._mk_btn(abf, "PWをコピー", "#7f8c8d",
                     lambda: self._copy(self.var_pw)).pack(side="left", padx=4)
        self._mk_btn(abf, "削除", COLOR["btn_r"],
                     self._delete).pack(side="right", padx=4)

        # カウントダウン表示
        self.var_cd = tk.StringVar(value="")
        self._cd_lbl = tk.Label(self, textvariable=self.var_cd,
                                font=("Meiryo UI", 22, "bold"),
                                bg=COLOR["bg"], fg=COLOR["accent"])
        self._cd_lbl.pack()

        # ステータスバー
        self.var_status = tk.StringVar(value="準備完了")
        tk.Label(self, textvariable=self.var_status, bg="#dce1e7",
                 anchor="w", font=("Meiryo UI", 8),
                 relief="sunken", padx=8).pack(fill="x", side="bottom")

    def _mk_btn(self, parent, text, color, cmd):
        return tk.Button(parent, text=text, command=cmd,
                         bg=color, fg=COLOR["white"],
                         font=FONT_BTN, relief="flat",
                         padx=10, pady=5, cursor="hand2",
                         activebackground=color,
                         activeforeground=COLOR["white"])

    # ----------------------------------------------------------
    # リスト操作
    # ----------------------------------------------------------
    def _refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        for e in self._entries:
            self.tree.insert("", "end", values=(
                e.get("name", ""), e.get("url", ""), e.get("id", "")
            ))

    def _on_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        self._sel_idx = idx
        e = self._entries[idx]
        self.var_name.set(e.get("name", ""))
        self.var_url.set(e.get("url", ""))
        self.var_id.set(e.get("id", ""))
        self.var_pw.set(_dec(e.get("password", "")))
        self.var_wait.set(e.get("wait", 5))
        self.var_tabs.set(e.get("tabs", 1))
        self.var_enter.set(e.get("enter", False))

    def _clear(self):
        for v in (self.var_name, self.var_url, self.var_id, self.var_pw):
            v.set("")
        self._sel_idx = None
        self.var_status.set("クリアしました。")

    # ----------------------------------------------------------
    # 保存
    # ----------------------------------------------------------
    def _save(self):
        url = self.var_url.get().strip()
        uid = self.var_id.get().strip()
        pw  = self.var_pw.get()

        if not url:
            messagebox.showwarning("入力エラー", "URLを入力してください。")
            return
        if not uid:
            messagebox.showwarning("入力エラー", "IDを入力してください。")
            return
        if not pw:
            messagebox.showwarning("入力エラー", "パスワードを入力してください。")
            return

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        record = {
            "name":     self.var_name.get().strip() or url,
            "url":      url,
            "id":       uid,
            "password": _enc(pw),
            "wait":     self.var_wait.get(),
            "tabs":     self.var_tabs.get(),
            "enter":    self.var_enter.get(),
        }

        if self._sel_idx is not None and 0 <= self._sel_idx < len(self._entries):
            self._entries[self._sel_idx] = record
        else:
            self._entries.append(record)

        save_entries(self._entries)
        self._refresh_list()
        self._clear()
        self.var_status.set("保存しました。")

    # ----------------------------------------------------------
    # 削除
    # ----------------------------------------------------------
    def _delete(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("未選択", "削除するサイトを一覧から選んでください。")
            return
        idx = self.tree.index(sel[0])
        name = self._entries[idx].get("name", self._entries[idx].get("url", ""))
        if not messagebox.askyesno("削除確認", f"「{name}」を削除しますか？"):
            return
        self._entries.pop(idx)
        save_entries(self._entries)
        self._refresh_list()
        self._clear()
        self.var_status.set("削除しました。")

    # ----------------------------------------------------------
    # クリップボードコピー（tkinter組み込み機能）
    # ----------------------------------------------------------
    def _copy(self, var: tk.StringVar):
        val = var.get()
        if not val:
            return
        self.clipboard_clear()
        self.clipboard_append(val)
        self.var_status.set("クリップボードにコピーしました。")

    # ----------------------------------------------------------
    # 自動入力
    # ----------------------------------------------------------
    def _autofill(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("未選択", "自動入力するサイトを一覧から選んでください。")
            return
        idx   = self.tree.index(sel[0])
        rec   = self._entries[idx]
        url   = rec["url"]
        uid   = rec["id"]
        pw    = _dec(rec["password"])
        wait  = rec.get("wait", 5)
        tabs  = rec.get("tabs", 1)
        enter = rec.get("enter", False)

        def _status(msg):
            self.after(0, lambda: self.var_status.set(msg))

        def _countdown(n):
            if n > 0:
                self.after(0, lambda v=n: self.var_cd.set(
                    f"IDフィールドをクリックしてください…  {v} 秒"))
            else:
                self.after(0, lambda: self.var_cd.set(""))

        def _run():
            do_autofill(url, uid, pw, wait, tabs, enter, _status, _countdown)

        threading.Thread(target=_run, daemon=True).start()
        self.var_status.set(
            f"ブラウザを開きます。{wait}秒以内にIDフィールドをクリックしてください。")


# ============================================================
# 起動
# ============================================================

if __name__ == "__main__":
    if sys.platform != "win32":
        print("このツールはWindowsでのみ動作します。")
        sys.exit(1)
    app = App()
    app.mainloop()
