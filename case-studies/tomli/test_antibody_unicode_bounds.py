# Antibody for tomli (T3 x T4): escaped code points must be validated at every
# boundary of the Unicode scalar value range, and invalid ones must raise
# TOMLDecodeError, never a raw ValueError. Found by Bug Vaccine: tomli's suite
# did not notice when the upper bound was moved by one (control mutant C3).
#
# To use: copy into tomli's tests/ folder.
import unittest

import tomli


class TestUnicodeEscapeBounds(unittest.TestCase):
    VALID = [0x0, 0xD7FF, 0xE000, 0x10FFFF]
    INVALID = [0xD800, 0xDFFF, 0x110000, 0xFFFFFFFF]

    def test_valid_boundaries_decode(self):
        for cp in self.VALID:
            with self.subTest(codepoint=hex(cp)):
                doc = f'a = "\\U{cp:08X}"'
                self.assertEqual(tomli.loads(doc)["a"], chr(cp))

    def test_invalid_boundaries_raise_toml_error(self):
        for cp in self.INVALID:
            for doc in (f'a = "\\U{cp:08X}"',) + ((f'a = "\\u{cp:04X}"',) if cp <= 0xFFFF else ()):
                with self.subTest(doc=doc):
                    with self.assertRaises(tomli.TOMLDecodeError):
                        tomli.loads(doc)
