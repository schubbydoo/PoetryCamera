"""Tests for the camera's adapter to propkit's AI tab. Run: PYTHONPATH=<propkit dir> python3 -m unittest discover -s tests"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from web_interface import ai_settings, config_manager as cm_mod  # noqa: E402
from web_interface.config_manager import config_manager  # noqa: E402
import poem_ai  # noqa: E402


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._orig = (config_manager.config_file, config_manager.config)
        config_manager.config_file = Path(self.tmp) / "cfg.json"
        config_manager.config = {}
        config_manager._ensure_defaults()
        config_manager._save_config()

    def tearDown(self):
        config_manager.config_file, config_manager.config = self._orig
        shutil.rmtree(self.tmp)

    def test_defaults_match_stock_config(self):
        d = ai_settings.defaults()
        self.assertEqual(d["model_provider"], "anthropic")
        self.assertIn(d["poem_format"], poem_ai.POEM_FORMAT_DESCRIPTIONS)
        self.assertEqual(d["demo_context"], "")

    def test_round_trip(self):
        ok, _ = ai_settings.save({"model_provider": "anthropic", "model": "claude-sonnet-4-6", "poem_prompt": "Write a poem.",
                                  "poem_format": "limerick", "demo_context": "  Halloween party  "})
        self.assertTrue(ok)
        v = ai_settings.load()
        self.assertEqual((v["model_provider"], v["model"], v["poem_format"]), ("anthropic", "claude-sonnet-4-6", "limerick"))
        self.assertEqual(v["demo_context"], "Halloween party")
        # the file the camera loop reads has the same values
        self.assertEqual(config_manager.get_ai_provider(), "anthropic")
        self.assertEqual(config_manager.get_openai_model(), "claude-sonnet-4-6")
        with open(config_manager.config_file) as f:
            self.assertEqual(json.load(f)["openai"]["provider"], "anthropic")

    def test_partial_save_keeps_other_values(self):
        ai_settings.save({"model": "gpt-4.1-mini"})
        v = ai_settings.load()
        self.assertEqual(v["model"], "gpt-4.1-mini")
        self.assertTrue(v["poem_prompt"].strip())

    def test_bad_input_is_refused_and_nothing_changes(self):
        before = ai_settings.load()
        for bad in ({"model_provider": "evil"}, {"model": "bad model!"}, {"model": ""}, {"poem_format": "haiku-ish"},
                    {"poem_prompt": "   "}, {"poem_prompt": "x" * 5000}, {"demo_context": "x" * 5000}):
            ok, msg = ai_settings.save(bad)
            self.assertFalse(ok, bad)
            self.assertTrue(msg)
        self.assertEqual(ai_settings.load(), before)

    def test_reset_to_defaults(self):
        ai_settings.save({"model_provider": "anthropic", "model": "claude-sonnet-4-6", "demo_context": "x"})
        ok, _ = ai_settings.save(ai_settings.defaults())
        self.assertTrue(ok)
        self.assertEqual(ai_settings.load(), ai_settings.defaults())

    def test_defaults_are_valid_options(self):
        from types import SimpleNamespace
        from propkit import ai
        self.assertEqual(ai.AIPage(SimpleNamespace(ai=ai_settings.build())).check_defaults(), [])

    def test_test_with_bad_picked_file(self):
        base = {"model_provider": "openai", "model": "gpt-4o-mini"}
        r = ai_settings.test(base, None, {"name": "x.txt", "type": "text/plain", "data": b"hi"})
        self.assertFalse(r["ok"])
        r = ai_settings.test(base, None, {"name": "x.jpg", "type": "image/jpeg", "data": b"x" * (6 * 1024 * 1024)})
        self.assertFalse(r["ok"])
        self.assertIn("too large", r["detail"])

    def test_health_items_name_their_provider(self):
        from web_interface import ai_health
        self.assertEqual(ai_health._check("anthropic", "", "m", True)["provider"], "anthropic")

    def test_test_without_photo_or_key_never_raises(self):
        r = ai_settings.test({"model_provider": "openai", "model": "gpt-4o-mini"})
        self.assertFalse(r["ok"])
        self.assertTrue(r["detail"])


class PromptTests(unittest.TestCase):
    def test_prompt_contents(self):
        p = poem_ai.build_prompt("Base {format_variable}", "limerick", "")
        self.assertTrue(p.startswith("CRITICAL RULE: NEVER use he/him/his"))
        self.assertIn("Base limerick — 5 lines, AABBA", p)
        self.assertNotIn("PRIVATE CONTEXT", p)
        self.assertIn("PRIVATE CONTEXT", poem_ai.build_prompt("x", "limerick", "a raven"))

    def test_clean_poem(self):
        self.assertEqual(poem_ai.clean_poem("Here's a poem:\n**Roses** red\nviolets blue\n\nNote: hope you like it"),
                         "Roses red\nviolets blue")


if __name__ == "__main__":
    unittest.main()
