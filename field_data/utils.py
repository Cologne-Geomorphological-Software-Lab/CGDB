"""Utility helpers for the field_data app."""

from __future__ import annotations

from urllib.parse import parse_qs


def extract_sample_pk_from_get(get_params: dict) -> str | None:
    """Return sample PK string from GET params, or None.

    Checks ``?sample=``, ``?sample__id__exact=``, and the encoded
    ``?_changelist_filters=sample__id__exact%3D…`` pattern that Django
    appends when clicking "Add" from a filtered changelist.
    """
    for param in ("sample", "sample__id__exact"):
        val = get_params.get(param, "")
        if val.isdigit():
            return val

    cl_filters = get_params.get("_changelist_filters", "")
    if cl_filters:
        params = parse_qs(cl_filters)
        pk_list = params.get("sample__id__exact", [])
        if pk_list and pk_list[0].isdigit():
            return pk_list[0]

    return None
