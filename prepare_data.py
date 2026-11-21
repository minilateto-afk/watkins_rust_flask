"""Reproducible, conservative ETL for Watkins rust Excel.

Usage:
  python prepare_data.py
  python prepare_data.py --source path/to/downloaded.xlsx

Never assigns numeric severity to TMS / TR / 0-20MSS / DRY / SUSC.
Preserves every raw measurement and its source Excel column.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from typing import Any
import pandas as pd
from measurements import MEASUREMENTS, as_records
from audpc_analysis import export_audpc, calculate_njoro_audpc
from findings_analysis import export_findings
from coverage_analysis import export_coverage

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'data/raw/Watkins.xlsx'
OUTPUT = ROOT / 'data/processed'
NUMERIC_RE = re.compile(r'^(\d{1,3}(?:\.\d+)?)\s*([A-Za-z]+)?$')
TRACE_RE = re.compile(r'^T[A-Za-z]*$')
MISSING = {'-', '--', '---', ';', 'NA', 'N/A', 'NAN', '.'}

def col_to_index(col: str) -> int:
    n = 0
    for letter in col:
        n = n * 26 + ord(letter.upper()) - ord('A') + 1
    return n - 1

def clean_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ''
    if isinstance(value, (int, float)) and float(value).is_integer():
        return str(int(value))
    return str(value).strip()

def parse_score(raw_value: Any, stage: str) -> dict:
    raw = clean_text(raw_value)
    result = {'raw_score':raw, 'severity_pct':None, 'seedling_score':None,
              'reaction':None, 'parse_status':None}
    if not raw:
        result['parse_status'] = 'blank'; return result
    if raw.upper() in MISSING:
        result['parse_status'] = 'missing_marker'; return result
    if '-' in raw:
        result['parse_status'] = 'range_or_interval'; return result
    if TRACE_RE.fullmatch(raw):
        result['parse_status'] = 'trace_not_quantified'; return result
    match = NUMERIC_RE.fullmatch(raw)
    if match:
        number = float(match.group(1))
        suffix = (match.group(2) or '').upper()
        if stage == 'seedling':
            # Seedling scale is not percent severity. Preserve numeric score separately.
            if 0 <= number <= 9 and not suffix:
                result['seedling_score'] = number
                result['parse_status'] = 'seedling_score'; return result
            result['parse_status'] = 'unverified_seedling'; return result
        if 0 <= number <= 100:
            result['severity_pct'] = number
            result['reaction'] = suffix or None
            result['parse_status'] = 'adult_severity'; return result
        result['parse_status'] = 'out_of_range'; return result
    if raw.upper() in {'DRY','SUSC'}:
        result['parse_status'] = 'special_note'; return result
    result['parse_status'] = 'unparsed'; return result

def build_from_rows(rows: list[list[Any]]) -> tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame,pd.DataFrame]:
    assert len(rows) >= 4 and len(rows[0]) >= 41
    records = []
    materials = []
    for excel_row, row in enumerate(rows[3:],start=4):
        if len(row)<41: row=list(row)+[None]*(41-len(row))
        row_id = clean_text(row[1])
        if not row_id.isdigit(): continue
        mat = {'material_id':row_id, 'accession':clean_text(row[0]),
               'country':clean_text(row[2]), 'accession_name':clean_text(row[3]),
               'excel_row':excel_row}
        materials.append(mat)
        for m in MEASUREMENTS:
            parsed = parse_score(row[col_to_index(m.column)],m.stage)
            records.append({**mat,'measurement_id':m.column,'disease':m.disease,
                            'site':m.site,'stage':m.stage,'series':m.series,
                            'date':m.date,'date_label':m.label,'source_column':m.column,
                            **parsed})
    obs=pd.DataFrame(records)
    mats=pd.DataFrame(materials)
    definitions=pd.DataFrame(as_records())
    summary=(obs.groupby(['measurement_id','disease','site','stage','series','date'],dropna=False)
             .agg(total=('material_id','size'),numerical_adult=('parse_status',lambda s:(s=='adult_severity').sum()),
                  numerical_seedling=('parse_status',lambda s:(s=='seedling_score').sum()),
                  missing=('parse_status',lambda s:s.isin(['blank','missing_marker']).sum()),
                  trace=('parse_status',lambda s:(s=='trace_not_quantified').sum()),
                  range=('parse_status',lambda s:(s=='range_or_interval').sum()),
                  other=('parse_status',lambda s:s.isin(['special_note','unparsed','out_of_range','unverified_seedling']).sum()))
             .reset_index())
    summary['valid_adult_fraction']=summary['numerical_adult']/summary['total']
    return obs,mats,definitions,summary

def read_source_xlsx(path: Path) -> list[list[Any]]:
    # header=None is essential: the workbook has 3 header rows and merged headings.
    raw=pd.read_excel(path,header=None,engine='openpyxl',sheet_name='Summary of SCPRID Phenotypes',dtype=object)
    # Ensure table includes columns AO even if input's right edge is blank.
    return raw.where(pd.notna(raw),None).values.tolist()

def export_all(rows: list[list[Any]], directory: Path=OUTPUT) -> dict:
    obs,mats,defs,quality=build_from_rows(rows)
    directory.mkdir(parents=True,exist_ok=True)
    obs.to_csv(directory/'observations.csv',index=False,encoding='utf-8-sig')
    mats.to_csv(directory/'materials.csv',index=False,encoding='utf-8-sig')
    defs.to_csv(directory/'measurement_dictionary.csv',index=False,encoding='utf-8-sig')
    quality.to_csv(directory/'quality_summary.csv',index=False,encoding='utf-8-sig')
    overview={
        'materials':int(len(mats)), 'measurements':len(MEASUREMENTS),
        'observation_cells':int(len(obs)),
        'stages':obs.stage.value_counts().to_dict(),
        'parse_status_counts':{k:int(v) for k,v in obs.parse_status.value_counts().to_dict().items()},
        'adult_valid_records':int((obs.parse_status=='adult_severity').sum()),
        'seedling_numeric_records':int((obs.parse_status=='seedling_score').sum()),
        'note':'Not a genetic dataset; no automatic imputation of trace, interval, special markers.'
    }
    (directory/'overview.json').write_text(json.dumps(overview,ensure_ascii=False,indent=2),encoding='utf-8')
    overview['audpc_phase2'] = export_audpc(obs,mats,directory)
    complete, _, _ = calculate_njoro_audpc(obs, mats)
    overview['findings_phase3'] = export_findings(complete, directory)
    overview['coverage_phase4'] = export_coverage(obs,mats,complete,directory)
    return overview

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,default=RAW)
    args=parser.parse_args()
    if not args.source.exists():
        parser.error(f'找不到原始 Excel：{args.source}')
    summary=export_all(read_source_xlsx(args.source))
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    print('輸出位置：',OUTPUT)

if __name__=='__main__':
    main()
