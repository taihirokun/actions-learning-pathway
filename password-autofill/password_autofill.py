"""
パスワード自動入力ツール
Windows向け・インストール不要（Pythonがあればそのまま動作）
PyInstallerでexe化すれば完全スタンドアロン
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import base64
import threading
import time
from pathlib import Path

# --- データ保存先 ---
DATA_FILE = Path(os.path.dirname(os.path.abspath(__file__))) / "autofill_data.json"

# --- 簡易エンコード/デコード（難読化） ---
def encode_password(pw: str) -> str:
    return base64.b64encode(pw.encode("utf-8")).decode("ascii")

def decode_password(encoded: str) -> str:
    return base64.b64decode(encoded.encode("ascii")).decode("utf-8")

# --- データ読み書き ---
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

# --- Selenium自動入力 ---
def autofill_selenium(url, user_id, password, status_var):
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        # webdriver-manager があれば自動でドライバ取得
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
        except ImportError:
            # なければパスにchromedriver.exeがある前提
            service = Service()

        options = Options()
        options.add_argument("--start-maximized")

        status_var.set("ブラウザを起動中...")
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url)

        # 最大15秒待ってフォームを探す
        wait = WebDriverWait(driver, 15)
        filled = False

        # よく使われるID/usernameフィールドのセレクタ候補
        id_selectors = [
            (By.NAME, "email"),
            (By.NAME, "username"),
            (By.NAME, "user"),
            (By.NAME, "login"),
            (By.NAME, "userid"),
            (By.NAME, "user_id"),
            (By.NAME, "id"),
            (By.NAME, "account"),
            (By.ID, "email"),
            (By.ID, "username"),
            (By.ID, "user"),
            (By.ID, "login"),
            (By.ID, "userid"),
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.CSS_SELECTOR, "input[type='text'][name*='user']"),
            (By.CSS_SELECTOR, "input[type='text'][name*='mail']"),
            (By.CSS_SELECTOR, "input[type='text'][name*='login']"),
            (By.CSS_SELECTOR, "input[type='text']"),  # 最後の手段
        ]

        id_field = None
        for by, selector in id_selectors:
            try:
                id_field = wait.until(EC.element_to_be_clickable((by, selector)))
                if id_field.is_displayed():
                    break
            except Exception:
                id_field = None

        if id_field:
            id_field.clear()
            id_field.send_keys(user_id)

            # パスワードフィールドを探す
            pw_field = None
            try:
                pw_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            except Exception:
                pass

            if pw_field and pw_field.is_displayed():
                pw_field.clear()
                pw_field.send_keys(password)
                filled = True
                status_var.set("入力完了！必要に応じてログインボタンを押してください。")
            else:
                status_var.set("パスワード欄が見つかりません。IDのみ入力しました。")
        else:
            status_var.set("入力欄が見つかりませんでした。手動で入力してください。")

    except ImportError:
        # seleniumがない場合はフォールバック
        autofill_fallback(url, user_id, password, status_var)
    except Exception as e:
        status_var.set(f"エラー: {e}")

def autofill_fallback(url, user_id, password, status_var):
    """seleniumがない場合: ブラウザを開いてクリップボードにコピー"""
    import webbrowser
    webbrowser.open(url)
    try:
        import pyperclip
        pyperclip.copy(user_id)
        status_var.set(f"ブラウザを開きました。クリップボードにIDをコピーしました。")
    except ImportError:
        status_var.set("ブラウザを開きました（seleniumが未インストール。手動で入力してください）")


# ====== GUI ======

class PasswordAutofillApp:
    def __init__(self, root):
        self.root = root
        self.root.title("パスワード自動入力ツール")
        self.root.resizable(False, False)
        self.entries = load_entries()
        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        root = self.root
        BG = "#f5f5f5"
        HEADER_BG = "#2c3e50"
        BTN_BLUE = "#2980b9"
        BTN_GREEN = "#27ae60"
        BTN_RED = "#e74c3c"
        root.configure(bg=BG)

        # ---- ヘッダー ----
        header = tk.Frame(root, bg=HEADER_BG, pady=10)
        header.pack(fill="x")
        tk.Label(header, text="パスワード自動入力ツール", font=("Meiryo UI", 14, "bold"),
                 bg=HEADER_BG, fg="white").pack()

        # ---- 入力フォーム ----
        form = tk.LabelFrame(root, text=" 新規登録 / 編集 ", bg=BG,
                             font=("Meiryo UI", 10, "bold"), padx=10, pady=8)
        form.pack(fill="x", padx=12, pady=(10, 4))

        labels = ["サイト名（任意）:", "ホームページアドレス (URL):", "ID / メールアドレス:", "パスワード:"]
        self.entries_vars = []
        for i, lbl in enumerate(labels):
            tk.Label(form, text=lbl, bg=BG, anchor="w",
                     font=("Meiryo UI", 9)).grid(row=i, column=0, sticky="w", pady=2)
            var = tk.StringVar()
            show = "*" if lbl.startswith("パスワード") else ""
            e = tk.Entry(form, textvariable=var, width=38, show=show,
                         font=("Meiryo UI", 9))
            e.grid(row=i, column=1, sticky="ew", padx=(6, 0), pady=2)
            self.entries_vars.append(var)
        self.var_name, self.var_url, self.var_id, self.var_pw = self.entries_vars

        # パスワード表示トグル
        self.show_pw = tk.BooleanVar()
        def toggle_pw():
            for widget in form.grid_slaves():
                if isinstance(widget, tk.Entry) and widget.grid_info()["row"] == 3:
                    widget.config(show="" if self.show_pw.get() else "*")
        tk.Checkbutton(form, text="表示", variable=self.show_pw, command=toggle_pw,
                       bg=BG, font=("Meiryo UI", 8)).grid(row=3, column=2, sticky="w")

        # ボタン行
        btn_frame = tk.Frame(form, bg=BG)
        btn_frame.grid(row=4, column=0, columnspan=3, pady=(8, 2))
        self._btn(btn_frame, "保存", BTN_GREEN, self._save_entry).pack(side="left", padx=4)
        self._btn(btn_frame, "クリア", "#7f8c8d", self._clear_form).pack(side="left", padx=4)

        # ---- 保存済みリスト ----
        list_frame = tk.LabelFrame(root, text=" 保存済みサイト一覧 ", bg=BG,
                                   font=("Meiryo UI", 10, "bold"), padx=10, pady=6)
        list_frame.pack(fill="both", expand=True, padx=12, pady=4)

        cols = ("name", "url", "id")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=7,
                                 selectmode="browse")
        self.tree.heading("name", text="サイト名")
        self.tree.heading("url", text="URL")
        self.tree.heading("id", text="ID")
        self.tree.column("name", width=110)
        self.tree.column("url", width=200)
        self.tree.column("id", width=140)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(list_frame, command=self.tree.yview)
        scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # リストボタン
        lb_frame = tk.Frame(root, bg=BG)
        lb_frame.pack(fill="x", padx=12, pady=(0, 6))
        self._btn(lb_frame, "自動入力して開く", BTN_BLUE, self._autofill).pack(side="left", padx=4)
        self._btn(lb_frame, "選択を削除", BTN_RED, self._delete_entry).pack(side="left", padx=4)

        # ---- ステータスバー ----
        self.status_var = tk.StringVar(value="準備完了")
        tk.Label(root, textvariable=self.status_var, bg="#ecf0f1", anchor="w",
                 font=("Meiryo UI", 8), relief="sunken", padx=6).pack(
                 fill="x", side="bottom")

    def _btn(self, parent, text, color, cmd):
        return tk.Button(parent, text=text, command=cmd, bg=color, fg="white",
                         font=("Meiryo UI", 9, "bold"), relief="flat",
                         padx=10, pady=4, cursor="hand2",
                         activebackground=color, activeforeground="white")

    def _refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        for entry in self.entries:
            self.tree.insert("", "end", values=(
                entry.get("name", ""),
                entry.get("url", ""),
                entry.get("id", ""),
            ))

    def _clear_form(self):
        for v in self.entries_vars:
            v.set("")
        self._selected_index = None

    def _on_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        self._selected_index = idx
        entry = self.entries[idx]
        self.var_name.set(entry.get("name", ""))
        self.var_url.set(entry.get("url", ""))
        self.var_id.set(entry.get("id", ""))
        self.var_pw.set(decode_password(entry.get("password", "")))

    def _save_entry(self):
        url = self.var_url.get().strip()
        user_id = self.var_id.get().strip()
        pw = self.var_pw.get()
        if not url:
            messagebox.showwarning("入力エラー", "ホームページアドレスを入力してください。")
            return
        if not user_id:
            messagebox.showwarning("入力エラー", "IDを入力してください。")
            return
        if not pw:
            messagebox.showwarning("入力エラー", "パスワードを入力してください。")
            return

        # URLにスキームがなければ付加
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        new_entry = {
            "name": self.var_name.get().strip() or url,
            "url": url,
            "id": user_id,
            "password": encode_password(pw),
        }

        idx = getattr(self, "_selected_index", None)
        if idx is not None and 0 <= idx < len(self.entries):
            self.entries[idx] = new_entry
        else:
            self.entries.append(new_entry)

        save_entries(self.entries)
        self._refresh_list()
        self._clear_form()
        self.status_var.set("保存しました。")

    def _delete_entry(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("選択なし", "削除するサイトをリストから選んでください。")
            return
        idx = self.tree.index(sel[0])
        name = self.entries[idx].get("name", self.entries[idx].get("url", ""))
        if not messagebox.askyesno("確認", f"「{name}」を削除しますか？"):
            return
        self.entries.pop(idx)
        save_entries(self.entries)
        self._refresh_list()
        self._clear_form()
        self.status_var.set("削除しました。")

    def _autofill(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("選択なし", "自動入力するサイトをリストから選んでください。")
            return
        idx = self.tree.index(sel[0])
        entry = self.entries[idx]
        url = entry["url"]
        user_id = entry["id"]
        pw = decode_password(entry["password"])

        self.status_var.set("ブラウザを起動しています...")
        t = threading.Thread(
            target=autofill_selenium,
            args=(url, user_id, pw, self.status_var),
            daemon=True,
        )
        t.start()


def main():
    root = tk.Tk()
    root.geometry("520x560")
    app = PasswordAutofillApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
