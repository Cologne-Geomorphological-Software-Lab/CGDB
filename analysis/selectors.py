"""Read-only queries analysis exposes for other apps to consume.

Architecture-review fix (F21): field_data's LocationViewSet.map (see
field_data/api_views.py) needs per-location measurement counts, but used to
get them by importing analysis.models directly (`from analysis.models
import GrainSize, LuminescenceDating`) — field_data is meant to be the
lower-level hub analysis builds on top of, so a Location-facing API
reaching into analysis's own model classes inverted that layering. This
module is the stable surface field_data imports from instead: adding a new
measurement type to this dict is the only change needed here when one is
added, without field_data/api_views.py having to change at all.
"""

from __future__ import annotations

from .models import GrainSize, LuminescenceDating

# name -> (model, lookup path back to Location). Consumers annotate a
# per-Location count for each entry (e.g. via a correlated Subquery), keyed
# by the given name.
LOCATION_MEASUREMENT_COUNTS = {
    "luminescence_count": (LuminescenceDating, "sample__location"),
    "grain_size_count": (GrainSize, "sample__location"),
}
