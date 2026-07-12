import os
import glob

def load_obsidian_notes(vault_path, max_files=10):
    """
    从 Obsidian 仓库读取 Markdown 笔记作为风格参考
    :param vault_path: Obsidian 仓库根目录
    :param max_files: 最多读取多少篇笔记
    :return: 笔记内容列表
    """
    notes = []
    if not os.path.exists(vault_path):
        print(f"警告: Obsidian 路径不存在: {vault_path}")
        return notes

    md_files = glob.glob(os.path.join(vault_path, "**", "*.md"), recursive=True)

    for file_path in md_files[:max_files]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if len(content) > 100:
                    notes.append(content)
        except Exception as e:
            print(f"读取文件失败 {file_path}: {e}")

    return notes