"""Watkins wheat rust phenotype analysis platform.

Source-preserving descriptive summaries and verified Njoro AUDPC calculations.
"""
from __future__ import annotations
from functools import lru_cache
from io import StringIO
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from plotly.io import to_html
from flask import Flask, render_template, request, Response, abort
from findings_analysis import build_findings, select_low_audpc, PERCENTILES, PAIR_IDS
from search_utils import normalize_query, search_materials, resolve_material_ids

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data' / 'processed'
app = Flask(__name__)
app.config['JSON_AS_ASCII']=False

STATUS_ZH={
 'adult_severity':'成株期可解析嚴重度',
 'seedling_score':'幼苗期數字評分',
 'missing_marker':'缺失標記',
 'blank':'空白欄位',
 'trace_not_quantified':'痕量評分（未量化）',
 'range_or_interval':'範圍／區間評分',
 'special_note':'特殊註記',
 'unparsed':'無法辨識的格式',
 'out_of_range':'超出合理範圍',
 'unverified_seedling':'待確認的幼苗評分'
}
DISEASE_ZH={'Yellow rust':'黃銹病','Stem rust':'莖銹病','Leaf rust':'葉銹病'}

@lru_cache(maxsize=1)
def get_data():
    for name in ('observations.csv','materials.csv','measurement_dictionary.csv','quality_summary.csv'):
        if not (DATA / name).exists():
            raise RuntimeError('尚未產生清理資料。請先執行：python prepare_data.py')
    obs=pd.read_csv(DATA/'observations.csv',dtype={'material_id':str,'accession':str,'measurement_id':str},keep_default_na=False)
    mats=pd.read_csv(DATA/'materials.csv',dtype={'material_id':str,'accession':str},keep_default_na=False)
    meta=pd.read_csv(DATA/'measurement_dictionary.csv',keep_default_na=False)
    quality=pd.read_csv(DATA/'quality_summary.csv',keep_default_na=False)
    obs['severity_pct']=pd.to_numeric(obs['severity_pct'],errors='coerce')
    obs['seedling_score']=pd.to_numeric(obs['seedling_score'],errors='coerce')
    return obs,mats,meta,quality

def plot_html(fig):
    fig.update_layout(template='plotly_white',font=dict(family='system-ui, sans-serif',color='#233b34'),
                      margin=dict(l=30,r=24,t=35,b=35),height=320,
                      paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)')
    return to_html(fig,full_html=False,include_plotlyjs=False,config={'displaylogo':False,'responsive':True})

def value_round(value, digits=2):
    return None if pd.isna(value) else round(float(value),digits)

@app.context_processor
def shared():
    return {'status_zh':STATUS_ZH,'disease_zh':DISEASE_ZH}

@app.route('/')
def dashboard():
    obs,mats,meta,quality=get_data()
    mid=request.args.get('m','I')
    valid_ids=set(meta.column.astype(str))
    if mid not in valid_ids: mid='I'
    m=meta.loc[meta.column==mid].iloc[0]
    selected=obs[obs.measurement_id==mid].copy()
    is_seedling=m.stage=='seedling'
    field='seedling_score' if is_seedling else 'severity_pct'
    numeric=selected[field].dropna()
    status_counts=(selected.parse_status.value_counts()
                   .reindex(list(STATUS_ZH),fill_value=0))
    stats={
       'total':len(selected), 'valid':int(numeric.size),
       'mean':value_round(numeric.mean()), 'median':value_round(numeric.median()),
       'std':value_round(numeric.std(ddof=1)),
       'min':value_round(numeric.min()),'max':value_round(numeric.max()),
       'q1':value_round(numeric.quantile(.25)),'q3':value_round(numeric.quantile(.75)),
    }
    if len(numeric):
        fig=go.Figure(go.Histogram(x=numeric,nbinsx=21,marker_color='#177e68',opacity=.9))
        fig.update_layout(xaxis_title='幼苗原始評分（非百分比）' if is_seedling else '病害嚴重度（%）',
                          yaxis_title='材料筆數')
        hist=plot_html(fig)
    else:hist=None
    visible=status_counts[status_counts>0]
    fig=go.Figure(go.Bar(x=[STATUS_ZH[s] for s in visible.index],y=visible.values,
                         marker_color=['#177e68' if s in ('adult_severity','seedling_score') else '#aab9b3' for s in visible.index]))
    fig.update_layout(yaxis_title='筆數',xaxis_tickangle=-20)
    status_chart=plot_html(fig)
    # Keep actual scored entries, including raw and reaction, for transparent auditing.
    table=selected[['material_id','accession','country','raw_score','parse_status',field,'reaction']].head(30).fillna('').to_dict('records')
    meta_options=meta.copy()
    meta_options['display']=meta_options.apply(lambda r:f"{DISEASE_ZH.get(r.disease,r.disease)} · {r.site} · {r.stage} · {r.label} [{r.column}]",axis=1)
    return render_template('dashboard.html',active='dashboard',measurements=meta_options.to_dict('records'),
          mid=mid,meta=m,stats=stats,hist=hist,status_chart=status_chart,
          quality=status_counts.to_dict(),records=table,is_seedling=is_seedling,
          total_materials=len(mats))

@app.route('/quality')
def quality_page():
    obs,mats,meta,quality=get_data()
    q=quality.merge(meta[['column','label','date_source']],left_on='measurement_id',right_on='column',how='left')
    order={'Yellow rust':0,'Stem rust':1,'Leaf rust':2}
    q['disease_order']=q.disease.map(order)
    q=q.sort_values(['disease_order','site','date']).drop(columns='disease_order')
    counts=obs.parse_status.value_counts().to_dict()
    return render_template('quality.html',active='quality',rows=q.to_dict('records'),
                           count=len(mats),total=len(obs),counts=counts)

@lru_cache(maxsize=1)
def get_coverage_data():
    """All 650 have metadata; only 601 have usable numeric observations."""
    import json
    required = ('coverage_all_650.csv', 'coverage_summary.json')
    for name in required:
        if not (DATA/name).exists():
            raise RuntimeError('缺少第四階段資料；請執行 python prepare_data.py')
    table=pd.read_csv(DATA/'coverage_all_650.csv',
                      dtype={'material_id':str,'accession':str}, keep_default_na=False)
    info=json.loads((DATA/'coverage_summary.json').read_text(encoding='utf-8'))
    if len(table)!=info['total'] or int((table.numeric_count>0).sum())!=info['any_numeric']:
        raise RuntimeError('650 筆材料涵蓋清單與統計摘要不一致')
    return table,info


@app.route('/coverage')
def coverage_page():
    table, info=get_coverage_data()
    raw=request.args.get('group','all')
    allowed=('all','complete_ijk','other_numeric','no_numeric')
    group=raw if raw in allowed else 'all'
    q=normalize_query(request.args.get('q',''),90)
    shown=table if group=='all' else table[table.coverage_group==group]
    if q:
        shown=search_materials(shown,q)
    try:
        page=max(1,int(request.args.get('page','1')))
    except ValueError:
        page=1
    per_page=50
    n_pages=max(1,(len(shown)+per_page-1)//per_page)
    page=min(page,n_pages)
    total_matching=len(shown)
    if not q:
        shown=shown.sort_values('excel_row')
    shown=shown.iloc[(page-1)*per_page:page*per_page]
    bins=table.numeric_count.value_counts().sort_index()
    counts=go.Figure(go.Bar(x=bins.index.tolist(),y=bins.values.tolist(),
                            marker_color='#167b65'))
    counts.update_layout(xaxis_title='每份材料可解析的數值觀測欄位數（0–29）',
                        yaxis_title='材料數量',height=350)
    disease=go.Figure(go.Bar(
       x=['黃銹病','莖銹病','葉銹病'],
       y=[info['any_yellow_adult'],info['any_stem_adult'],info['any_leaf_adult']],
       marker_color=['#167b65','#dc9147','#637cbd'],
       text=[info['any_yellow_adult'],info['any_stem_adult'],info['any_leaf_adult']],
       textposition='outside'))
    disease.update_layout(yaxis_title='至少有一筆可解析成株期病害分數的材料數量',
                          yaxis_range=[0,650],height=350)
    return render_template('coverage.html',active='coverage',
       summary=info,group=group,q=q,page=page,n_pages=n_pages,
       filtered_count=int(len(table)) if (group=='all' and not q) else None,
       rows=shown.to_dict('records'),
       results_count=total_matching,
       chart_counts=plot_html(counts), chart_disease=plot_html(disease))


@app.route('/coverage/export')
def coverage_export():
    table,_=get_coverage_data()
    buffer=StringIO()
    table.to_csv(buffer,index=False)
    return Response('\ufeff'+buffer.getvalue(),mimetype='text/csv; charset=utf-8',
       headers={'Content-Disposition':'attachment; filename="watkins_all_650_coverage.csv"'})


@app.route('/materials')
def materials_page():
    _,mats,_,_=get_data()
    q=normalize_query(request.args.get('q',''),100)
    filtered=search_materials(mats,q)
    try:
        page=max(1,int(request.args.get('page','1')))
    except (ValueError,TypeError):
        page=1
    per_page=50
    count=len(filtered)
    n_pages=max(1,(count+per_page-1)//per_page)
    page=min(page,n_pages)
    shown=filtered.iloc[(page-1)*per_page:page*per_page]
    return render_template('materials.html',active='materials',q=q,total=count,
                           total_materials=len(mats),page=page,n_pages=n_pages,
                           rows=shown.fillna('').to_dict('records'))

@app.route('/materials/<material_id>')
def material_detail(material_id):
    obs,mats,meta,_=get_data()
    found=mats[mats.material_id==material_id]
    if found.empty:abort(404)
    mat=found.iloc[0].to_dict()
    rows=obs[obs.material_id==material_id].sort_values(['disease','site','date']).copy()
    adult=rows[rows.stage=='adult']
    fig=go.Figure()
    for (disease,site,series), g in adult.groupby(['disease','site','series'],sort=False):
        g=g.sort_values('date')
        fig.add_trace(go.Scatter(x=g.date,y=g.severity_pct,mode='lines+markers',
                  name=f'{DISEASE_ZH.get(disease,disease)} · {site} · {series}',
                  hovertemplate='%{x}<br>嚴重度 %{y}%<extra>%{fullData.name}</extra>'))
    fig.update_traces(connectgaps=False)
    fig.update_layout(yaxis_title='成株期嚴重度（%）',xaxis_title='2013 年觀測日期',legend=dict(orientation='h',y=-.3),height=440)
    chart=plot_html(fig) if adult.severity_pct.notna().any() else None
    audpc,_,_=get_audpc_data()
    available=audpc[audpc.material_id==material_id]
    audpc_result=available.iloc[0].to_dict() if not available.empty else None
    rows=rows.fillna('')
    return render_template('material_detail.html',active='materials',mat=mat,
         records=rows.to_dict('records'),chart=chart,audpc_result=audpc_result)


@app.route('/methods')
def methods_page():
    return render_template('methods.html',active='methods')

@app.route('/export')
def export():
    obs,_,meta,_=get_data()
    mid=request.args.get('m','I')
    if mid not in set(meta.column.astype(str)):abort(404)
    selected=obs[obs.measurement_id==mid].copy()
    stream=StringIO()
    selected.to_csv(stream,index=False)
    # UTF-8 BOM for spreadsheet clients (Chinese labels preserved in remaining source metadata).
    return Response('\ufeff'+stream.getvalue(),mimetype='text/csv; charset=utf-8',
                    headers={'Content-Disposition':f'attachment; filename="watkins_{mid}_cleaned.csv"'})

@app.route('/health')
def health():
    return {'ok':True,'service':'watkins-wheat-rust'}


@lru_cache(maxsize=1)
def get_audpc_data():
    """Read the reproducible Phase 2 outputs generated by prepare_data.py."""
    import json
    for filename in ('audpc_njoro_apr_may.csv','audpc_excluded.csv','audpc_summary.json'):
        if not (DATA/filename).exists():
            raise RuntimeError('缺少第二階段 AUDPC 資料。請先執行 python prepare_data.py')
    good=pd.read_csv(DATA/'audpc_njoro_apr_may.csv',
                     dtype={'material_id':str,'accession':str}, keep_default_na=False)
    excluded=pd.read_csv(DATA/'audpc_excluded.csv',
                         dtype={'material_id':str,'accession':str},keep_default_na=False)
    overview=json.loads((DATA/'audpc_summary.json').read_text(encoding='utf-8'))
    return good,excluded,overview


@app.route('/audpc')
def audpc_page():
    good, excluded, info=get_audpc_data()
    q=request.args.get('q','').strip()[:70]
    sort=request.args.get('sort','low')
    mid=normalize_query(request.args.get('id','2'),40)
    sort_options={'low':('audpc_pct_days',True),
                  'high':('audpc_pct_days',False),
                  'id':('material_id_num',True)}
    if sort not in sort_options: sort='low'
    shown=search_materials(good,q)
    shown['material_id_num']=pd.to_numeric(shown.material_id,errors='coerce')
    col,ascending=sort_options[sort]
    shown=shown.sort_values([col,'material_id_num'],ascending=[ascending,True])
    fig=go.Figure(go.Histogram(x=good['audpc_pct_days'],nbinsx=27,marker_color='#167b65'))
    fig.update_layout(xaxis_title='AUDPC（%·天）', yaxis_title='完整三次觀測的材料數量')
    distribution=plot_html(fig)
    sample=good[(good.material_id==mid) | (good.accession==mid)]
    unknown_selection=None
    if sample.empty:
        unknown_selection=mid
        sample=good.iloc[:0] if request.args.get('id') else good[good.material_id=='2']
    selected=sample.iloc[0].to_dict() if not sample.empty else None
    example_chart=None
    segments=[]
    if selected:
        ys=[float(selected[x]) for x in ('apr21_pct','apr30_pct','may07_pct')]
        times=[0,9,16]
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=times,y=ys,mode='lines+markers',
              marker=dict(size=10,color='#11694e'), line=dict(width=3,color='#167b65'),
              fill='tozeroy',fillcolor='rgba(22,123,101,0.11)',
              name='觀測嚴重度',hovertemplate='第 %{x} 天<br>%{y}%<extra></extra>'))
        fig.update_layout(xaxis=dict(title='距 4/21 天數（天）',tickmode='array',tickvals=times,
                                     ticktext=['4/21（0 天）','4/30（9 天）','5/7（16 天）']),
                          yaxis=dict(title='病害嚴重度（%）',range=[0, max(10, min(100,max(ys)+12))]),
                          showlegend=False)
        example_chart=plot_html(fig)
        segments=[{'from':'4/21 → 4/30','start':ys[0],'end':ys[1],
                   'days':9,'area':float(selected['area_apr21_apr30'])},
                  {'from':'4/30 → 5/7','start':ys[1],'end':ys[2],
                   'days':7,'area':float(selected['area_apr30_may07'])}]
    # Material IDs present in the CSV are trusted numbers, not user-provided HTML.
    out=shown.head(60).to_dict('records')
    return render_template('audpc.html', active='audpc', summary=info,
            histogram=distribution, rows=out, shown_count=len(shown),
            sort=sort,q=q,selected=selected,example_chart=example_chart,
            segments=segments,unknown_selection=unknown_selection,
            excluded_preview=excluded.head(5).to_dict('records'))


@app.route('/audpc/export')
def audpc_export():
    good,_,_=get_audpc_data()
    output=StringIO()
    cols=['material_id','accession','country','accession_name',
          'I_raw','J_raw','K_raw','apr21_pct','apr30_pct','may07_pct',
          'area_apr21_apr30','area_apr30_may07',
          'audpc_pct_days','time_weighted_mean_pct']
    good[cols].to_csv(output,index=False)
    return Response('\ufeff'+output.getvalue(),mimetype='text/csv; charset=utf-8',
       headers={'Content-Disposition':'attachment; filename="njoro_2013_audpc_complete_cases.csv"'})


@lru_cache(maxsize=1)
def get_findings_data():
    import json
    path = DATA / 'findings_matched_490.csv'
    summary_file = DATA / 'findings_summary.json'
    if not path.exists() or not summary_file.exists():
        raise RuntimeError('缺少第三階段分析資料。請先執行 python prepare_data.py')
    findings = pd.read_csv(path, dtype={'material_id':str, 'accession':str}, keep_default_na=False)
    summary = json.loads(summary_file.read_text(encoding='utf-8'))
    # Refuse inconsistent files instead of displaying stale analysis.
    verified, check = build_findings(findings)
    if check['complete_count'] != summary['complete_count'] or check['direction_counts'] != summary['direction_counts']:
        raise RuntimeError('第三階段統計摘要與資料不一致，請重新執行 prepare_data.py')
    return verified, summary


def _curve_figure(rows, title='材料的病害進展'):
    fig = go.Figure()
    palette = ['#167b65', '#dc9147', '#637cbd', '#a35f9a']
    for idx, record in enumerate(rows):
        ys = [float(record[c]) for c in ('apr21_pct','apr30_pct','may07_pct')]
        fig.add_trace(go.Scatter(
            x=[0, 9, 16], y=ys, mode='lines+markers',
            name=f"材料 {record['material_id']} · AUDPC {record['audpc_pct_days']:g}",
            line=dict(color=palette[idx % len(palette)], width=3),
            marker=dict(size=10),
            hovertemplate='第 %{x} 天 · %{y:.1f}%<extra>%{fullData.name}</extra>'))
    fig.update_layout(title=title, xaxis=dict(title='距 4/21 的天數', tickmode='array',
                      tickvals=[0,9,16], ticktext=['4/21','4/30','5/7']),
                      yaxis=dict(title='病害嚴重度（%）', range=[-1, 101]),
                      legend=dict(orientation='h',y=-.32),height=380)
    return plot_html(fig)


@app.route('/findings')
def findings_page():
    findings, summary = get_findings_data()
    dates = summary['dates_stats']
    trend = go.Figure()
    trend.add_trace(go.Scatter(x=[d['day'] for d in dates], y=[d['mean'] for d in dates],
                               name='平均數', mode='lines+markers',
                               line=dict(color='#167b65', width=3), marker=dict(size=10)))
    trend.add_trace(go.Scatter(x=[d['day'] for d in dates], y=[d['median'] for d in dates],
                               name='中位數',mode='lines+markers',
                               line=dict(color='#dc9147', width=3), marker=dict(size=9)))
    trend.update_layout(xaxis=dict(title='距 4/21 的天數',tickmode='array',tickvals=[0,9,16],
                                    ticktext=['4/21','4/30','5/7']),
                        yaxis=dict(title='病害嚴重度（%）',range=[0,60]),
                        legend=dict(orientation='h', y=-.30),height=350)
    directions = summary['direction_counts']
    bars = go.Figure(go.Bar(x=['增加','不變','下降'],
                            y=[directions['增加'],directions['不變'],directions['下降']],
                            marker_color=['#167b65','#b6c7be','#dc9147'],
                            text=[directions['增加'],directions['不變'],directions['下降']],
                            textposition='outside'))
    bars.update_layout(yaxis_title='材料筆數',yaxis_range=[0,470],height=350)
    delta = go.Figure(go.Histogram(x=findings['delta_16d_pct_points'],nbinsx=24,
                                   marker_color='#637cbd'))
    delta.update_layout(xaxis_title='5/7 − 4/21 病害嚴重度（百分點）', yaxis_title='材料筆數')
    raw_input=normalize_query(request.args.get('compare','43,436'),130)
    ids, unknown=resolve_material_ids(findings,raw_input,max_items=4)
    selected=findings[findings.material_id.isin(ids)].copy()
    selected['display_order']=selected.material_id.map({mid:i for i,mid in enumerate(ids)})
    selected=selected.sort_values('display_order')
    rows=selected.to_dict('records')
    comparison=_curve_figure(rows) if rows else None
    return render_template('findings.html',active='findings',summary=summary,
         trend=plot_html(trend), direction_chart=plot_html(bars),
         delta_chart=plot_html(delta), comparison=comparison,
         selected_rows=rows, unknown_ids=unknown, compare_input=raw_input,
         pair_rows=findings[findings.material_id.isin(PAIR_IDS)].sort_values('material_id').to_dict('records'))


@app.route('/screening')
def screening_page():
    findings, summary = get_findings_data()
    raw = request.args.get('percentile','10')
    try:
        percentile = int(raw)
    except (ValueError, TypeError):
        percentile = 10
    if percentile not in PERCENTILES:
        percentile = 10
    group, bounds = select_low_audpc(findings, percentile)
    # Show actual selection against the full complete-case distribution.
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=findings.audpc_pct_days,y=findings.may07_pct,
         mode='markers',name='所有完整材料',marker=dict(color='#c6d4ce',size=7,opacity=.65)))
    fig.add_trace(go.Scatter(x=group.audpc_pct_days,y=group.may07_pct,
         mode='markers',name='探索性低 AUDPC 子集合',
         marker=dict(color='#167b65',size=8,opacity=.85)))
    fig.add_vline(x=bounds['cutoff'], line_dash='dash',line_color='#dc9147',
                  annotation_text=f"第 {percentile} 百分位：{bounds['cutoff']:g}",
                  annotation_position='top right')
    fig.update_layout(xaxis_title='AUDPC（%·天）',yaxis_title='5/7 病害嚴重度（%）',
                      legend=dict(orientation='h',y=-.3),height=390)
    # Search all 490 complete-case materials. State whether a matched record
    # passes the currently selected exploratory cutoff; never imply that an
    # excluded or incomplete material has an AUDPC value.
    q=normalize_query(request.args.get('q',''),100)
    matched=search_materials(findings,q) if q else group
    matched=matched.copy()
    matched['within_cutoff']=matched.audpc_pct_days.le(bounds['cutoff'])
    matched['material_id_num']=pd.to_numeric(matched.material_id,errors='coerce')
    if not q:
        matched=matched.sort_values(['audpc_pct_days','material_id_num'])
    display_count=len(matched)
    displayed=matched.head(80).to_dict('records')
    # A search without complete-case results can still resolve to a valid
    # source accession with other recorded scores.
    fallback_records=[]
    if q and matched.empty:
        _, mats, _, _ = get_data()
        fallback_records=search_materials(mats,q).head(8).to_dict('records')
    raw_compare=normalize_query(request.args.get('compare','43,436'),130)
    ids, unknown=resolve_material_ids(findings,raw_compare,max_items=4)
    curve_rows=findings[findings.material_id.isin(ids)].copy()
    curve_rows['_order']=curve_rows.material_id.map({v:i for i,v in enumerate(ids)})
    curve_rows=curve_rows.sort_values('_order').drop(columns='_order')
    comparison= _curve_figure(curve_rows.to_dict('records'),title='指定材料的病害進展比較') if len(curve_rows) else None
    return render_template('screening.html',active='screening',
          summary=summary,selected=displayed,selection=bounds,
          options=PERCENTILES,percentile=percentile,chart=plot_html(fig),
          shown=len(displayed),matched_count=display_count,search_query=q,
          outside_complete=fallback_records,compare_input=raw_compare,
          compare_error=unknown,comparison=comparison,
          compare_rows=curve_rows.to_dict('records'))


@app.route('/findings/export')
def findings_export():
    data, _ = get_findings_data()
    csv = StringIO()
    data.to_csv(csv,index=False)
    return Response('\ufeff'+csv.getvalue(),mimetype='text/csv; charset=utf-8',
           headers={'Content-Disposition':'attachment; filename="njoro_matched_descriptive_results.csv"'})


@app.route('/screening/export')
def screening_export():
    data, _ = get_findings_data()
    try:
        percentile = int(request.args.get('percentile','10'))
    except (ValueError,TypeError):
        abort(400)
    if percentile not in PERCENTILES:abort(400)
    chosen,_ = select_low_audpc(data,percentile)
    csv = StringIO()
    chosen.to_csv(csv,index=False)
    return Response('\ufeff'+csv.getvalue(),mimetype='text/csv; charset=utf-8',
           headers={'Content-Disposition':f'attachment; filename="low_audpc_p{percentile}_exploratory.csv"'})

if __name__=='__main__':
    print('開啟：http://127.0.0.1:5000')
    app.run(host='127.0.0.1',port=5000,debug=False)
