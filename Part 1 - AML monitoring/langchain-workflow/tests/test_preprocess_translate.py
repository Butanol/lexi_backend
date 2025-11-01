import importlib.util
from pathlib import Path
from unittest.mock import Mock, patch


def _load_preprocess_module():
    # Load the preprocess_data module by file path to avoid import path issues
    repo_root = Path(__file__).resolve().parents[3]
    module_path = repo_root / "Part 1 - AML monitoring" / "langchain-workflow" / "scripts" / "preprocess_data.py"
    spec = importlib.util.spec_from_file_location("preprocess_data", str(module_path))
    module = importlib.util.module_from_spec(spec)
    # Inject a lightweight mock for pdfminer.high_level.extract_text so the
    # module can be imported in test environments without pdfminer installed.
    import sys, types
    pdfminer_mod = types.ModuleType("pdfminer")
    pdfminer_high = types.ModuleType("pdfminer.high_level")
    def _fake_extract_text(p):
        return "(extracted text)"
    pdfminer_high.extract_text = _fake_extract_text
    sys.modules.setdefault("pdfminer", pdfminer_mod)
    sys.modules.setdefault("pdfminer.high_level", pdfminer_high)

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
