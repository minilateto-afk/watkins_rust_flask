"""Consistent, conservative material lookup across all Flask views.

Material identifiers are strings from the source workbook. Search never alters
quantitative observations and never substitutes a different material for an
unknown identifier.
"""
from __future__ import annotations
import re
import unicodedata
import pandas as pd

SEARCH_COLS = ('material_id', 'accession', 'accession_name', 'country')


def normalize_query(query: str, max_length: int = 100) -> str:
    """Normalize fullwidth digits, Unicode whitespace and accidental padding."""
    return ' '.join(unicodedata.normalize('NFKC', str(query or '')).strip().split())[:max_length]


def search_materials(df: pd.DataFrame, query: str) -> pd.DataFrame:
    """Find an Excel serial, accession number, cultivar or origin without regex.

    Exact material/accession matches lead the results; partial matches remain
    available. All returned rows retain their source identifiers.
    """
    query = normalize_query(query)
    if not query:
        return df.copy()
    parts = []
    for col in SEARCH_COLS:
        if col in df.columns:
            parts.append(df[col].fillna('').astype(str).str.contains(query, case=False, regex=False))
    if not parts:
        return df.iloc[:0].copy()
    mask = parts[0]
    for part in parts[1:]:
        mask = mask | part
    output = df.loc[mask].copy()
    if not output.empty:
        output['_match_priority'] = 2
        for col in ('material_id','accession'):
            if col in output.columns:
                match = output[col].astype(str).str.casefold().eq(query.casefold())
                output.loc[match,'_match_priority'] = 0
        for col in ('accession_name','country'):
            if col in output.columns:
                match = output[col].astype(str).str.casefold().eq(query.casefold())
                output.loc[match,'_match_priority'] = output.loc[match,'_match_priority'].clip(upper=1)
        output['_row_order'] = range(len(output))
        output = output.sort_values(['_match_priority','_row_order'],kind='stable')
        output = output.drop(columns=['_match_priority','_row_order'])
    return output


def resolve_material_ids(df: pd.DataFrame, raw: str, max_items: int = 4):
    """Resolve exact Excel serials / exact accession codes for curve comparison.

    Unrecognized tokens are reported rather than silently ignored. This
    prevents showing unrelated study subjects in response to a failed lookup.
    """
    raw = unicodedata.normalize('NFKC', str(raw or '')).replace('，', ',').replace('、', ',')
    tokens = list(dict.fromkeys(p.strip() for p in re.split(r'[,;；\n]+', raw) if p.strip()))[:max_items]
    resolved, unknown = [], []
    for token in tokens:
        exact = df[(df.material_id.astype(str).str.casefold() == token.casefold()) |
                   (df.accession.astype(str).str.casefold() == token.casefold())]
        if exact.empty:
            unknown.append(token)
        else:
            mid = str(exact.iloc[0]['material_id'])
            if mid not in resolved:
                resolved.append(mid)
    return resolved, unknown
