"""AI笔记流水线 — GUI 控制面板"""
import os, sys, subprocess, threading, time
from datetime import datetime
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHON = sys.executable
LOG_PATH = os.path.join(PROJECT, 'logs', 'watcher.log')
INPUT_DIR = os.path.join(PROJECT, 'input')

class PipelineGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AI笔记流水线控制面板")
        self.root.geometry("700x500")
        self.process = None
        self._last_log_pos = 0

        top = ttk.Frame(self.root)
        top.pack(fill='x', padx=10, pady=5)
        self.status_var = tk.StringVar(value="● 停止")
        ttk.Label(top, textvariable=self.status_var, font=('', 10, 'bold')).pack(side='left')
        ttk.Label(top, text="| 拖文件到 input/ 自动处理").pack(side='left', padx=10)

        self.log_area = scrolledtext.ScrolledText(self.root, height=20, font=('Consolas', 9), bg='#1e1e1e', fg='#d4d4d4', insertbackground='white')
        self.log_area.pack(fill='both', expand=True, padx=10, pady=5)
        self.log_area.config(state='disabled')

        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill='x', padx=10, pady=5)
        self.btn_start = ttk.Button(btn_frame, text="▶ 启动监听", command=self.start_watcher)
        self.btn_start.pack(side='left', padx=2)
        self.btn_stop = ttk.Button(btn_frame, text="⏹ 停止监听", command=self.stop_watcher, state='disabled')
        self.btn_stop.pack(side='left', padx=2)
        ttk.Button(btn_frame, text="📂 选择文件处理", command=self.process_file).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="📁 打开 input", command=self.open_input).pack(side='left', padx=2)

        # 首次加载全部历史日志
        self._load_all_logs()
        self._auto_refresh()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()

    def _log_gui(self, msg):
        self.log_area.config(state='normal')
        self.log_area.insert('end', f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
        self.log_area.see('end')
        self.log_area.config(state='disabled')

    def _load_all_logs(self):
        self.log_area.config(state='normal')
        self.log_area.delete('1.0', 'end')
        try:
            if os.path.exists(LOG_PATH):
                with open(LOG_PATH, 'r', encoding='utf-8', errors='replace') as f:
                    self.log_area.insert('end', f.read())
                self._last_log_pos = os.path.getsize(LOG_PATH)
                self.log_area.see('end')
        except: pass
        self.log_area.config(state='disabled')

    def _append_new_logs(self):
        self.log_area.config(state='normal')
        try:
            if os.path.exists(LOG_PATH):
                sz = os.path.getsize(LOG_PATH)
                if sz > self._last_log_pos:
                    with open(LOG_PATH, 'r', encoding='utf-8', errors='replace') as f:
                        f.seek(self._last_log_pos)
                        self.log_area.insert('end', f.read())
                    self._last_log_pos = sz
                    self.log_area.see('end')
        except: pass
        self.log_area.config(state='disabled')

    def _auto_refresh(self):
        if self.process and self.process.poll() is None:
            self.status_var.set("● 运行中")
            self.btn_start.config(state='disabled')
            self.btn_stop.config(state='normal')
        else:
            self.status_var.set("● 停止")
            self.btn_start.config(state='normal')
            self.btn_stop.config(state='disabled')
        self._append_new_logs()
        self.root.after(3000, self._auto_refresh)

    def start_watcher(self):
        self.process = subprocess.Popen([PYTHON, '-c',
            'import sys; sys.path.insert(0,"src"); from watcher import start_watcher; start_watcher("input")'],
            cwd=PROJECT, stdout=open(LOG_PATH, 'a', encoding='utf-8'), stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW, env={**os.environ,"PYTHONIOENCODING":"utf-8"})
        self._log_gui("▶ 监听已启动")

    def stop_watcher(self):
        if self.process:
            self.process.terminate()
            self.process = None
            self._log_gui("⏹ 监听已停止")

    def process_file(self):
        path = filedialog.askopenfilename(initialdir=INPUT_DIR, title="选择文件处理")
        if not path: return
        self._log_gui(f"📂 处理: {os.path.basename(path)}")
        t = threading.Thread(target=self._run_process, args=(path,), daemon=True)
        t.start()

    def _run_process(self, path):
        try:
            r = subprocess.run([PYTHON, '-c', f'import sys; sys.path.insert(0,"src"); from main import process_file; process_file(r"{path}")'],
                               cwd=PROJECT, capture_output=True, text=True, timeout=180)
            self.root.after(0, lambda: self._log_gui(r.stdout + r.stderr))
        except Exception as e:
            self.root.after(0, lambda: self._log_gui(f"❌ {e}"))

    def open_input(self):
        os.startfile(INPUT_DIR)

    def on_close(self):
        self.stop_watcher()
        self.root.destroy()

if __name__ == '__main__':
    PipelineGUI()