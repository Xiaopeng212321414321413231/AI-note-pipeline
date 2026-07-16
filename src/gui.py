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
from tkinter import ttk, scrolledtext, messagebox
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.checkpoint import (
    load, get_interrupted, get_errors, get_pending,
    summary, clear_all, STAGES, STAGE_NAMES,
)
from src.main import run_pipeline, process_input_dir, resume_interrupted
from src import rss_importer

class PipelineGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AI 笔记流水线 v2.0")
        self.root.geometry("700x580")
        self.root.resizable(True, True)

        # 设置样式
        self.root.configure(bg="#f0f0f0")
        style = ttk.Style()
        style.theme_use("clam")

        # 运行状态
        self.running = False
        self.stop_flag = False

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

        # --- 📁 本地文件处理 ---
        Label(main_frame, text="📁 本地文件处理", bg="#f0f0f0",
              font=("Microsoft YaHei", 11, "bold"),
              fg="#2b3e4f", anchor="w").pack(fill=X, pady=(0, 3))
        btn_frame = Frame(main_frame, bg="#f0f0f0")
        btn_frame.pack(fill=X, pady=(0, 10))

        self.start_btn = Button(
            btn_frame,
            text="▶  开始处理",
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
        self.start_btn.config(text="⏹  处理中...", bg="#e67e22", state=NORMAL)
        self.clear_btn.config(state=DISABLED)
        self.resume_btn.config(state=DISABLED)
        self.skip_resume_btn.config(state=DISABLED)
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
        self.start_btn.config(text="▶  开始处理", bg="#27ae60", state=NORMAL)
        self.clear_btn.config(state=NORMAL)
        self.resume_btn.config(state=NORMAL)
        self.skip_resume_btn.config(state=NORMAL)
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