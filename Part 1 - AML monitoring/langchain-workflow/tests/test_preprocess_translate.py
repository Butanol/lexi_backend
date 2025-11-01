import importlib.util
from pathlib import Path
from unittest.mock import Mock, patch


def _load_preprocess_module():
    # Load the preprocess_data module by file path to avoid import path issues
    repo_root = Path(__file__).resolve().parents[3]
    module_path = repo_root / "Part 1 - AML monitoring" / "langchain-workflow" / "scripts" / "preprocess_data.py"
    spec = importlib.util.spec_from_file_location("preprocess_data", str(module_path))
    module = importlib.util.module_from_spec(spec)
    # Inject a lightweight mock for the fitz module so the module can be
    # imported in test environments without PyMuPDF installed.
    import sys, types
    fitz_mod = types.ModuleType("fitz")

    class FakePage:
        def __init__(self, text):
            self._text = text

        def get_text(self, mode="text"):
            return self._text

    class FakeDoc(list):
        def __init__(self, pages):
            super().__init__([FakePage(p) for p in pages])

    def fake_open(path):
        # return a doc with a single page for tests
        return FakeDoc(["(extracted text)"])

    fitz_mod.open = fake_open
    sys.modules.setdefault("fitz", fitz_mod)

    spec.loader.exec_module(module)
    return module


def _mock_response(json_data):
    m = Mock()
    m.json.return_value = json_data
    m.raise_for_status.return_value = None
    return m


def test_translate_handles_list_response():
    module = _load_preprocess_module()
    sample = {"success": True, "translated_text": ["你好", "你好吗？", "谢谢"]}
    import os
    os.environ["JIGSAWSTACK_API_KEY"] = "test-key"

    with patch("requests.post") as post:
        post.return_value = _mock_response(sample)
        out = module.translate_text_jigsaw("Hello\nHow are you?\nThank you", target="zh")
        assert out == "你好\n\n你好吗？\n\n谢谢"


def test_translate_handles_string_response():
    module = _load_preprocess_module()
    sample = {"success": True, "translated_text": "你好\n你好吗？\n谢谢"}
    import os
    os.environ["JIGSAWSTACK_API_KEY"] = "test-key"

    with patch("requests.post") as post:
        post.return_value = _mock_response(sample)
        out = module.translate_text_jigsaw("Hello\nHow are you?\nThank you", target="zh")
        assert out == "你好\n你好吗？\n谢谢"
