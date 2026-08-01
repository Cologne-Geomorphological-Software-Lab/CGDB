"""Tests for analysis.mps_parser — pure functions, no Django/DB dependency."""

from __future__ import annotations

from analysis.mps_parser import STATS_KEY_MAP, parse_block_line, parse_mps_lines

MINIMAL_LINES = """\
[#Bindiam]
10.0
20.0
[#Binheight]
50.0
50.0
[Size0]
Obs=150.5
[SizeStats]
Mean=15.0
Mode=12.0
Median=14.0
SD=3.5
Skew=0.2
Kurtosis=2.8
FWMean=15.1
FWMedian=14.2
FWSD=3.6
FWSkew=0.3
FWKurt=2.9
""".splitlines()


def test_parse_mps_lines_extracts_classes_and_measured_data() -> None:
    """[#Bindiam]/[#Binheight] blocks become classes/measured_data lists."""
    result = parse_mps_lines(MINIMAL_LINES)
    assert result["classes"] == [10.0, 20.0]
    assert result["measured_data"] == [50.0, 50.0]


def test_parse_mps_lines_extracts_concentration() -> None:
    """Obs= lines inside Size0/Size1/Size2 blocks feed concentration."""
    result = parse_mps_lines(MINIMAL_LINES)
    assert result["concentration"] == [150.5]


def test_parse_mps_lines_extracts_stats_block() -> None:
    """[SizeStats] key=value lines map to their model field names."""
    result = parse_mps_lines(MINIMAL_LINES)
    for mps_key, field_name in STATS_KEY_MAP.items():
        assert result[field_name] is not None, f"missing {mps_key} -> {field_name}"
    assert result["mean"] == 15.0
    assert result["fwkurt"] == 2.9


def test_parse_mps_lines_ignores_unrecognized_blocks() -> None:
    """Lines outside any known block are silently ignored, not an error."""
    lines = ["[SomeOtherBlock]", "garbage line", "[#Bindiam]", "5.0"]
    result = parse_mps_lines(lines)
    assert result["classes"] == [5.0]


def test_parse_mps_lines_skips_unparseable_numeric_values() -> None:
    """A non-numeric value in a #Bindiam/#Binheight block is dropped, not raised."""
    lines = ["[#Bindiam]", "not-a-number", "10.0"]
    result = parse_mps_lines(lines)
    assert result["classes"] == [10.0]


def test_parse_block_line_size_block_ignores_non_obs_keys() -> None:
    """Only the Obs= key inside a Size0/1/2 block feeds concentration."""
    state = {"classes": [], "measured_data": [], "concentration": [], "stats": {}}
    parse_block_line("SomeOtherKey=1.0", "Size1", state)
    assert state["concentration"] == []
    parse_block_line("Obs=42.0", "Size1", state)
    assert state["concentration"] == [42.0]


def test_parse_block_line_none_block_is_noop() -> None:
    """A data line encountered before any [Block] header does nothing."""
    state = {"classes": [], "measured_data": [], "concentration": [], "stats": {}}
    parse_block_line("10.0", None, state)
    assert state == {"classes": [], "measured_data": [], "concentration": [], "stats": {}}
