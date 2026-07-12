import os
import sys
import time
import threading
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

SUPPORTED_EXTS = {'.png','.jpg','.jpeg','.bmp','.tiff','.webp','.pdf','.docx','.md','.txt','.mp3','.wav','.m4a','.flac','.aac','.ogg','.amr'}

class WatcherHandler(FileSystemEventHandler):
    def __init__(self, input_dir, process_func):
        self.input_dir = input_dir
        self.process = process_func
        self.processing = set()
        self.lock = threading.Lock()

    def on_created(self, event):
        if event.is_directory:
            return
        path = event.src_path.replace('\\', '/')
        if not os.path.isfile(path):
            return
        time.sleep(1)
        with self.lock:
            if path in self.processing:
                return
            self.processing.add(path)
        thread = threading.Thread(target=self._process_safe, args=(path,), daemon=True)
        thread.start()

    def _process_safe(self, path):
        try:
            logging.info(f"检测到新文件: {path}")
            self.process(path)
        except Exception as e:
            logging.error(f"处理失败: {path} - {e}")
        finally:
            time.sleep(0.5)
            with self.lock:
                self.processing.discard(path)

def start_watcher(input_dir):
    from main import process_file
    event_handler = WatcherHandler(input_dir, process_file)
    observer = Observer()
    observer.schedule(event_handler, input_dir, recursive=False)

    observer.start()

    # 启动时扫一遍已有文件
    print("   [扫描] 扫描现有文件...")
    for f in sorted(os.listdir(input_dir)):
        fpath = os.path.join(input_dir, f)
        if os.path.isfile(fpath) and not f.startswith('.'):
            ext = os.path.splitext(f)[1].lower()
            if ext in SUPPORTED_EXTS:
                print(f"   [排队] 队列: {f}")
                dummy_event = type('e', (), {'is_directory': False, 'src_path': fpath})()
                event_handler.on_created(dummy_event)

    print(f"\n 开始监听: {os.path.abspath(input_dir)}")
    print("  把文件拖入 input/ 即可自动处理（Ctrl+C 停止）\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    start_watcher("input")