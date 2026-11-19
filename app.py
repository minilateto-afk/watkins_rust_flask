"""Watkins rust phenotype exploratory dashboard — Phase 1.

Adult disease severity values only. Does NOT currently compute AUDPC,
Friedman, Spearman, inferred disease resistance or genetic results.
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
    return {'ok':True,'phase':1}

if __name__=='__main__':
    print('開啟：http://127.0.0.1:5000')
    app.run(host='127.0.0.1',port=5000,debug=True)
