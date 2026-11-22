import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import update_profile as updater
import validate_profile as validator

SHA = "a" * 40
TEMPLATE = (ROOT / "templates/FengGe.conf").read_text(encoding="utf-8")


def report(raw):
    return {
        "profile_sha256": hashlib.sha256(raw).hexdigest(),
        "expanded_rule_entries": 47760, "remote_bytes": 824000,
        "remote_files": 18, "sample_checks_passed": 58,
        "sources": [{"url": validator.SOURCE_PREFIX + SHA + "/rule/Shadowrocket/AdvertisingLite/AdvertisingLite_Domain.list",
                     "entries": 37692, "sha256": "unchanged", "bytes": 595771}],
    }


class UpdateTests(unittest.TestCase):
    def test_git_lookup_requires_exact_upstream_branch(self):
        with patch("update_profile.subprocess.run", return_value=SimpleNamespace(stdout=SHA + "\trefs/heads/master\n")):
            self.assertEqual(updater.current_upstream(), SHA)
        with patch("update_profile.subprocess.run", return_value=SimpleNamespace(stdout=SHA + "\trefs/heads/other\n")):
            with self.assertRaises(ValueError):
                updater.current_upstream()

    def workspace(self, raw):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / "templates").mkdir()
        (root / "profiles").mkdir()
        (root / "templates/FengGe.conf").write_text(TEMPLATE, encoding="utf-8")
        (root / "profiles/FengGe.conf").write_bytes(raw)
        (root / "profiles/validation-report.json").write_text(json.dumps(report(raw)))
        return root

    def test_pins_every_source_to_one_immutable_revision(self):
        raw = updater.pin(TEMPLATE, SHA)
        _, _, rules = validator.check_profile(raw)
        refs = [r[1] for r in rules if r[0] in {"RULE-SET", "DOMAIN-SET"}]
        self.assertEqual(len(refs), 18)
        self.assertTrue(all(validator.SOURCE_PATTERN.fullmatch(u).group(1) == SHA for u in refs))
        self.assertNotIn("/master/rule/", raw.decode())

    def test_fetch_rejects_floating_or_unapproved_sources(self):
        with patch("validate_profile.urllib.request.urlopen") as network:
            for url in [validator.SOURCE_PREFIX + "master/rule/Shadowrocket/China/China.list",
                        "https://example.com/rules.list"]:
                with self.assertRaises(ValueError):
                    validator.fetch(url)
            network.assert_not_called()

    def test_download_or_route_failure_leaves_all_published_files_unchanged(self):
        root = self.workspace(TEMPLATE.encode())
        files = [root / "profiles/FengGe.conf", root / "profiles/validation-report.json"]
        before = [p.read_bytes() for p in files]
        with patch("update_profile.validate", side_effect=ValueError("source unreachable")):
            with self.assertRaises(ValueError):
                updater.update(root, SHA)
        self.assertEqual(before, [p.read_bytes() for p in files])
        self.assertFalse((root / "profiles/FengGe-Emergency.conf").exists())

    def test_expansion_or_truncation_stops_publication(self):
        old = report(TEMPLATE.encode())
        for change in ({"expanded_rule_entries": 65001}, {"remote_bytes": 1500001}):
            bad = copy.deepcopy(old)
            bad.update(change)
            with self.assertRaises(ValueError):
                updater.check_budget(bad, old)
        for count in (22000, 51000):
            bad = copy.deepcopy(old)
            bad["sources"][0]["entries"] = count
            with self.assertRaises(ValueError):
                updater.check_budget(bad, old)
        updater.check_budget(old, old)

    def test_budget_failure_does_not_touch_live_files(self):
        root = self.workspace(TEMPLATE.encode())
        before = {p.name: p.read_bytes() for p in (root / "profiles").iterdir()}
        bad = report(updater.pin(TEMPLATE, SHA))
        bad["expanded_rule_entries"] = 999999
        with patch("update_profile.validate", return_value=bad):
            with self.assertRaises(ValueError):
                updater.update(root, SHA)
        self.assertEqual(before, {p.name: p.read_bytes() for p in (root / "profiles").iterdir()})

    def test_detects_unvalidated_manual_output_edit(self):
        root = self.workspace(TEMPLATE.encode())
        (root / "profiles/FengGe.conf").write_text("unexpected edit")
        with patch("update_profile.validate") as validate:
            with self.assertRaises(ValueError):
                updater.update(root, SHA)
            validate.assert_not_called()

    def test_success_produces_consistent_config_report_and_emergency(self):
        root = self.workspace(TEMPLATE.encode())
        with patch("update_profile.validate", side_effect=report):
            self.assertTrue(updater.update(root, SHA))
        raw = (root / "profiles/FengGe.conf").read_bytes()
        result = json.loads((root / "profiles/validation-report.json").read_text())
        self.assertEqual(result["profile_sha256"], hashlib.sha256(raw).hexdigest())
        emergency = (root / "profiles/FengGe-Emergency.conf").read_bytes()
        self.assertEqual(result["emergency_profile"]["sha256"], hashlib.sha256(emergency).hexdigest())
        self.assertEqual(updater.check_emergency(emergency), 10)

    def test_unrelated_upstream_commit_does_not_rewrite_outputs(self):
        root = self.workspace(updater.pin(TEMPLATE, SHA))
        emergency = updater.emergency_profile(updater.pin(TEMPLATE, SHA))
        (root / "profiles/FengGe-Emergency.conf").write_bytes(emergency)
        before = {p.name: p.read_bytes() for p in (root / "profiles").iterdir()}
        with patch("update_profile.validate", side_effect=report):
            self.assertFalse(updater.update(root, "b" * 40))
        self.assertEqual(before, {p.name: p.read_bytes() for p in (root / "profiles").iterdir()})

    def test_emergency_has_no_external_rules_or_test_groups(self):
        emergency = updater.emergency_profile(updater.pin(TEMPLATE, SHA))
        self.assertEqual(updater.check_emergency(emergency), 10)
        self.assertNotIn(b"raw.githubusercontent.com", emergency)
        self.assertNotIn(b"TAILSCALE", emergency)
        self.assertNotIn(b"url-test", emergency)


    def test_management_routes_and_emergency_never_use_public_proxy(self):
        raw = updater.pin(TEMPLATE, SHA)
        sections, _, rules = validator.check_profile(raw)
        mappings = dict(line.split(" = ", 1) for line in sections["Host"])
        general = dict(line.split(" = ", 1) for line in sections["General"])
        self.assertEqual(general["use-local-host-item-for-proxy"], "true")
        for host in ("hermes.staru.icu", "secure.staru.icu"):
            self.assertEqual(mappings[host], "server:100.123.3.89")
            self.assertEqual(validator.route(rules, host=host, country="CN"), "TAILSCALE")
        self.assertEqual(validator.route(rules, ip="100.123.3.89", country="CN"), "TAILSCALE")
        self.assertNotEqual(validator.route(rules, host="api.staru.icu", country="CN"), "TAILSCALE")
        self.assertNotEqual(validator.route(rules, ip="100.123.3.90", country="CN"), "TAILSCALE")
        emergency = updater.emergency_profile(raw).decode()
        emergency_rules = [line.split(",") for line in
                           emergency.split("[Rule]", 1)[1].split("[Host]", 1)[0].splitlines()
                           if line and not line.startswith("#")]
        for host in ("hermes.staru.icu", "secure.staru.icu"):
            self.assertEqual(validator.route(emergency_rules, host=host), "REJECT")
        self.assertEqual(validator.route(emergency_rules, ip="100.123.3.89"), "REJECT")


if __name__ == "__main__":
    unittest.main()
