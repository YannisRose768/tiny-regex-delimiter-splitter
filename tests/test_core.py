import unittest

from tiny_regex_delimiter_splitter import (
    RegexDelimiterSplitter,
    SplitSegment,
    SplitResult,
)
from tiny_regex_delimiter_splitter.core import MatchInfo


class TestBasicSplit(unittest.TestCase):
    def test_single_char_delimiter(self):
        splitter = RegexDelimiterSplitter(",")
        result = splitter.split("a,b,c")
        self.assertEqual([s.text for s in result.text_segments], ["a", "b", "c"])
        self.assertEqual([d.matched_text for d in result.delimiters], [",", ","])

    def test_no_match_returns_single_segment(self):
        splitter = RegexDelimiterSplitter("\\d+")
        result = splitter.split("no digits here")
        self.assertEqual(len(result.text_segments), 1)
        self.assertEqual(result.text_segments[0].text, "no digits here")
        self.assertEqual(result.delimiters, [])

    def test_empty_string(self):
        splitter = RegexDelimiterSplitter(",")
        result = splitter.split("")
        self.assertEqual(len(result.text_segments), 1)
        self.assertEqual(result.text_segments[0].text, "")
        self.assertEqual(result.delimiters, [])


class TestPositionsAndReconstruction(unittest.TestCase):
    def _reconstruct(self, result):
        parts = []
        for item in result.flat():
            if isinstance(item, SplitSegment):
                parts.append(item.text)
            else:
                parts.append(item.matched_text)
        return "".join(parts)

    def test_reconstruction_matches_original(self):
        original = "alpha,beta;gamma,delta"
        splitter = RegexDelimiterSplitter("[,;]")
        result = splitter.split(original)
        self.assertEqual(self._reconstruct(result), original)

    def test_segment_spans_are_correct(self):
        splitter = RegexDelimiterSplitter(",")
        result = splitter.split("a,b,c")
        spans = [(s.start, s.end) for s in result.text_segments]
        self.assertEqual(spans, [(0, 1), (2, 3), (4, 5)])

    def test_delimiter_spans_are_correct(self):
        splitter = RegexDelimiterSplitter(",")
        result = splitter.split("a,b,c")
        spans = [d.span() for d in result.delimiters]
        self.assertEqual(spans, [(1, 2), (3, 4)])


class TestEdgeCases(unittest.TestCase):
    def test_leading_delimiter_produces_empty_leading_segment(self):
        splitter = RegexDelimiterSplitter(",")
        result = splitter.split(",a,b")
        self.assertEqual([s.text for s in result.text_segments], ["", "a", "b"])

    def test_trailing_delimiter_produces_empty_trailing_segment(self):
        splitter = RegexDelimiterSplitter(",")
        result = splitter.split("a,b,")
        self.assertEqual([s.text for s in result.text_segments], ["a", "b", ""])

    def test_adjacent_delimiters_produce_empty_segment(self):
        splitter = RegexDelimiterSplitter(",")
        result = splitter.split("a,,b")
        self.assertEqual([s.text for s in result.text_segments], ["a", "", "b"])

    def test_multi_char_delimiter(self):
        splitter = RegexDelimiterSplitter("--")
        result = splitter.split("a--b--c")
        self.assertEqual([s.text for s in result.text_segments], ["a", "b", "c"])
        self.assertEqual([d.matched_text for d in result.delimiters], ["--", "--"])
        self.assertEqual(result.delimiters[0].span(), (1, 3))

    def test_zero_width_match_does_not_loop(self):
        # A zero-width assertion (word boundary) must not hang. finditer
        # advances past zero-width matches, so this terminates and produces
        # one boundary per word-boundary hit.
        splitter = RegexDelimiterSplitter(r"\b")
        result = splitter.split("ab cd")
        # Every word boundary is a delimiter; segments between them are kept.
        # Boundaries in "ab cd": before 'a', after 'b', before 'c', after 'd'.
        self.assertEqual([s.text for s in result.text_segments], ["", "ab", " ", "cd", ""])
        self.assertEqual(len(result.delimiters), 4)
        self.assertTrue(all(d.start == d.end for d in result.delimiters))


class TestCapturedGroups(unittest.TestCase):
    def test_unnamed_groups(self):
        splitter = RegexDelimiterSplitter(r"(\w)=(\d)")
        result = splitter.split("x=1,y=2")
        self.assertEqual([s.text for s in result.text_segments], ["", ",", ""])
        self.assertEqual(result.delimiters[0].groups, ("x", "1"))
        self.assertEqual(result.delimiters[1].groups, ("y", "2"))

    def test_named_groups(self):
        splitter = RegexDelimiterSplitter(r"(?P<key>\w+):(?P<val>\d+)")
        result = splitter.split("a:1,b:2")
        self.assertEqual(result.delimiters[0].groupdict, {"key": "a", "val": "1"})
        self.assertEqual(result.delimiters[1].groupdict, {"key": "b", "val": "2"})

    def test_unmatched_optional_group_is_none(self):
        splitter = RegexDelimiterSplitter(r"(\d)?-")
        result = splitter.split("1-,-")
        self.assertEqual(result.delimiters[0].groups, ("1",))
        self.assertEqual(result.delimiters[1].groups, (None,))


class TestCompiledPattern(unittest.TestCase):
    def test_accepts_precompiled_pattern(self):
        import re

        splitter = RegexDelimiterSplitter(re.compile("[,;]"))
        result = splitter.split("a,b;c")
        self.assertEqual([s.text for s in result.text_segments], ["a", "b", "c"])

    def test_rejects_non_pattern_non_string(self):
        with self.assertRaises(TypeError):
            RegexDelimiterSplitter(123)


class TestFlatIterator(unittest.TestCase):
    def test_flat_interleaves_segments_and_delimiters(self):
        splitter = RegexDelimiterSplitter(",")
        result = splitter.split("a,b")
        items = list(result.flat())
        # Exactly: segment, delimiter, segment.
        self.assertEqual(len(items), 3)
        self.assertIsInstance(items[0], SplitSegment)
        self.assertIsInstance(items[1], MatchInfo)
        self.assertIsInstance(items[2], SplitSegment)

    def test_no_match_flat_is_single_segment(self):
        splitter = RegexDelimiterSplitter("\\d+")
        result = splitter.split("abc")
        items = list(result.flat())
        self.assertEqual(len(items), 1)
        self.assertIsInstance(items[0], SplitSegment)


if __name__ == "__main__":
    unittest.main()
