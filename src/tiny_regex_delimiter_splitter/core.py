"""Split strings on regex delimiters with match positions and captured groups.

Design decisions (stated plainly so behaviour is predictable):

1. Delimiter matches are excluded from the returned text segments. A match's
   start and end positions are recorded on the adjacent MatchInfo entries so
   the caller can reconstruct the original string exactly if needed.

2. Adjacent delimiter matches produce empty-text segments between them, and a
   delimiter at the very start or end of the string also produces an empty
   leading or trailing segment. This mirrors str.split's behaviour for empty
   results and keeps reconstruction (segment + match.span) lossless.

3. Zero-width delimiter matches are supported. Because finditer already
   advances past a zero-width match, each zero-width match contributes exactly
   one boundary (an empty match object) rather than an infinite loop.

4. The result is a concrete SplitResult dataclass with .text_segments and
   .delimiters lists of equal length: len(delimiters) == len(text_segments) - 1.
   A convenience .flat() iterator interleaves segments and delimiters in
   document order, which is the form most useful for reconstruction.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterator, List, Optional, Pattern


@dataclass(frozen=True)
class MatchInfo:
    """Information about a single delimiter match.

    Attributes:
        start: Index of the match's first character in the original string.
        end: Index immediately after the match's last character.
        matched_text: The exact substring the regex matched.
        groups: Tuple of captured groups, mirroring re.Match.groups().
            Unmatched optional groups appear as None, exactly as re returns.
        groupdict: Dict of named captured groups. Unmatched optional named
            groups appear as None.
    """

    start: int
    end: int
    matched_text: str
    groups: tuple
    groupdict: dict = field(default_factory=dict)

    def span(self) -> tuple:
        """Return (start, end) as a plain tuple, matching re.Match.span()."""
        return (self.start, self.end)


@dataclass(frozen=True)
class SplitSegment:
    """A single text piece produced by splitting.

    Attributes:
        text: The substring between two delimiter matches (or between a
            string boundary and the first/last delimiter).
        start: Index of the first character of this segment in the original
            string. Equal to the previous delimiter's end, or 0 for the
            first segment.
        end: Index immediately after this segment's last character.
    """

    text: str
    start: int
    end: int


@dataclass(frozen=True)
class SplitResult:
    """The complete output of a split operation.

    Invariants:
        len(delimiters) == len(text_segments) - 1
        Reconstructing: text_segments[0].text, then for each i,
            delimiters[i].matched_text followed by text_segments[i+1].text,
            yields the original string exactly.
    """

    text_segments: List[SplitSegment]
    delimiters: List[MatchInfo]

    def flat(self) -> Iterator:
        """Yield segments and delimiters interleaved in document order.

        Yields SplitSegment then MatchInfo then SplitSegment then MatchInfo
        ... ending with a SplitSegment. Useful for a straightforward
        left-to-right reconstruction or render of the original string.
        """
        yield self.text_segments[0]
        for delim, seg in zip(self.delimiters, self.text_segments[1:]):
            yield delim
            yield seg


class RegexDelimiterSplitter:
    """Splits strings on a regex delimiter, preserving match metadata.

    Args:
        pattern: A compiled regex Pattern or a string. If a string is given it
            is compiled once with re.compile. The pattern is used as-is; flags
            must be set on a pre-compiled pattern if needed.

    Raises:
        TypeError: If pattern is neither a str nor a re.Pattern.
        re.error: If pattern is a string that is not valid regex.

    Example:
        >>> splitter = RegexDelimiterSplitter(r"[,;]")
        >>> result = splitter.split("a,b;c")
        >>> [s.text for s in result.text_segments]
        ['a', 'b', 'c']
        >>> [(d.matched_text, d.start, d.end) for d in result.delimiters]
        [(',', 1, 2), (';', 3, 4)]
    """

    def __init__(self, pattern):
        if isinstance(pattern, str):
            pattern = re.compile(pattern)
        elif not isinstance(pattern, Pattern):
            raise TypeError(
                "pattern must be a str or a compiled re.Pattern, got %r" % type(pattern)
            )
        # Store the compiled pattern. Using finditer over findall/scanner gives
        # us both positions and captured groups in a single pass.
        self._pattern = pattern

    @property
    def pattern(self):
        """The compiled regex Pattern this splitter uses."""
        return self._pattern

    def split(self, text):
        """Split *text* on this splitter's delimiter pattern.

        Args:
            text: The string to split.

        Returns:
            A SplitResult. See its docstring for the structural invariants.

        Notes:
            - Delimiter text is excluded from segments; use result.delimiters
              to recover it along with positions and groups.
            - Zero-width matches are handled without infinite looping because
              re.finditer advances past them automatically.
            - An input with no matches returns a single segment spanning the
              whole string, with an empty delimiters list.
        """
        text_segments: List[SplitSegment] = []
        delimiters: List[MatchInfo] = []
        cursor = 0

        for m in self._pattern.finditer(text):
            # Segment between the previous delimiter (or string start) and this match.
            segment_text = text[cursor:m.start()]
            text_segments.append(
                SplitSegment(text=segment_text, start=cursor, end=m.start())
            )

            delimiters.append(
                MatchInfo(
                    start=m.start(),
                    end=m.end(),
                    matched_text=m.group(0),
                    groups=m.groups(),
                    groupdict=m.groupdict(),
                )
            )
            cursor = m.end()

        # Final trailing segment (always present, possibly empty).
        text_segments.append(
            SplitSegment(text=text[cursor:], start=cursor, end=len(text))
        )

        return SplitResult(text_segments=text_segments, delimiters=delimiters)
