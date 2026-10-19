# tiny-regex-delimiter-splitter

Splits strings on regex patterns while keeping track of match positions and captured groups.

```python
from tiny_regex_delimiter_splitter import RegexDelimiterSplitter

splitter = RegexDelimiterSplitter(r"(?P<key>\w+)=(?P<val>\d+)")
result = splitter.split("a=1,b=2")

for seg in result.text_segments:
    print(repr(seg.text), seg.start, seg.end)

for delim in result.delimiters:
    print(delim.matched_text, delim.span(), delim.groupdict)
```

The exported names are `RegexDelimiterSplitter`, `SplitSegment`, and `SplitResult` (plus `MatchInfo` from `tiny_regex_delimiter_splitter.core`).

## Why this exists

`re.split` discards the matched delimiter text by default and, when captured groups are
present, interleaves them into the result list in a way that makes positional reasoning
awkward. When you need to know *where* each delimiter matched and *what* each capture
group held — for example, to reconstruct the original string with substitutions applied
only to delimiters — a flat list is the wrong shape.

This library returns a `SplitResult` with two parallel structures: `text_segments` (the
pieces between delimiters) and `delimiters` (the matches themselves, with `start`, `end`,
`matched_text`, `groups`, and `groupdict`). The invariant `len(delimiters) ==
len(text_segments) - 1` always holds, so reconstruction is a simple zip. A `flat()`
iterator is provided for left-to-right traversal.

Delimiter text is excluded from segments by design. If a match is zero-width (e.g.
`\b`), each boundary still produces exactly one delimiter entry and the adjacent
segments reflect the gap (possibly empty) around it. `re.finditer` advances past
zero-width matches, so there is no infinite loop.

## Edge you will hit

A delimiter at the very start or end of the string produces an empty leading or trailing
segment, and adjacent delimiters produce empty segments between them. This is deliberate:
it keeps `segment.text + delimiter.matched_text` reconstruction lossless. If you want to
drop empty segments, filter `result.text_segments` yourself — the library does not guess.
