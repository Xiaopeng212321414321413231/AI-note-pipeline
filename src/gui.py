# -*- coding: utf-8 -*-
"""
一键点击启动流水线 GUI — 支持断点续传、实时进度显示
"""

import os
import sys
import threading
import time
import logging
from tkinter import *
from tkinter import ttk, scrolledtext, messagebox, filedialog
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.checkpoint import (
    load, get_interrupted, get_errors, get_pending,
    summary, clear_all, STAGES, STAGE_NAMES,
)
from src.main import run_pipeline, process_input_dir, resume_interrupted, process_file
from src import rss_importer

# -*- supported formats -*-
SUPPORTED_FORMATS = {
    '\u56fe\u7247': ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp'],
    'PDF':  ['.pdf'],
    '\u97f3\u9891': ['.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg', '.amr'],
    '\u89c6\u9891': ['.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm', '.ts', '.m4v', '.mpg', '.mpeg'],
    '\u6587\u6863': ['.docx'],
    '\u6587\u672c': ['.md', '.txt'],
}
ALL_EXTS = [ext for exts in SUPPORTED_FORMATS.values() for ext in exts]

def is_supported(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    return ext in ALL_EXTS

class PipelineGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AI 笔记流水线 v2.0")
        self.root.geometry("700x750")
        self.root.resizable(True, True)

        # 设置样式
        self.root.configure(bg="#f0f0f0")
        style = ttk.Style()
        style.theme_use("clam")

        # 运行状态
        self.running = False
        self.stop_flag = False
        self.selected_file = None
        self.selected_files = []

        self._build_ui()
        self._refresh_status()

    def _build_ui(self):
        # ========== 顶部标题 ==========
        title_frame = Frame(self.root, bg="#2b3e4f", height=60)
        title_frame.pack(fill=X)
        Label(title_frame, text="🤖 AI 多模态笔记处理流水线",
              fg="white", bg="#2b3e4f",
              font=("Microsoft YaHei", 16, "bold")).pack(pady=12)

        # ========== 主操作区 ==========
        main_frame = Frame(self.root, bg="#f0f0f0", padx=15, pady=10)
        main_frame.pack(fill=X)

        # ── 📎 文件选择处理（内嵌浏览器） ──
        Label(main_frame, text='📎 文件选择处理', bg='#f0f0f0',
              font=('Microsoft YaHei', 11, 'bold'),
              fg='#2b3e4f', anchor='w').pack(fill=X, pady=(0, 3))

        file_btn_frame = Frame(main_frame, bg='#f0f0f0')
        file_btn_frame.pack(fill=X, pady=(0, 5))

        self.toggle_btn = Button(
            file_btn_frame,
            text='📂 打开文件浏览器',
            command=self._toggle_browser,
            bg='#3498db', fg='white',
            font=('Microsoft YaHei', 11, 'bold'),
            padx=20, pady=8,
            cursor='hand2',
            relief=FLAT,
            activebackground='#2980b9',
            activeforeground='white',
        )
        self.toggle_btn.pack(side=LEFT)

        self.process_file_btn = Button(
            file_btn_frame,
            text='▶ 处理选中文件',
            command=self._process_selected_file,
            bg='#27ae60', fg='white',
            font=('Microsoft YaHei', 11, 'bold'),
            padx=20, pady=8,
            cursor='hand2',
            relief=FLAT,
            state=DISABLED,
            activebackground='#2ecc71',
            activeforeground='white',
        )
        self.process_file_btn.pack(side=LEFT, padx=(10, 0))

        self.rewrite_var = BooleanVar(value=True)
        self.rewrite_check = Checkbutton(
            file_btn_frame,
            text='🔁 AI 重写',
            variable=self.rewrite_var,
            bg='#f0f0f0',
            fg='#2b3e4f',
            font=('Microsoft YaHei', 9, 'bold'),
            selectcolor='#eaf6ea',
            activebackground='#f0f0f0',
            activeforeground='#27ae60',
            cursor='hand2',
        )
        self.rewrite_check.pack(side=LEFT, padx=(12, 0))

        # ── 内嵌文件浏览器面板（初始隐藏） ──
        self.browser_frame = Frame(main_frame, bg='#ffffff', padx=8, pady=6,
                                   highlightbackground='#3498db', highlightthickness=1)
        self.browser_frame.pack(fill=X, pady=(5, 5))
        self.browser_frame.pack_forget()

        # 路径栏
        path_bar = Frame(self.browser_frame, bg='#ffffff')
        path_bar.pack(fill=X, pady=(0, 4))
        Label(path_bar, text='📁 路径:', bg='#ffffff',
              font=('Microsoft YaHei', 9)).pack(side=LEFT)
        self.path_entry = Entry(path_bar, font=('Microsoft YaHei', 9))
        self.path_entry.pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        self.go_btn = Button(path_bar, text='前往', command=self._goto_path,
                             bg='#3498db', fg='white', font=('Microsoft YaHei', 9),
                             padx=8, pady=2, relief=FLAT, cursor='hand2')
        self.go_btn.pack(side=LEFT, padx=(0, 3))
        self.up_btn = Button(path_bar, text='⬆ 上级', command=self._go_up,
                             bg='#95a5a6', fg='white', font=('Microsoft YaHei', 9),
                             padx=8, pady=2, relief=FLAT, cursor='hand2')
        self.up_btn.pack(side=LEFT)

        # 文件树
        tree_frame = Frame(self.browser_frame, bg='#ffffff')
        tree_frame.pack(fill=X, pady=(0, 4))
        self.file_tree = ttk.Treeview(
            tree_frame, columns=('size', 'mtime'),
            show='tree headings', height=10, selectmode='extended',
        )
        self.file_tree.heading('#0', text='名称')
        self.file_tree.heading('size', text='大小')
        self.file_tree.heading('mtime', text='修改时间')
        self.file_tree.column('#0', width=280, anchor='w')
        self.file_tree.column('size', width=80, anchor='e')
        self.file_tree.column('mtime', width=140, anchor='w')
        self.file_tree.pack(fill=X)
        self.file_tree.bind('<Double-1>', self._on_tree_double_click)

        # 操作按钮
        act_bar = Frame(self.browser_frame, bg='#ffffff')
        act_bar.pack(fill=X)
        self.add_files_btn = Button(
            act_bar, text='➕ 添加选中文件', command=self._add_selected_files,
            bg='#27ae60', fg='white', font=('Microsoft YaHei', 9, 'bold'),
            padx=12, pady=4, relief=FLAT, cursor='hand2',
        )
        self.add_files_btn.pack(side=LEFT)
        self.clear_sel_btn = Button(
            act_bar, text='🗑 清空已选', command=self._clear_selected,
            bg='#e74c3c', fg='white', font=('Microsoft YaHei', 9),
            padx=12, pady=4, relief=FLAT, cursor='hand2',
        )
        self.clear_sel_btn.pack(side=LEFT, padx=(5, 0))

        # ── 已选文件列表 ──
        self.sel_frame = Frame(main_frame, bg='#ffffff', padx=10, pady=6,
                               highlightbackground='#27ae60', highlightthickness=1)
        self.sel_frame.pack(fill=X, pady=(5, 2))
        self.sel_frame.pack_forget()

        self.sel_label = Label(self.sel_frame, text='📋 已选文件 (0)',
                               bg='#ffffff', fg='#2b3e4f',
                               font=('Microsoft YaHei', 10, 'bold'), anchor='w')
        self.sel_label.pack(fill=X, pady=(0, 3))

        self.sel_listbox = Listbox(self.sel_frame, height=4, font=('Consolas', 9),
                                   bg='#fafafa', fg='#333', selectmode='single',
                                   exportselection=False)
        self.sel_listbox.pack(fill=X)
        self.sel_listbox.bind('<Double-1>', self._remove_selected_item)

        # 状态卡片
        self.file_info_frame = Frame(main_frame, bg='#ffffff', padx=10, pady=6,
                                      highlightbackground='#ddd', highlightthickness=1)
        self.file_info_frame.pack(fill=X, pady=(5, 2))

        self.file_status_icon = Label(self.file_info_frame, text='💤', bg='#ffffff',
                                       font=('Segoe UI Emoji', 14))
        self.file_status_icon.pack(side=LEFT, padx=(0, 8))

        self.file_info_label = Label(self.file_info_frame,
                                      text='尚未选择文件',
                                      bg='#ffffff', fg='#888',
                                      font=('Microsoft YaHei', 9),
                                      anchor='w', justify=LEFT)
        self.file_info_label.pack(side=LEFT, fill=X, expand=True)

        # 支持的格式说明
        fmt_parts = []
        for k, v in SUPPORTED_FORMATS.items():
            fmt_parts.append(f'{k}({chr(44).join(v)})')
        fmt_text = '支持: ' + ' | '.join(fmt_parts)
        Label(main_frame, text=fmt_text, bg='#f0f0f0',
              fg='#aaa', font=('Microsoft YaHei', 7), anchor='w').pack(fill=X, pady=(1, 8))

        ttk.Separator(main_frame, orient=HORIZONTAL).pack(fill=X, pady=(0, 8))

        # --- 📁 批量处理（input/ 目录） ---
        Label(main_frame, text="📁 批量处理（input/ 目录）", bg="#f0f0f0",
              font=("Microsoft YaHei", 11, "bold"),
              fg="#2b3e4f", anchor="w").pack(fill=X, pady=(0, 3))
        btn_frame = Frame(main_frame, bg="#f0f0f0")
        btn_frame.pack(fill=X, pady=(0, 10))

        self.start_btn = Button(
            btn_frame,
            text="▶  批量处理",
            command=self._start_pipeline,
            bg="#27ae60", fg="white",
            font=("Microsoft YaHei", 14, "bold"),
            padx=30, pady=12,
            cursor="hand2",
            relief=FLAT,
            activebackground="#2ecc71",
            activeforeground="white",
        )
        self.start_btn.pack(side=LEFT, padx=(0, 10))

        self.clear_btn = Button(
            btn_frame,
            text="🔄 重新开始",
            command=self._confirm_clear,
            bg="#e74c3c", fg="white",
            font=("Microsoft YaHei", 10),
            padx=12, pady=8,
            cursor="hand2",
            relief=FLAT,
            activebackground="#c0392b",
            activeforeground="white",
        )
        self.clear_btn.pack(side=LEFT, padx=(0, 10))

        self.status_btn = Button(
            btn_frame,
            text="📋 刷新状态",
            command=self._refresh_status,
            bg="#3498db", fg="white",
            font=("Microsoft YaHei", 10),
            padx=12, pady=8,
            cursor="hand2",
            relief=FLAT,
            activebackground="#2980b9",
            activeforeground="white",
        )
        self.status_btn.pack(side=LEFT)

        self.retry_btn = Button(
            btn_frame,
            text="🔁 重试失败文件",
            command=self._retry_errors,
            bg="#e67e22", fg="white",
            font=("Microsoft YaHei", 10),
            padx=12, pady=8,
            cursor="hand2",
            relief=FLAT,
            activebackground="#d35400",
            activeforeground="white",
        )
        self.retry_btn.pack(side=LEFT, padx=(10, 0))

        # ========== 🌐 联网处理 ==========
        ttk.Separator(main_frame, orient=HORIZONTAL).pack(fill=X, pady=(5, 8))
        Label(main_frame, text="🌐 联网处理", bg="#f0f0f0",
              font=("Microsoft YaHei", 11, "bold"),
              fg="#2b3e4f", anchor="w").pack(fill=X, pady=(0, 3))
        web_frame = Frame(main_frame, bg="#f0f0f0")
        web_frame.pack(fill=X, pady=(5, 10))

        Label(web_frame, text="知乎专栏ID:", bg="#f0f0f0",
              font=("Microsoft YaHei", 9)).pack(side=LEFT, padx=(0, 5))
        self.zhihu_entry = Entry(web_frame, width=20,
                                 font=("Microsoft YaHei", 9))
        self.zhihu_entry.pack(side=LEFT, padx=(0, 10))
        self.zhihu_entry.insert(0, "kazike")

        self.scan_btn = Button(
            web_frame,
            text="📡  扫描今天新文章",
            command=self._scan_today,
            bg="#8e44ad", fg="white",
            font=("Microsoft YaHei", 10, "bold"),
            padx=12, pady=8,
            cursor="hand2",
            relief=FLAT,
            activebackground="#9b59b6",
            activeforeground="white",
        )
        self.scan_btn.pack(side=LEFT, padx=(0, 5))

        self.download_btn = Button(
            web_frame,
            text="⬇  下载全部队列",
            command=self._download_all,
            bg="#1abc9c", fg="white",
            font=("Microsoft YaHei", 10, "bold"),
            padx=12, pady=8,
            cursor="hand2",
            relief=FLAT,
            activebackground="#16a085",
            activeforeground="white",
        )
        self.download_btn.pack(side=LEFT)


        # ========== 恢复提示区 ==========
        # ========== 恢复提示区 ==========
        self.resume_frame = Frame(main_frame, bg="#fff3cd", padx=10, pady=8,
                                  highlightbackground="#ffc107", highlightthickness=1)
        self.resume_frame.pack(fill=X, pady=(0, 10))
        self.resume_frame.pack_forget()  # 初始隐藏

        self.resume_label = Label(self.resume_frame, text="",
                                  bg="#fff3cd", fg="#856404",
                                  font=("Microsoft YaHei", 10),
                                  justify=LEFT, wraplength=600)
        self.resume_label.pack(fill=X)

        resume_btn_frame = Frame(self.resume_frame, bg="#fff3cd")
        resume_btn_frame.pack(anchor="w", pady=(5, 0))

        self.resume_btn = Button(
            resume_btn_frame, text="▶ 继续处理这些文件",
            command=self._resume_interrupted,
            bg="#ffc107", fg="#333",
            font=("Microsoft YaHei", 9, "bold"),
            padx=10, pady=3,
            cursor="hand2",
            relief=FLAT,
        )
        self.resume_btn.pack(side=LEFT, padx=(0, 5))

        self.skip_resume_btn = Button(
            resume_btn_frame, text="✕ 忽略，处理新文件",
            command=self._hide_resume,
            bg="#e0e0e0", fg="#666",
            font=("Microsoft YaHei", 9),
            padx=10, pady=3,
            cursor="hand2",
            relief=FLAT,
        )
        self.skip_resume_btn.pack(side=LEFT)

        # ========== 状态摘要区 ==========
        status_frame = LabelFrame(main_frame, text="📊 处理状态", padx=10, pady=8,
                                  font=("Microsoft YaHei", 10, "bold"),
                                  bg="#f0f0f0")
        status_frame.pack(fill=X, pady=(0, 10))

        self.status_text = Text(status_frame, height=5, font=("Consolas", 9),
                                bg="#fafafa", fg="#333", relief=FLAT,
                                padx=5, pady=5)
        self.status_text.pack(fill=X)
        self.status_text.config(state=DISABLED)

        # ========== 实时日志区 ==========
        log_frame = LabelFrame(main_frame, text="📝 运行日志", padx=10, pady=8,
                               font=("Microsoft YaHei", 10, "bold"),
                               bg="#f0f0f0")
        log_frame.pack(fill=BOTH, expand=True)

        self.log_area = scrolledtext.ScrolledText(
            log_frame, height=12, font=("Consolas", 9),
            bg="#1e1e1e", fg="#d4d4d4",
            insertbackground="white",
            state=DISABLED, wrap=WORD,
        )
        self.log_area.pack(fill=BOTH, expand=True)

        # 底部状态栏
        self.bottom_bar = Label(self.root, text="就绪",
                                bg="#2b3e4f", fg="#ccc",
                                font=("Microsoft YaHei", 9),
                                anchor="w", padx=15)
        self.bottom_bar.pack(fill=X, side=BOTTOM)



    # ══════════════════════════════════════════
    # 📎 文件选择处理（内嵌浏览器）
    # ══════════════════════════════════════════

    def _toggle_browser(self):
        """展开/收起内嵌文件浏览器"""
        if self.browser_frame.winfo_ismapped():
            self.browser_frame.pack_forget()
            self.toggle_btn.config(text='📂 打开文件浏览器')
        else:
            self.browser_frame.pack(fill=X, pady=(5, 5))
            self.toggle_btn.config(text='🗂 收起文件浏览器')
            if not hasattr(self, 'current_dir'):
                self.current_dir = os.path.expanduser('~/Desktop')
                self.selected_files = []
                self._load_dir(self.current_dir)

    def _load_dir(self, path):
        """加载目录到文件树"""
        path = os.path.abspath(path)
        if not os.path.isdir(path):
            self._log(f'⚠️ 目录不存在: {path}')
            return
        self.current_dir = path
        self.path_entry.delete(0, END)
        self.path_entry.insert(0, path)
        self.file_tree.delete(*self.file_tree.get_children())
        try:
            items = sorted(os.listdir(path), key=str.lower)
        except PermissionError:
            self._log(f'⚠️ 无权限访问: {path}')
            return
        for name in items:
            if name.startswith('.') or name == 'desktop.ini':
                continue
            full = os.path.join(path, name)
            try:
                is_dir = os.path.isdir(full)
                size = '' if is_dir else self._fmt_size(os.path.getsize(full))
                mtime = time.strftime('%Y-%m-%d %H:%M',
                                      time.localtime(os.path.getmtime(full)))
            except OSError:
                continue
            icon = '📁' if is_dir else self._file_icon(full)
            self.file_tree.insert('', 'end', iid=full,
                                  text=f'{icon} {name}',
                                  values=(size, mtime), open=False)

    def _fmt_size(self, n):
        for unit in ('B', 'KB', 'MB', 'GB'):
            if n < 1024:
                return f'{n:.0f}{unit}' if unit == 'B' else f'{n:.1f}{unit}'
            n /= 1024
        return f'{n:.1f}TB'

    def _file_icon(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext in ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp'):
            return '🖼️'
        if ext == '.pdf':
            return '📕'
        if ext in ('.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg', '.amr'):
            return '🎵'
        if ext == '.docx':
            return '📄'
        if ext in ('.md', '.txt'):
            return '📝'
        return '📄'

    def _goto_path(self):
        p = self.path_entry.get().strip()
        if p:
            self._load_dir(p)

    def _go_up(self):
        parent = os.path.dirname(self.current_dir)
        if parent and parent != self.current_dir:
            self._load_dir(parent)

    def _on_tree_double_click(self, event):
        item = self.file_tree.focus()
        if not item:
            return
        if os.path.isdir(item):
            self._load_dir(item)
        else:
            self._add_paths([item])

    def _add_selected_files(self):
        sel = self.file_tree.selection()
        if not sel:
            messagebox.showinfo('提示', '请先在文件列表中选中文件')
            return
        files = [i for i in sel if os.path.isfile(i)]
        self._add_paths(files)

    def _add_paths(self, paths):
        added = 0
        for p in paths:
            if p in self.selected_files:
                continue
            self.selected_files.append(p)
            self.sel_listbox.insert(END, os.path.basename(p))
            added += 1
        if added:
            self._update_sel_status()
            self._log(f'➕ 已添加 {added} 个文件')

    def _clear_selected(self):
        self.selected_files = []
        self.sel_listbox.delete(0, END)
        self._update_sel_status()
        self._log('🗑 已清空选中文件')

    def _remove_selected_item(self, event):
        idx = self.sel_listbox.curselection()
        if idx:
            self.selected_files.pop(idx[0])
            self.sel_listbox.delete(idx[0])
            self._update_sel_status()

    def _update_sel_status(self):
        n = len(self.selected_files)
        self.sel_label.config(text=f'📋 已选文件 ({n})')
        if n > 0:
            self.sel_frame.pack(fill=X, pady=(5, 2))
            self.sel_frame.pack_propagate(False)
            unsupported = [p for p in self.selected_files if not is_supported(p)]
            if unsupported:
                exts = sorted({os.path.splitext(p)[1].lower() for p in unsupported})
                self.file_status_icon.config(text='⛔')
                self.file_info_label.config(
                    text=f'{n} 个文件，其中 {len(unsupported)} 个不兼容 ({",".join(exts)})',
                    fg='#e74c3c'
                )
                self.file_info_frame.config(highlightbackground='#e74c3c')
                self.process_file_btn.config(state=NORMAL)
            else:
                self.file_status_icon.config(text='✅')
                self.file_info_label.config(
                    text=f'{n} 个文件，全部兼容 ✓',
                    fg='#27ae60'
                )
                self.file_info_frame.config(highlightbackground='#27ae60')
                self.process_file_btn.config(state=NORMAL)
        else:
            self.sel_frame.pack_forget()
            self.file_status_icon.config(text='💤')
            self.file_info_label.config(text='尚未选择文件', fg='#888')
            self.file_info_frame.config(highlightbackground='#ddd')
            self.process_file_btn.config(state=DISABLED)

    def _process_selected_file(self):
        """处理所有已选文件"""
        if not self.selected_files:
            messagebox.showinfo('提示', '请先选择文件')
            return
        if self.running:
            messagebox.showinfo('提示', '流水线正在运行中')
            return

        self.running = True
        self.process_file_btn.config(text='⏹  处理中...', bg='#e67e22', state=DISABLED)
        self.toggle_btn.config(state=DISABLED)
        self.start_btn.config(state=DISABLED)
        self.bottom_bar.config(text='正在处理选中文件...')

        self._log('=' * 50)
        self._log(f'📎 开始处理 {len(self.selected_files)} 个选中文件')

        files = list(self.selected_files)

        def run():
            self._setup_log_redirect()
            done = 0
            skipped = 0
            for fp in files:
                self._log(f'➡ 处理: {os.path.basename(fp)}')
                if not is_supported(fp):
                    ext = os.path.splitext(fp)[1].lower()
                    self._log(f'⛔ 流水线不兼容，跳过: {ext} 格式')
                    skipped += 1
                    continue
                try:
                    process_file(fp, rewrite=self.rewrite_var.get())
                    done += 1
                except Exception as e:
                    self._log(f'❌ 处理失败: {e}')
            self._log(f'✅ 完成: {done} 个成功, {skipped} 个不兼容跳过')
            self._restore_log_redirect()
            self.root.after(0, self._on_file_done)

        threading.Thread(target=run, daemon=True).start()

    def _on_file_done(self):
        """选中文件处理完成后的 UI 更新"""
        self.running = False
        self.process_file_btn.config(text='▶ 处理选中文件', bg='#27ae60', state=NORMAL)
        self.toggle_btn.config(state=NORMAL)
        self.start_btn.config(state=NORMAL)
        self.bottom_bar.config(text='就绪')
        self._log('=' * 50)
        self._refresh_status()

    def _retry_errors(self):
        """将 error 文件夹的文件移回 input 并开始处理"""
        import shutil
        from pathlib import Path
        error_dir = os.path.join(INPUT_DIR, 'error')
        if not os.path.isdir(error_dir):
            messagebox.showinfo("提示", "没有 error 文件夹")
            return
        error_files = [f for f in os.listdir(error_dir) if os.path.isfile(os.path.join(error_dir, f)) and not f.startswith('.')]
        if not error_files:
            messagebox.showinfo("提示", "error 文件夹是空的")
            return
        count = len(error_files)
        moved = 0
        for f in error_files:
            src = os.path.join(error_dir, f)
            dst = os.path.join(INPUT_DIR, f)
            try:
                os.rename(src, dst)
                moved += 1
                self._log(f"↩️ 已移回: {f}")
            except Exception as e:
                self._log(f"⚠️ 移动失败 {f}: {e}")
        self._log(f"🔄 已移回 {moved}/{count} 个文件到 input，开始处理...")
        self._refresh_status()
        self._start_pipeline()

    def _refresh_status(self):
        """刷新状态摘要"""
        try:
            s = summary()
            self.status_text.config(state=NORMAL)
            self.status_text.delete("1.0", END)
            self.status_text.insert("1.0", s)
            self.status_text.config(state=DISABLED)

            # 检查是否有中断文件
            interrupted = get_interrupted()
            if interrupted:
                get_errors()
                text_lines = [f"⚠️ 发现 {len(interrupted)} 个中断的文件："]
                for fp, info in list(interrupted.items())[:5]:
                    stage = STAGE_NAMES.get(info.get("stage_num", 0), "?")
                    err = info.get("error", "")
                    line = f"  • {os.path.basename(fp)} (卡在: {stage})"
                    if err:
                        line += f" — {err[:40]}"
                    text_lines.append(line)
                if len(interrupted) > 5:
                    text_lines.append(f"  ...还有 {len(interrupted)-5} 个")

                self.resume_label.config(text="\n".join(text_lines))
                self.resume_frame.pack(fill=X, pady=(0, 10))
                self.resume_frame.pack_propagate(False)
            else:
                self._hide_resume()
        except Exception as e:
            self._log(f"⚠️ 刷新状态失败: {e}")

    def _hide_resume(self):
        self.resume_frame.pack_forget()

    def _confirm_clear(self):
        if messagebox.askyesno("确认", "清除所有 checkpoint 重新开始？\n（中断的进度会丢失）"):
            clear_all()
            self._log("🔄 已清除所有 checkpoint")
            self._refresh_status()

    def _start_pipeline(self):
        """启动流水线（新线程）"""
        if self.running:
            messagebox.showinfo("提示", "流水线正在运行中")
            return

        self.running = True
        self.stop_flag = False
        self.selected_file = None
        self.selected_files = []
        self.start_btn.config(text="⏹  处理中...", bg="#e67e22", state=NORMAL)
        self.clear_btn.config(state=DISABLED)
        self.resume_btn.config(state=DISABLED)
        self.skip_resume_btn.config(state=DISABLED)
        self.toggle_btn.config(state=DISABLED)
        self.process_file_btn.config(state=DISABLED)
        self.bottom_bar.config(text="正在运行...")

        self._log("=" * 50)
        self._log("🚀 流水线启动")

        # 后台线程
        threading.Thread(target=self._run_pipeline_thread, daemon=True).start()

    def _run_pipeline_thread(self):
        """后台运行流水线"""
        try:
            # 重定向日志到 GUI
            self._setup_log_redirect()

            # 先恢复中断
            self._log("📂 第一步：恢复中断的文件...")
            resumed = resume_interrupted()
            self._log(f"  恢复完成: {resumed} 个文件")

            if not self.stop_flag:
                # 处理新文件
                self._log("\n📂 第二步：处理新文件...")
                processed = process_input_dir()
                self._log(f"  处理完成: {processed} 个文件")
        except Exception as e:
            self._log(f"❌ 流水线异常: {e}")
        finally:
            self._restore_log_redirect()
            self.root.after(0, self._on_pipeline_done)

    def _on_pipeline_done(self):
        """流水线完成后的 UI 更新"""
        self.running = False
        self.start_btn.config(text="▶  批量处理", bg="#27ae60", state=NORMAL)
        self.clear_btn.config(state=NORMAL)
        self.resume_btn.config(state=NORMAL)
        self.skip_resume_btn.config(state=NORMAL)
        self.toggle_btn.config(state=NORMAL)
        self.process_file_btn.config(state=NORMAL)
        self.bottom_bar.config(text="就绪")
        self._refresh_status()
        self._log("\n✅ 流水线完成")
        self._log("=" * 50)

    def _resume_interrupted(self):
        """纯恢复中断文件"""
        if self.running:
            return
        self.running = True
        self.start_btn.config(text="⏹  恢复中...", bg="#e67e22", state=NORMAL)
        self.clear_btn.config(state=DISABLED)
        self.bottom_bar.config(text="正在恢复中断文件...")

        self._log("=" * 50)
        self._log("🔄 恢复中断文件")

        def run():
            self._setup_log_redirect()
            try:
                count = resume_interrupted()
                self._log(f"✅ 恢复完成: {count} 个文件")
            except Exception as e:
                self._log(f"❌ 恢复失败: {e}")
            finally:
                self._restore_log_redirect()
                self.root.after(0, self._on_pipeline_done)

        threading.Thread(target=run, daemon=True).start()

    def _log(self, msg):
        """向日志区添加一行（线程安全）"""
        def do_log():
            self.log_area.config(state=NORMAL)
            self.log_area.insert(END, msg + "\n")
            self.log_area.see(END)
            self.log_area.config(state=DISABLED)
        self.root.after(0, do_log)

    def _setup_log_redirect(self):
        """将 logging 输出也捕获到 GUI"""
        class GuiHandler(logging.Handler):
            def __init__(self, gui):
                super().__init__()
                self.gui = gui
                self.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

            def emit(self, record):
                msg = self.format(record)
                self.gui._log(msg)

        handler = GuiHandler(self)
        handler.setLevel(logging.INFO)
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        self._log_handler = handler

    def _restore_log_redirect(self):
        try:
            if hasattr(self, "_log_handler"):
                logging.getLogger().removeHandler(self._log_handler)
        except Exception:
            pass

    def _scan_today(self):
        if self.running or getattr(self, '_scanning', False):
            messagebox.showinfo("提示", "正在扫描中，请稍后")
            return
        self._log("📡 开始扫描今天新文章...")
        def run():
            self._scanning = True
            try:
                n = rss_importer.run()
                self._log(f"  ✅ RSS: 新增 {n} 篇")
                col_id = self.zhihu_entry.get().strip()
                if col_id:
                    try:
                        self._log(f"  获取知乎专栏: {col_id}...")
                        n2 = rss_importer.fetch_zhihu(col_id)
                        self._log(f"  ✅ 知乎: 新增 {n2} 篇")
                    except Exception as e:
                        self._log(f"  ❌ 知乎获取失败: {e}")
                self._log("📡 扫描完成")
            except Exception as e:
                self._log(f"❌ 扫描异常: {e}")
            finally:
                self._scanning = False
        threading.Thread(target=run, daemon=True).start()

    def _download_all(self):
        if self.running:
            messagebox.showinfo("提示", "流水线正在运行中")
            return
        import json
        qpath = Path(__file__).resolve().parent.parent / "data" / "rss_queue.json"
        if qpath.exists():
            q = json.loads(qpath.read_text(encoding="utf-8"))
            pending = sum(1 for v in q.values() if v.get("status") == "待处理")
        else:
            pending = 0
        if pending == 0:
            messagebox.showinfo("提示", '队列中没有待处理的文章了，先用"扫描今天新文章"添加文章')
            return
        self._log(f"📥 开始下载全部队列 {pending} 篇...")
        def run():
            self.running = True
            self.download_btn.config(text="⬇  下载中...", bg="#95a5a6", state=DISABLED)
            self.scan_btn.config(state=DISABLED)
            try:
                done = rss_importer.proc()  # 无limit = 处理全部
                self._log(f"✅ 全部下载完成: {done} 篇")
            except Exception as e:
                self._log(f"❌ 下载异常: {e}")
            finally:
                self.running = False
                self.root.after(0, lambda: self.download_btn.config(
                    text="⬇  下载全部队列", bg="#1abc9c", state=NORMAL))
                self.root.after(0, lambda: self.scan_btn.config(state=NORMAL))
        threading.Thread(target=run, daemon=True).start()

def main():

    root = Tk()
    PipelineGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()