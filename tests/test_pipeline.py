"""流水线集成测试 — 覆盖核心函数的正常路径和异常路径"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ["TOKENIZERS_PARALLELISM"] = "false"


class TestSaveResult:
    """save_result() 输出的 .md 文件结构是否正确"""

    def test_frontmatter_has_title(self):
        """YAML frontmatter 的 title 字段必须正确"""
        from src.main import save_result
        path = save_result("Hello world", "", "Test Title")
        assert path and os.path.exists(path), "文件未生成"
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert 'title: "Test Title"' in content, f"标题错误: {content[:200]}"
        assert content.startswith("---"), "缺少 YAML 起始 ---"
        os.remove(path)

    def test_frontmatter_has_date(self):
        """YAML frontmatter 必须包含日期"""
        from src.main import save_result
        path = save_result("Test", "", "Date Test")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "date: " in content, "缺少 date 字段"
        os.remove(path)

    def test_content_preserved(self):
        """正文内容应当保留"""
        from src.main import save_result
        body = "这是测试正文内容"
        path = save_result(body, "", "Content Test")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert body in content, "正文丢失"
        os.remove(path)


class TestConfig:
    """config.py 配置加载"""

    def test_config_imports(self):
        """所有配置变量可导入且类型正确"""
        from src import config
        assert hasattr(config, "ZHIPUAI_API_KEY")
        assert hasattr(config, "OUTPUT_DIR")
        assert hasattr(config, "CHROMA_DB_PATH")
        assert isinstance(config.OBSIDIAN_VAULT_PATH, str)

    def test_output_dir_is_absolute(self):
        """OUTPUT_DIR 应该是绝对路径"""
        from src import config
        assert os.path.isabs(config.OUTPUT_DIR) or config.OUTPUT_DIR.startswith("G:")


class TestClassifier:
    """内容分类器"""

    def test_short_text_skipped(self):
        """极短文本应返回 skip"""
        from src.classifier import classify_content
        from src.config import ZHIPUAI_API_KEY
        result = classify_content(ZHIPUAI_API_KEY, "hi")
        assert result == "skip"

    def test_empty_text_returns_skip(self):
        """空文本应返回 skip"""
        from src.classifier import classify_content
        from src.config import ZHIPUAI_API_KEY
        result = classify_content(ZHIPUAI_API_KEY, "")
        assert result == "skip"
