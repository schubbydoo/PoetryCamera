"""Poem activity events and the shared Dashboard. Run with propkit on PYTHONPATH (see test_ai_settings.py)."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.expanduser("~/propkit"))   # as the app does, so tests also prove the app needs no PYTHONPATH
_TMP = tempfile.mkdtemp()
os.environ["POETRYCAMERA_EVENTS_DIR"] = os.path.join(_TMP, "events")   # before the app is imported

from propkit.stats import StatsSpec, compute, read_events  # noqa: E402
from web_interface import poem_stats  # noqa: E402

SPEC = StatsSpec(noun="poem", outcomes={"ok": ("Written", "good"), "fallback": ("Canned poem (AI failed)", "warn")})


class StatsTests(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(poem_stats.EVENTS_DIR, ignore_errors=True)
        poem_stats._recorder = None
        self.log = os.path.join(_TMP, "poem_log.jsonl")
        self._orig = poem_stats.LOG_PATH
        poem_stats.LOG_PATH = self.log
        if os.path.exists(self.log):
            os.remove(self.log)

    def tearDown(self):
        poem_stats.LOG_PATH = self._orig

    def test_record_then_compute(self):
        poem_stats.record_poem("anthropic", "claude-sonnet-4-6", 4.5)
        poem_stats.record_poem(None, None, None, fallback=True)
        ev = read_events(poem_stats.EVENTS_DIR)
        self.assertEqual([(e["kind"], e["outcome"]) for e in ev], [("poem", "ok"), ("poem", "fallback")])
        self.assertEqual(ev[0]["detail"], "anthropic/claude-sonnet-4-6")
        self.assertNotIn("text", ev[0])
        out = compute(poem_stats.EVENTS_DIR, SPEC)
        self.assertTrue(json.dumps(out))           # whole summary serialises
        self.assertIn("2", json.dumps(out["summary"] if "summary" in out else out))

    def test_recording_never_raises_and_old_log_still_written(self):
        poem_stats.EVENTS_DIR, keep = "/proc/nope/events", poem_stats.EVENTS_DIR
        poem_stats._recorder = None
        try:
            poem_stats.record_poem("openai", "gpt-4o", 3.0)   # unwritable events dir
        finally:
            poem_stats.EVENTS_DIR = keep
            poem_stats._recorder = None
        self.assertEqual(len(open(self.log).read().splitlines()), 1)

    def test_backfill_is_idempotent(self):
        with open(self.log, "w") as f:
            f.write(json.dumps({"time": "2026-10-29T19:38:12", "provider": "anthropic", "model": "m", "seconds": 4.9, "fallback": False}) + "\n")
            f.write(json.dumps({"time": "2026-10-29T19:46:44", "provider": None, "model": None, "seconds": None, "fallback": True}) + "\n")
            f.write("not json\n")
        before = open(self.log).read()
        self.assertEqual(poem_stats.backfill_events(), 2)
        self.assertEqual(poem_stats.backfill_events(), 0)
        ev = read_events(poem_stats.EVENTS_DIR)
        self.assertEqual([e["outcome"] for e in ev], ["ok", "fallback"])
        self.assertEqual(open(self.log).read(), before)        # the old log is untouched

    def test_canned_streak_and_banner(self):
        from web_interface.app import _banner
        self.assertEqual(poem_stats.canned_streak(), 0)
        self.assertIsNone(_banner())
        poem_stats.record_poem("a", "m", 4.0)
        poem_stats.record_poem(None, None, None, fallback=True)
        self.assertIsNone(_banner())                       # one canned poem is not yet a warning
        poem_stats.record_poem(None, None, None, fallback=True)
        b = _banner()
        self.assertEqual((b["tone"], poem_stats.canned_streak()), ("warn", 2))
        self.assertIn("2 poems", b["text"])
        poem_stats.record_poem("a", "m", 4.0)              # a good poem clears it
        self.assertIsNone(_banner())

    def test_page_and_api_reflect_a_poem(self):
        from web_interface.app import app
        poem_stats.record_poem("anthropic", "claude-sonnet-4-6", 4.2)
        c = app.test_client()
        self.assertEqual(c.get("/").status_code, 200)
        self.assertEqual(c.get("/api/stats").status_code, 200)
        evs = c.get("/api/events").get_json()
        text = json.dumps(evs)
        self.assertIn("claude-sonnet-4-6", text)
        self.assertEqual(c.get("/settings").status_code, 200)
        self.assertIn(b"btn-test-print", c.get("/settings").data)


if __name__ == "__main__":
    unittest.main()
