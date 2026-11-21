"""Phase 2: conservative trapezoidal AUDPC for one *verified* time series.

Scope is 2013 Yellow rust, adult plants, KARI-Njoro Apr–May (I, J, K).
This module deliberately does NOT infer resistance, perform hypothesis tests,
combine separate fields, or interpolate incomplete/ambiguous observations.
"""
from __future__ import annotations

from datetime import date
import json
from math import isfinite
from pathlib import Path
import pandas as pd

from measurements import MEASUREMENTS

SERIES_NAME = 'Njoro Apr–May'
REQUIRED_COLUMNS = ('I', 'J', 'K')
EXPECTED_DATES = ('2013-04-21', '2013-04-30', '2013-05-07')
COLUMN_LABELS = {'I': 'apr21', 'J': 'apr30', 'K': 'may07'}
AUDPC_SOURCE = 'https://www.apsnet.org/edcenter/sites/EcologyAndEpidemiologyInR/DiseaseProgress/Pages/AUDPC.aspx'


def observation_days() -> tuple[int, ...]:
    """Check the declared source mapping to guard against silent date/series drift."""
    found = {m.column: m for m in MEASUREMENTS if m.column in REQUIRED_COLUMNS}
    if len(found) != 3:
        raise ValueError('AUDPC source columns I/J/K are incomplete.')
    for col, expected in zip(REQUIRED_COLUMNS, EXPECTED_DATES):
        m = found[col]
        if (m.date != expected or m.disease != 'Yellow rust' or
            m.site != 'KARI-Njoro' or m.stage != 'adult' or m.series != SERIES_NAME):
            raise ValueError(f'Unexpected mapping for source column {col}.')
    times = [date.fromisoformat(found[c].date) for c in REQUIRED_COLUMNS]
    return tuple((t-times[0]).days for t in times)


def trapezoid_audpc(severities, days):
    """Area in severity-percentage × days; strict complete case, no interpolation."""
    y = list(severities)
    x = list(days)
    if len(y) != len(x) or len(y) < 2:
        raise ValueError('A curve requires at least 2 matched dates and values.')
    if not all(isfinite(float(v)) and 0 <= float(v) <= 100 for v in y):
        raise ValueError('All severity values must be finite percentages 0–100.')
    if not all(isfinite(float(t)) for t in x) or any(b <= a for a,b in zip(x,x[1:])):
        raise ValueError('Observation days must be strictly increasing.')
    segments = [((float(y[i])+float(y[i+1]))/2)*(float(x[i+1])-float(x[i]))
                for i in range(len(y)-1)]
    return sum(segments), segments


def calculate_njoro_audpc(obs: pd.DataFrame, mats: pd.DataFrame):
    """Return (complete cases, excluded cases, audit summary) from phase-1 data.

    Exactly one row per material × source column is required. Unexpected
    duplicates cause an error, rather than silently skewing a pivot.
    """
    days = observation_days()
    records = obs[obs['measurement_id'].isin(REQUIRED_COLUMNS)].copy()
    if (records.duplicated(['material_id','measurement_id'])).any():
        raise ValueError('Duplicate material × measurement observations found.')
    if not records.empty:
        mismatched = (records['disease'].ne('Yellow rust') |
                      records['site'].ne('KARI-Njoro') |
                      records['stage'].ne('adult') |
                      records['series'].ne(SERIES_NAME))
        if mismatched.any():
            raise ValueError('An observation does not belong to Njoro Apr–May.')
    records['severity_pct'] = pd.to_numeric(records['severity_pct'], errors='coerce')
    records['material_id'] = records['material_id'].astype(str)
    material_table = mats.copy()
    material_table['material_id'] = material_table['material_id'].astype(str)
    if material_table['material_id'].duplicated().any():
        raise ValueError('Duplicate material IDs in master table.')
    indexed = records.set_index(['material_id','measurement_id'])
    scored = []
    excluded = []
    for mat in material_table.to_dict('records'):
        mid = mat['material_id']
        severities, invalid = [], []
        record_values = {}
        for col in REQUIRED_COLUMNS:
            key = (mid, col)
            if key not in indexed.index:
                invalid.append(f'{col}:no_source_row')
                record_values[col] = None
                continue
            entry = indexed.loc[key]
            status = str(entry['parse_status'])
            value = entry['severity_pct']
            record_values[col] = None if pd.isna(value) else float(value)
            if status != 'adult_severity' or pd.isna(value):
                invalid.append(f'{col}:{status}')
            elif not isfinite(float(value)) or not 0 <= float(value) <= 100:
                invalid.append(f'{col}:invalid_numeric')
            else:
                severities.append(float(value))
        if invalid:
            excluded.append({**mat, 'reason': '; '.join(invalid),
                             'I_raw':_source_raw(indexed,mid,'I'),
                             'J_raw':_source_raw(indexed,mid,'J'),
                             'K_raw':_source_raw(indexed,mid,'K')})
            continue
        total, areas = trapezoid_audpc(severities, days)
        scored.append({**mat, 'I_raw':_source_raw(indexed,mid,'I'),
                       'J_raw':_source_raw(indexed,mid,'J'),
                       'K_raw':_source_raw(indexed,mid,'K'),
                       'apr21_pct':severities[0], 'apr30_pct':severities[1],
                       'may07_pct':severities[2],
                       'area_apr21_apr30':areas[0], 'area_apr30_may07':areas[1],
                       'audpc_pct_days':total,
                       'time_weighted_mean_pct':total/(days[-1]-days[0])})
    complete_df = pd.DataFrame(scored)
    excluded_df = pd.DataFrame(excluded)
    summary = {
        'disease':'Yellow rust', 'site':'KARI-Njoro','series':SERIES_NAME,
        'source_columns':list(REQUIRED_COLUMNS),
        'dates':list(EXPECTED_DATES), 'days_from_first':list(days),
        'interval_days':[b-a for a,b in zip(days,days[1:])],
        'total_materials':len(material_table),
        'complete_materials':len(complete_df),
        'excluded_materials':len(excluded_df),
        'per_date_valid':{
            c:int(((records['measurement_id']==c) &
                     records['parse_status'].eq('adult_severity') &
                     records['severity_pct'].notna()).sum())
            for c in REQUIRED_COLUMNS},
        'median_audpc':None if complete_df.empty else float(complete_df['audpc_pct_days'].median()),
        'mean_audpc':None if complete_df.empty else float(complete_df['audpc_pct_days'].mean()),
        'minimum_audpc':None if complete_df.empty else float(complete_df['audpc_pct_days'].min()),
        'maximum_audpc':None if complete_df.empty else float(complete_df['audpc_pct_days'].max()),
        'note':('Descriptive trapezoidal area for complete, explicitly numeric scores only. '
                'No interpolation, p-values, heritability, multi-site stability or genetic claims.'),
        'reference':AUDPC_SOURCE,
    }
    return complete_df, excluded_df, summary


def _source_raw(indexed,mid,col):
    key = (mid,col)
    return '' if key not in indexed.index else str(indexed.loc[key]['raw_score'])


def export_audpc(obs:pd.DataFrame, mats:pd.DataFrame, directory:Path):
    complete, excluded, summary = calculate_njoro_audpc(obs,mats)
    directory.mkdir(parents=True,exist_ok=True)
    complete.to_csv(directory/'audpc_njoro_apr_may.csv', index=False,encoding='utf-8-sig')
    excluded.to_csv(directory/'audpc_excluded.csv',index=False,encoding='utf-8-sig')
    (directory/'audpc_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    return summary
