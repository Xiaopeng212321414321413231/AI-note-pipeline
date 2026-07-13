# -*- coding: utf-8 -*-
"""启动健康检查 — 在流水线运行前检查环境完整性"""
import os, sys, json
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent

def get_api_key():
    env_path = PROJECT_DIR / '.env'
    if not env_path.exists():
        return None
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('ZHIPUAI_API_KEY='):
                val = line.split('=', 1)[1].strip().strip("\"'")
                return val
    return None

def check_rapidocr():
    try:
        from rapidocr_onnxruntime import RapidOCR
        engine = RapidOCR()
        import numpy as np
        blank = np.ones((100, 100, 3), dtype=np.uint8) * 255
        result, _ = engine(blank)
        return ('ok', 'RapidOCR 引擎可用')
    except ImportError:
        return ('warn', 'rapidocr-onnxruntime 未安装，回退 Tesseract')
    except Exception as e:
        return ('warn', f'RapidOCR 异常: {str(e)[:50]}')

def check_api_key():
    key = get_api_key()
    if not key:
        return ('error', '未找到 ZHIPUAI_API_KEY（请检查 .env 文件）')
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key, base_url='https://open.bigmodel.cn/api/paas/v4/', timeout=10)
        resp = client.chat.completions.create(
            model='glm-4-flash', messages=[{'role':'user','content':'hi'}], max_tokens=1
        )
        return ('ok', f'API Key 有效（{key[:8]}...）')
    except Exception as e:
        err = str(e)
        if '401' in err:
            return ('error', f'API Key 无效: 认证失败')
        if '1301' in err:
            return ('warn', 'API Key 有效，但输入被安全过滤')
        return ('warn', f'API 请求异常: {str(e)[:50]}')

def check_chromadb():
    db_path = PROJECT_DIR / 'data' / 'chroma_db'
    if not db_path.exists():
        return ('warn', 'ChromaDB 目录不存在，首次运行自动创建')
    try:
        import chromadb
        client = chromadb.PersistentClient(str(db_path))
        client.heartbeat()
        return ('ok', 'ChromaDB 连接正常')
    except Exception as e:
        return ('warn', f'ChromaDB 异常: {str(e)[:50]}')

def check_input_dirs():
    input_dir = PROJECT_DIR / 'input'
    if not input_dir.exists():
        return ('error', 'input 目录不存在！')
    errors = input_dir / 'error'
    error_count = len(list(errors.glob('*'))) if errors.exists() else 0
    if error_count > 0:
        return ('warn', f'待重试文件: {error_count} 个')
    return ('ok', '无积压文件')

def run_all():
    checks = [
        ('RapidOCR', check_rapidocr()),
        ('API Key', check_api_key()),
        ('ChromaDB', check_chromadb()),
        ('Input目录', check_input_dirs()),
    ]
    icons = {'ok': '✅', 'warn': '⚠️', 'error': '❌'}
    has_error = False
    lines = ['='*50, '  🔍 启动前环境检查', '='*50]
    for name, (status, msg) in checks:
        lines.append(f'  {icons.get(status, "❓")} {name}: {msg}')
        if status == 'error':
            has_error = True
    lines.append('='*50)
    if has_error:
        lines.append('  ❌ 存在严重问题，建议修复后重试')
    else:
        lines.append('  ✅ 一切正常，开始处理！')
    lines.append('='*50)
    return ('\n'.join(lines), has_error)

if __name__ == '__main__':
    output, has_error = run_all()
    print(output)
    sys.exit(1 if has_error else 0)
