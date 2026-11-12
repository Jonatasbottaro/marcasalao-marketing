import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import srt_validate

VALID = (
    "1\n00:00:00,000 --> 00:00:04,000\nPrimeira cena.\n\n"
    "2\n00:00:04,000 --> 00:00:09,000\nSegunda cena.\n\n"
    "3\n00:00:09,000 --> 00:00:12,000\nTerceira cena.\n"
)


def codes(errors):
    return [e.split(":", 1)[0] for e in errors]


class SrtValidateTest(unittest.TestCase):
    def test_valid_passes(self):
        self.assertEqual(srt_validate.validate_srt_text(VALID, 12.0), [])

    def test_timestamp_invalid(self):
        bad = VALID.replace("00:00:04,000 --> 00:00:09,000", "00:00:74,000 --> 00:00:09,000")
        self.assertIn("SRT_TIMESTAMP_INVALID", codes(srt_validate.validate_srt_text(bad, 12.0)))

    def test_interval_invalid(self):
        bad = VALID.replace("00:00:04,000 --> 00:00:09,000", "00:00:09,000 --> 00:00:04,000")
        self.assertIn("SRT_INTERVAL_INVALID", codes(srt_validate.validate_srt_text(bad, 12.0)))

    def test_order_overlap(self):
        bad = VALID.replace("00:00:09,000 --> 00:00:12,000", "00:00:08,000 --> 00:00:12,000")
        self.assertIn("SRT_OVERLAP", codes(srt_validate.validate_srt_text(bad, 12.0)))

    def test_out_of_duration(self):
        self.assertIn("SRT_OUT_OF_DURATION", codes(srt_validate.validate_srt_text(VALID, 10.0)))

    def test_text_empty(self):
        bad = VALID.replace("Segunda cena.\n", "\n")
        self.assertIn("SRT_TEXT_EMPTY", codes(srt_validate.validate_srt_text(bad, 12.0)))

    def test_block_index(self):
        bad = VALID.replace("\n2\n", "\n7\n")
        self.assertIn("SRT_BLOCK_INDEX", codes(srt_validate.validate_srt_text(bad, 12.0)))

    def test_newline_final(self):
        self.assertIn("SRT_NEWLINE_INVALID", codes(srt_validate.validate_srt_text(VALID.rstrip("\n"), 12.0)))
        self.assertIn("SRT_NEWLINE_INVALID", codes(srt_validate.validate_srt_text(VALID + "\n", 12.0)))
        self.assertIn("SRT_NEWLINE_INVALID", codes(srt_validate.validate_srt_text(VALID.replace("\n", "\r\n"), 12.0)))

    def test_encoding(self):
        self.assertEqual(codes(srt_validate.validate_srt_bytes(VALID.encode("utf-8"), 12.0)), [])
        self.assertIn("SRT_ENCODING", codes(srt_validate.validate_srt_bytes(VALID.encode("latin-1").replace(b"cena", b"cen\xe1"), 12.0)))

    def test_empty(self):
        self.assertIn("SRT_EMPTY", codes(srt_validate.validate_srt_text("\n", 12.0)))


if __name__ == "__main__":
    unittest.main()