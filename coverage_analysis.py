"""Phase 4: accountable quantitative coverage of ALL 650 material records.

'Included in the inventory' is not the same as 'has numerical disease data'.
This module never imputes missing values or pools distinct disease/site/stage
measurements into a made-up resistance score.
"""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

NUMERIC_STATUSES = {'adult_severity', 'seedling_score'}
REQUIRED_COLUMNS = {'I', 'J', 'K'}
GROUP_LABELS = {
    'complete_ijk': 'Njoro 三次完整觀測（可計算本系列 AUDPC）',
    'other_numeric': '其他觀測仍有數值（不能計算本系列 AUDPC）',
    'no_numeric': '無可直接解析的數值評分'
}


def build_coverage(obs: pd.DataFrame, mats: pd.DataFrame, audited_audpc: pd.DataFrame):
    """Return one row per material and a transparent numeric-coverage summary."""
    if mats.material_id.astype(str).duplicated().any():
        raise ValueError('主表材料 ID 重複')
    if obs.duplicated(['material_id','measurement_id']).any():
        raise ValueError('觀測資料出現材料與欄位重複')
    expected = set(mats.material_id.astype(str))
    if set(obs.material_id.astype(str)) != expected:
        raise ValueError('觀測表與材料表的材料集合不一致')
    n_per = obs.groupby('material_id').size()
    if n_per.nunique() != 1 or int(n_per.iloc[0]) != 29:
        raise ValueError('每個材料應有 29 筆來源觀測欄位')
    rows=[]
    audpc_ids=set(audited_audpc.material_id.astype(str))
    for mat in mats.to_dict('records'):
        mid=str(mat['material_id'])
        records=obs[obs.material_id.astype(str)==mid]
        numeric = records[records.parse_status.isin(NUMERIC_STATUSES)]
        adult = records[records.parse_status.eq('adult_severity')]
        seedling=records[records.parse_status.eq('seedling_score')]
        ijk=records[records.measurement_id.isin(REQUIRED_COLUMNS)]
        ijk_count=int(ijk.parse_status.eq('adult_severity').sum())
        valid_count=int(len(numeric))
        if ijk_count==3:
            label='complete_ijk'
        elif valid_count>0:
            label='other_numeric'
        else:
            label='no_numeric'
        if (label=='complete_ijk') != (mid in audpc_ids):
            raise ValueError(f'完整時間曲線資格與 AUDPC 清單不一致：{mid}')
        rows.append({
            **mat, 'numeric_count':valid_count,
            'numeric_coverage_pct':round(valid_count/29*100,2),
            'adult_numeric_count':len(adult), 'seedling_numeric_count':len(seedling),
            'yellow_adult_count':int(adult.disease.eq('Yellow rust').sum()),
            'stem_adult_count':int(adult.disease.eq('Stem rust').sum()),
            'leaf_adult_count':int(adult.disease.eq('Leaf rust').sum()),
            'njoro_ijk_valid_count':ijk_count,
            'trace_count':int(records.parse_status.eq('trace_not_quantified').sum()),
            'range_count':int(records.parse_status.eq('range_or_interval').sum()),
            'missing_count':int(records.parse_status.isin(['blank','missing_marker']).sum()),
            'other_unclear_count':int(records.parse_status.isin(['special_note','unparsed','out_of_range','unverified_seedling']).sum()),
            'coverage_group':label,
            'coverage_label':GROUP_LABELS[label],
        })
    result=pd.DataFrame(rows)
    # Do not calculate an average of incompatible severity/seedling scales or sites.
    total=int(len(result))
    summary={
      'total':total,
      'all_29_measurement_cells':total*29,
      'complete_ijk':int((result.coverage_group=='complete_ijk').sum()),
      'other_numeric':int((result.coverage_group=='other_numeric').sum()),
      'no_numeric':int((result.coverage_group=='no_numeric').sum()),
      'any_numeric':int((result.numeric_count>0).sum()),
      'ijk_valid_distribution':{str(k):int(v) for k,v in result.njoro_ijk_valid_count.value_counts().sort_index().items()},
      'any_yellow_adult':int((result.yellow_adult_count>0).sum()),
      'any_stem_adult':int((result.stem_adult_count>0).sum()),
      'any_leaf_adult':int((result.leaf_adult_count>0).sum()),
      'adult_numeric_entries':int(result.adult_numeric_count.sum()),
      'seedling_numeric_entries':int(result.seedling_numeric_count.sum()),
      'method_note':'每筆材料 29 個來源觀測格；僅計入可明確解析的成株期病害嚴重度與幼苗期原始數字評分，兩者不混算。缺失值未補值；跨地點/疾病/日期不合併成單一抗病分數。'
    }
    if sum(summary[k] for k in ('complete_ijk','other_numeric','no_numeric'))!=total:
        raise ValueError('涵蓋分類不能完整覆蓋材料清單')
    return result,summary


def export_coverage(obs:pd.DataFrame,mats:pd.DataFrame,audpc:pd.DataFrame,directory:Path):
    table,overview=build_coverage(obs,mats,audpc)
    directory.mkdir(parents=True,exist_ok=True)
    table.to_csv(directory/'coverage_all_650.csv',index=False,encoding='utf-8-sig')
    (directory/'coverage_summary.json').write_text(json.dumps(overview,ensure_ascii=False,indent=2),encoding='utf-8')
    return overview
