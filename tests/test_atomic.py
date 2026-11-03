"""Shared files are replaced atomically and readers keep the previous settings (temp folders only)."""
import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.expanduser("~/propkit"))

import atomic_io
import zoltar_poems
from web_interface.config_manager import ConfigManager


class AtomicTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_write_keeps_permissions_and_leaves_no_temp(self):
        p = os.path.join(self.tmp, "a.json")
        atomic_io.write_json(p, {"x": 1}, mode=0o600)
        atomic_io.write_json(p, {"x": 2})
        self.assertEqual(oct(os.stat(p).st_mode & 0o777), "0o600")
        self.assertEqual(os.listdir(self.tmp), ["a.json"])
        self.assertEqual(atomic_io.read_json(p), {"x": 2})

    def test_race_writer_vs_readers(self):
        p = os.path.join(self.tmp, "race.json")
        big = {"k%d" % i: "v" * 50 for i in range(400)}
        atomic_io.write_json(p, dict(big, n=0))
        stop, bad, reads = threading.Event(), [], [0]

        def writer():
            n = 0
            while not stop.is_set():
                n += 1
                atomic_io.write_json(p, dict(big, n=n), indent=2)

        def reader():
            while not stop.is_set():
                d = atomic_io.read_json(p)
                reads[0] += 1
                if not d or len(d) != 401:
                    bad.append(d)

        ts = [threading.Thread(target=writer)] + [threading.Thread(target=reader) for _ in range(4)]
        [t.start() for t in ts]
        stop.wait(3)
        stop.set()
        [t.join() for t in ts]
        self.assertGreater(reads[0], 100)
        self.assertEqual(len(bad), 0)

    def _manager(self, text):
        cm = ConfigManager.__new__(ConfigManager)
        cm.config_file = Path(self.tmp) / "cfg.json"
        cm.config_file.write_text(text)
        cm._read_failed = False
        return cm

    def test_reload_keeps_previous_config_when_file_is_broken(self):
        good = json.dumps({"printer": {"cat_printer": {"mac_address": "AA:BB"}}, "auth": {"secret_key": "k", "password_hash": "h"}})
        cm = self._manager(good)
        cm.reload()
        for broken in ("", '{"printer": {"cat_pr', "[1,2]"):
            cm.config_file.write_text(broken)
            cm.reload()
            self.assertEqual(cm.config["printer"]["cat_printer"]["mac_address"], "AA:BB")
            self.assertEqual(cm.config_file.read_text(), broken)     # nothing was written over it

    def test_unreadable_at_start_never_overwrites_file(self):
        cm = self._manager("")
        cm.config = {}
        cm._read_failed = True
        cm._ensure_defaults()
        self.assertEqual(cm.config_file.read_text(), "")

    def test_config_race_through_manager(self):
        cm = self._manager(json.dumps({"auth": {"secret_key": "k", "password_hash": "h"}}))
        cm.reload()
        stop, bad = threading.Event(), []

        def writer():
            n = 0
            while not stop.is_set():
                n += 1
                cm.config["openai"]["model"] = "m%d" % n
                cm._save_config()

        def reader():
            other = self._manager(cm.config_file.read_text())
            while not stop.is_set():
                other.reload()
                if other.config["printer"]["cat_printer"]["mac_address"] != "A7:09:08:1B:58:69":
                    bad.append(1)

        ts = [threading.Thread(target=writer)] + [threading.Thread(target=reader) for _ in range(3)]
        [t.start() for t in ts]
        stop.wait(3)
        stop.set()
        [t.join() for t in ts]
        self.assertEqual(len(bad), 0)

    def test_zoltar_settings_survive_broken_file(self):
        zoltar_poems.SETTINGS_PATH = os.path.join(self.tmp, "z.json")
        zoltar_poems.STATE_PATH = os.path.join(self.tmp, "zs.json")
        zoltar_poems._last_good = None
        zoltar_poems.save_settings({"enabled": True, "address": "10.0.0.5:8000", "token": "secret"})
        self.assertEqual(oct(os.stat(zoltar_poems.SETTINGS_PATH).st_mode & 0o777), "0o600")
        self.assertTrue(zoltar_poems.get_settings()["enabled"])
        open(zoltar_poems.SETTINGS_PATH, "w").write("")
        s = zoltar_poems.get_settings()
        self.assertTrue(s["enabled"])
        self.assertEqual(s["token"], "secret")

    def test_zoltar_save_refuses_when_unreadable_on_first_read(self):
        zoltar_poems.SETTINGS_PATH = os.path.join(self.tmp, "z2.json")
        zoltar_poems._last_good = None
        open(zoltar_poems.SETTINGS_PATH, "w").write('{"enabled": tr')
        with self.assertRaises(RuntimeError):
            zoltar_poems.save_settings({"enabled": True})
        self.assertEqual(open(zoltar_poems.SETTINGS_PATH).read(), '{"enabled": tr')

    def test_lucky_state_written_atomically(self):
        zoltar_poems.STATE_PATH = os.path.join(self.tmp, "state.json")
        n = zoltar_poems.pick_number()
        self.assertIn(n, zoltar_poems.NUMBERS)
        self.assertIn(str(n), atomic_io.read_json(zoltar_poems.STATE_PATH))


if __name__ == "__main__":
    unittest.main()
