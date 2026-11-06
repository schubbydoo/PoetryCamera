"""The capability list is well formed and claims nothing the code lacks."""
import os
import re
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.expanduser("~/propkit"))

from propkit import capabilities as pk_caps
from web_interface.capabilities import capabilities

# What must exist in the code for each installed capability (id -> list of "module:attribute" or "file:text").
EVIDENCE = {
    "poem.photo": ["poem_ai:generate_openai", "poem_ai:generate_anthropic", "poem_ai:clean_poem", "main:def print_poem", "main:Button(16)"],
    "poem.formats": ["poem_ai:POEM_FORMAT_DESCRIPTIONS", "web_interface/ai_settings.py:demo_context"],
    "print.thermal": ["printer/scripts/cat_printer.py:MX06", "printer/scripts/network_printer.py:class NetworkPrinter",
                      "web_interface/app.py:/api/printer/test"],
    "zoltar.lucky_number": ["zoltar_poems:register", "zoltar_poems:pick_number", "printer/scripts/cat_printer.py:def create_lucky_block",
                            "web_interface/app.py:/api/settings/zoltar"],
    "ai.settings": ["web_interface/ai_settings.py:def test", "web_interface/ai_health.py:def run_checks", "web_interface/app.py:_banner"],
}


def read(rel):
    with open(os.path.join(ROOT, rel)) as f:
        return f.read()


class CapabilityTests(unittest.TestCase):
    def test_well_formed_and_survives_propkit_cleaning(self):
        caps = capabilities()
        cleaned = pk_caps.clean(caps)
        self.assertEqual(len(cleaned), len(caps))
        ids = [c["id"] for c in caps]
        self.assertEqual(len(set(ids)), len(ids))
        for c in caps:
            self.assertTrue(c["label"] and c["description"], c["id"])
            if c["installed"]:
                self.assertTrue(c["since"] and c["plain"], c["id"])
                self.assertEqual(c["reason"] if "reason" in c else "", "")
            else:
                self.assertTrue(c["reason"], "%s is not installed: needs a reason" % c["id"])
            self.assertEqual(c["ops"], [])

    def test_installed_claims_match_the_code(self):
        installed = {c["id"] for c in capabilities() if c["installed"]}
        self.assertEqual(installed, set(EVIDENCE), "every installed capability needs evidence here, and vice versa")
        for cid, checks in EVIDENCE.items():
            for chk in checks:
                where, what = chk.split(":", 1)
                if where.endswith(".py"):
                    self.assertTrue(what in read(where), "%s: %s missing in %s" % (cid, what, where))
                elif what.startswith("def ") or what == "Button(16)":
                    self.assertTrue(what in read(where + ".py"), "%s: %s missing in %s" % (cid, what, where))
                else:
                    mod = __import__(where)
                    self.assertTrue(hasattr(mod, what), "%s: %s.%s missing" % (cid, where, what))

    def test_not_installed_things_really_are_absent(self):
        self.assertNotIn("def print_photo", read("main.py"))
        self.assertNotIn("/api/trigger", read("web_interface/app.py"))
        self.assertNotIn("pyttsx3", read("requirements.txt"))


if __name__ == "__main__":
    unittest.main()
