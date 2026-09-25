import hashlib
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "services" / "public-identity" / "pwned_passwords.py"

spec = importlib.util.spec_from_file_location("ordax_pwned_passwords", MODULE)
checker_module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = checker_module
spec.loader.exec_module(checker_module)


class FakeTransport:
    def __init__(self, status=200, body=b""):
        self.status = status
        self.body = body
        self.calls = []

    def request(self, url, headers):
        self.calls.append((url, dict(headers)))
        return self.status, self.body


class PwnedPasswordCheckerTests(unittest.TestCase):
    def test_range_query_sends_only_five_character_prefix_with_padding(self):
        password = "correct horse battery staple"
        digest = hashlib.sha1(
            password.encode("utf-8"),
            usedforsecurity=False,
        ).hexdigest().upper()
        transport = FakeTransport(
            body=(f"{digest[5:]}:17\r\n" + ("0" * 35) + ":0\r\n").encode("ascii")
        )
        checker = checker_module.PwnedPasswordChecker(transport=transport)

        self.assertEqual(checker.compromised_count(password), 17)

        url, headers = transport.calls[0]
        self.assertEqual(url, f"https://api.pwnedpasswords.com/range/{digest[:5]}")
        self.assertNotIn(password, url)
        self.assertNotIn(digest, url)
        self.assertEqual(headers["Add-Padding"], "true")
        self.assertEqual(headers["Accept"], "text/plain")
        self.assertIn("OrdaX", headers["User-Agent"])

    def test_padding_entries_and_missing_suffix_are_not_compromised(self):
        password = "unique ordax password value"
        digest = hashlib.sha1(
            password.encode("utf-8"),
            usedforsecurity=False,
        ).hexdigest().upper()
        body = (
            ("A" * 35) + ":0\r\n"
            + ("B" * 35) + ":42\r\n"
        ).encode("ascii")
        transport = FakeTransport(body=body)
        checker = checker_module.PwnedPasswordChecker(transport=transport)

        self.assertFalse(checker.is_compromised(password))
        self.assertNotIn(digest[5:].encode("ascii"), body)

    def test_non_200_and_invalid_matching_count_fail_closed(self):
        checker = checker_module.PwnedPasswordChecker(
            transport=FakeTransport(status=503, body=b"unavailable")
        )
        with self.assertRaises(checker_module.PwnedPasswordsError):
            checker.is_compromised("safe-enough-password")

        password = "another candidate password"
        digest = hashlib.sha1(
            password.encode("utf-8"),
            usedforsecurity=False,
        ).hexdigest().upper()
        checker = checker_module.PwnedPasswordChecker(
            transport=FakeTransport(body=f"{digest[5:]}:not-a-number\r\n".encode("ascii"))
        )
        with self.assertRaises(checker_module.PwnedPasswordsError):
            checker.is_compromised(password)

    def test_invalid_password_is_rejected_without_network(self):
        transport = FakeTransport()
        checker = checker_module.PwnedPasswordChecker(transport=transport)
        for password in ("", "bad\x00password"):
            with self.subTest(password=password):
                with self.assertRaises(ValueError):
                    checker.is_compromised(password)
        self.assertEqual(transport.calls, [])


if __name__ == "__main__":
    unittest.main()
