"""Watkins rust phenotype exploratory dashboard — Phase 2.

Descriptive plots and one conservative, audited AUDPC series only. No
Friedman, Spearman, genetic inference or claims of field resistance.
"""
from __future__ import annotations
from functools import lru_cache
from io import StringIO
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from plotly.io import to_html
from flask import Flask, render_template, request, Response, abort

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

@app.route('/materials')
def materials_page():
    _,mats,_,_=get_data()
    q=request.args.get('q','').strip()[:100]
    filtered=mats
    if q:
        mask=(mats['material_id'].str.contains(q,case=False,regex=False) |
              mats['accession'].fillna('').str.contains(q,case=False,regex=False) |
              mats['accession_name'].fillna('').str.contains(q,case=False,regex=False) |
              mats['country'].fillna('').str.contains(q,case=False,regex=False))
        filtered=mats[mask]
    return render_template('materials.html',active='materials',q=q,total=len(filtered),
                           rows=filtered.head(100).fillna('').to_dict('records'))

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
    rows=rows.fillna('')
    return render_template('material_detail.html',active='materials',mat=mat,records=rows.to_dict('records'),chart=chart)

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
    return {'ok':True,'phase':2}


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
    mid=request.args.get('id','2').strip()[:30]
    sort_options={'low':('audpc_pct_days',True),
                  'high':('audpc_pct_days',False),
                  'id':('material_id_num',True)}
    if sort not in sort_options: sort='low'
    shown=good.copy()
    if q:
        mask=(shown['material_id'].str.contains(q,case=False,regex=False) |
              shown['accession'].fillna('').str.contains(q,case=False,regex=False) |
              shown['accession_name'].fillna('').str.contains(q,case=False,regex=False) |
              shown['country'].fillna('').str.contains(q,case=False,regex=False))
        shown=shown[mask]
    shown['material_id_num']=pd.to_numeric(shown.material_id,errors='coerce')
    col,ascending=sort_options[sort]
    shown=shown.sort_values([col,'material_id_num'],ascending=[ascending,True])
    fig=go.Figure(go.Histogram(x=good['audpc_pct_days'],nbinsx=27,marker_color='#167b65'))
    fig.update_layout(xaxis_title='AUDPC（%·天）', yaxis_title='完整三次觀測的材料數量')
    distribution=plot_html(fig)
    sample=good[good.material_id==mid]
    if sample.empty:
        sample=good[good.material_id=='2']
    if sample.empty:sample=good.head(1)
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
            segments=segments,excluded_preview=excluded.head(5).to_dict('records'))


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

if __name__=='__main__':
    print('開啟：http://127.0.0.1:5000')
    app.run(host='127.0.0.1',port=5000,debug=False)
