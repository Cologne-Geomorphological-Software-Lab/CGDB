"""Shared minimal .mps-format fixture content.

Used by test_mps_parser.py (parse_mps_lines unit tests), test_grainsize_fromfile.py
(GrainSize.from_file() tests), and test_admin_integration.py (admin upload
integration test) — kept in one place so the three don't drift out of sync.
"""

MINIMAL_AV = """\
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
"""
