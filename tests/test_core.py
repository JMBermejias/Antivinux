# -*- coding: utf-8 -*-
"""Pruebas basicas del nucleo de Antivinux (no requieren GTK)."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from antivinux.backend import (  # noqa: E402
    parse_cvd_header,
    database_files,
    count_signatures,
)
from antivinux.backend.quarantine import QuarantineManager  # noqa: E402
from antivinux.backend.clamav import Scanner  # noqa: E402
from antivinux.backend import appupdate  # noqa: E402


HEADER = (
    "ClamAV-VDB:17 Sep 2026 06-24 +0000:28126:355666:90:"
    "d11370bc331eaffe:extra:1\n"
)


class CvdHeaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="antivinux-test-")

    def _write(self, name, header):
        path = os.path.join(self.tmp, name)
        with open(path, "wb") as fh:
            fh.write(header.encode("latin-1"))
            fh.write(b"\x00" * 1024)
        return path

    def test_parse_header(self):
        path = self._write("daily.cvd", HEADER)
        info = parse_cvd_header(path)
        self.assertEqual(info["version"], "28126")
        self.assertEqual(info["signatures"], 355666)
        self.assertEqual(info["functional_level"], 90)
        self.assertIn("17 Sep 2026", info["date"])

    def test_invalid_header(self):
        path = os.path.join(self.tmp, "bad.cvd")
        with open(path, "wb") as fh:
            fh.write(b"NOT-A-CVD-HEADER\n")
        self.assertIsNone(parse_cvd_header(path))

    def test_database_files_and_count(self):
        self._write("main.cvd", HEADER.replace("28126", "62"))
        self._write("bytecode.cvd", HEADER.replace("28126", "340"))
        files = database_files(self.tmp)
        self.assertIn("main.cvd", files)
        self.assertIn("bytecode.cvd", files)
        entries = {}
        for name in files:
            info = parse_cvd_header(os.path.join(self.tmp, name))
            entries[name] = {"signatures": info["signatures"], "size": 1024}
        self.assertEqual(count_signatures(entries), 355666 * 2)


class QuarantineTests(unittest.TestCase):
    def test_quarantine_restore_delete(self):
        tmp = tempfile.mkdtemp(prefix="antivinux-q-")
        manager = QuarantineManager(os.path.join(tmp, "q"))
        source = os.path.join(tmp, "virus.bin")
        with open(source, "w") as fh:
            fh.write("contenido malicioso")

        entry = manager.quarantine(source, "Eicar-Test-Signature")
        self.assertIsNotNone(entry)
        self.assertEqual(len(manager.list()), 1)

        self.assertTrue(manager.restore(entry["id"]))
        self.assertEqual(len(manager.list()), 0)

        entry = manager.quarantine(source, "Otra.Firma")
        self.assertTrue(manager.delete(entry["id"]))
        self.assertEqual(len(manager.list()), 0)


class ScannerParsingTests(unittest.TestCase):
    def test_extract_findings(self):
        lines = [
            "/home/user/eicar.com: Eicar-Test-Signature FOUND\n",
            "/home/user/clean.txt: OK\n",
            "/home/user/trojan: Unix.Trojan.Agent-123 FOUND\n",
        ]
        findings = Scanner._extract_findings(lines)
        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0]["file"], "/home/user/eicar.com")
        self.assertEqual(findings[0]["signature"], "Eicar-Test-Signature")
        self.assertEqual(findings[1]["signature"], "Unix.Trojan.Agent-123")

    def test_summary_stats(self):
        blob = (
            "----------- SCAN SUMMARY -----------\n"
            "Known viruses: 8916621\n"
            "Engine version: 0.103.11\n"
            "Scanned directories: 12\n"
            "Scanned files: 345\n"
            "Infected files: 1\n"
            "Total scanned: 12.4 MB\n"
        )
        stats = Scanner._summary_stats(blob)
        self.assertEqual(stats["infected"], 1)
        self.assertEqual(stats["scanned"], 345)
        self.assertEqual(stats["scanned_dirs"], 12)
        self.assertEqual(stats["known_viruses"], "8916621")
        self.assertEqual(stats["engine"], "0.103.11")

    def test_summary_empty_blob(self):
        stats = Scanner._summary_stats("")
        self.assertEqual(stats["infected"], 0)
        self.assertIsNone(stats["scanned"])
        self.assertEqual(stats["scanned_dirs"], 0)

    def test_build_args_default(self):
        scanner = Scanner()
        args = scanner.build_args()
        self.assertIn("--no-banner", args)
        self.assertIn("--recursive", args)
        self.assertNotIn("--stdout", args)
        self.assertNotIn("--bell", args)
        self.assertNotIn("--infected", args)

    def test_count_scanned(self):
        scanner = Scanner()
        lines = [
            "/home/user/a.txt: OK\n",
            "/home/user/b.bin: Empty file\n",
            "/home/user/eicar.com: Eicar-Test-Signature FOUND\n",
            "\n",
        ]
        self.assertEqual(scanner._count_scanned(lines), 3)


class AppUpdateTests(unittest.TestCase):
    def test_parse_version(self):
        self.assertEqual(appupdate.parse_version("1.0.10"), (1, 0, 10))
        self.assertEqual(appupdate.parse_version("v1.0.10"), (1, 0, 10))
        self.assertEqual(appupdate.parse_version("1.0.2"), (1, 0, 2))

    def test_is_newer(self):
        self.assertTrue(appupdate.is_newer("1.0.10", "1.0.9"))
        self.assertTrue(appupdate.is_newer("v1.1.0", "1.0.99"))
        self.assertFalse(appupdate.is_newer("1.0.6", "1.0.6"))
        self.assertFalse(appupdate.is_newer("1.0.5", "1.0.6"))

    def test_check_for_update_never_raises(self):
        info = appupdate.check_for_update(
            current_version="9999.0.0", timeout=0.001
        )
        self.assertIn("available", info)
        self.assertFalse(info["available"])

    def test_install_package_missing_file(self):
        ok, _ = appupdate.install_package("/ruta/que/no/existe.deb")
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main(verbosity=2)