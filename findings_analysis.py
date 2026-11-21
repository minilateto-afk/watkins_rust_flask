"""Phase 3: matched descriptive trends, AUDPC ambiguity, exploratory selection.

No hypothesis tests or genetic inference. Everything is derived from Phase 2
complete-case AUDPC data; source I/J/K scores remain linked by material ID.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

VALUE_COLUMNS = ('apr21_pct', 'apr30_pct', 'may07_pct')
DATES = ('2013-04-21', '2013-04-30', '2013-05-07')
DAYS = (0, 9, 16)
PAIR_IDS = ('43', '436')
PERCENTILES = (5, 10, 20, 25)


def check_complete_cases(df: pd.DataFrame) -> pd.DataFrame:
    """Require one row per material, complete 0–100% and verified AUDPC."""
    columns = {'material_id', 'audpc_pct_days', *VALUE_COLUMNS}
    if not columns.issubset(df.columns):
        raise ValueError(f'Missing required columns: {columns - set(df.columns)}')
    result = df.copy()
    result['material_id'] = result['material_id'].astype(str)
    if result['material_id'].duplicated().any() or result.empty:
        raise ValueError('Complete-case table must have unique material IDs and >=1 row.')
    for column in (*VALUE_COLUMNS, 'audpc_pct_days'):
        result[column] = pd.to_numeric(result[column], errors='raise')
        if not np.isfinite(result[column]).all():
            raise ValueError(f'Nonfinite value in {column}')
    for col in VALUE_COLUMNS:
        if not result[col].between(0, 100).all():
            raise ValueError(f'Out-of-range severity in {col}')
    expected = (result['apr21_pct'] + result['apr30_pct']) * 9 / 2 + (result['apr30_pct'] + result['may07_pct']) * 7 / 2
    if not np.allclose(result['audpc_pct_days'], expected, atol=1e-9, rtol=0):
        raise ValueError('AUDPC does not match source scores and time intervals.')
    return result


def build_findings(good: pd.DataFrame):
    """Return per-material results and summary computed on SAME complete-case set."""
    df = check_complete_cases(good)
    df['delta_16d_pct_points'] = df['may07_pct'] - df['apr21_pct']
    df['delta_first_interval_pp'] = df['apr30_pct'] - df['apr21_pct']
    df['delta_second_interval_pp'] = df['may07_pct'] - df['apr30_pct']
    df['change_class'] = np.select([df['delta_16d_pct_points'] > 0,
                                    df['delta_16d_pct_points'] < 0],
                                   ['增加', '下降'], default='不變')
    grouped = df['change_class'].value_counts().to_dict()
    dates = []
    for col, name, day in zip(VALUE_COLUMNS, DATES, DAYS):
        vals = df[col]
        dates.append({'date':name, 'day':day, 'n':len(vals),
                      'mean':float(vals.mean()), 'median':float(vals.median()),
                      'std_sample':float(vals.std(ddof=1)),
                      'q1':float(vals.quantile(.25)), 'q3':float(vals.quantile(.75))})
    pair = df[df.material_id.isin(PAIR_IDS)].set_index('material_id')
    if set(pair.index) != set(PAIR_IDS):
        raise ValueError('The two documented real-source comparison records are missing.')
    one, two = pair.loc[PAIR_IDS[0]], pair.loc[PAIR_IDS[1]]
    if not np.isclose(one.audpc_pct_days, two.audpc_pct_days, atol=1e-9) or \
       all(one[k] == two[k] for k in VALUE_COLUMNS):
        raise ValueError('Real-source same-AUDPC / different-curve example is invalid.')
    summary = {
        'scope': '2013 Yellow rust, KARI-Njoro, columns I/J/K, same 490 complete cases',
        'source_columns': ['I', 'J', 'K'], 'dates':list(DATES), 'day_offsets':list(DAYS),
        'complete_count':int(len(df)),
        'dates_stats':dates,
        'direction_counts':{k:int(grouped.get(k,0)) for k in ('增加','不變','下降')},
        'delta_mean_pp':float(df.delta_16d_pct_points.mean()),
        'delta_median_pp':float(df.delta_16d_pct_points.median()),
        'audpc_median':float(df.audpc_pct_days.median()),
        'pair_ids':list(PAIR_IDS), 'pair_audpc':float(one.audpc_pct_days),
        'observation_note': 'Descriptive results on complete cases only: no significance test, resistance gene or causal claims.',
        'screening_note': 'Exploratory low-AUDPC subset, not validated resistant germplasm. Include all ties at threshold.'
    }
    return df, summary


def select_low_audpc(df: pd.DataFrame, percentile: int = 10):
    """Empirical percentile with linear quantile and all threshold ties retained."""
    if percentile not in PERCENTILES:
        raise ValueError('Unsupported percentile; use 5, 10, 20 or 25.')
    df = check_complete_cases(df)
    threshold = float(df['audpc_pct_days'].quantile(percentile / 100.0))
    selected = df[df['audpc_pct_days'] <= threshold + 1e-9].copy()
    selected['material_id_num'] = pd.to_numeric(selected['material_id'], errors='coerce')
    selected = selected.sort_values(['audpc_pct_days','material_id_num', 'material_id'],kind='stable')
    selected = selected.drop(columns=['material_id_num'])
    return selected, {'percentile':percentile, 'cutoff':threshold,
                      'total':len(df),'selected':len(selected),'nominal':int(np.ceil(len(df)*percentile/100)),
                      'ties_included':True}


def export_findings(good: pd.DataFrame, directory: Path):
    details, summary = build_findings(good)
    directory.mkdir(parents=True,exist_ok=True)
    details.to_csv(directory / 'findings_matched_490.csv', index=False, encoding='utf-8-sig')
    for p in PERCENTILES:
        cohort, cut = select_low_audpc(details, p)
        summary[f'low_{p}_percent'] = cut
        if p == 10:
            cohort.to_csv(directory / 'low_audpc_p10_exploratory.csv', index=False, encoding='utf-8-sig')
    (directory/'findings_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    return summary
