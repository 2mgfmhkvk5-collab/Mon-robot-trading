import json, os, math, html
from datetime import datetime, timezone
from pathlib import Path
import yfinance as yf

ROOT=Path(__file__).parent
STATE=ROOT/'state.json'
OUT=ROOT/'docs'/'index.html'
SYMBOLS=['NVDA','PLUG','WOLF','OUST','MVIS','BTG','HL','UUUU','DNN','SOUN']
START_CAD=1000.0
MAX_POSITION_CAD=250.0
MAX_POSITIONS=3
FEE_CAD=1.0 # estimation par ordre, ajustable
USD_CAD=1.38 # taux de simulation fixe; remplacer par taux réel avant tout test sérieux

def load():
    if STATE.exists(): return json.loads(STATE.read_text())
    return {'cash':START_CAD,'positions':{},'pending':{},'trades':[],'history':[],'last_day':None}

def save(s): STATE.write_text(json.dumps(s,indent=2,ensure_ascii=False)+'\n')

def market_data(symbol):
    try:
        df=yf.download(symbol,period='4mo',interval='1d',auto_adjust=True,progress=False,threads=False)
        if df is None or len(df)<25:return None
        if hasattr(df.columns,'nlevels') and df.columns.nlevels>1:df.columns=df.columns.get_level_values(0)
        df=df.dropna(subset=['Open','Close','Volume'])
        if len(df)<25:return None
        return df
    except Exception as exc:
        print('Data error',symbol,str(exc));return None

def run():
    s=load(); data={x:market_data(x) for x in SYMBOLS}
    valid=[(x,d) for x,d in data.items() if d is not None]
    if not valid: raise RuntimeError('Aucune donnée de marché valide. Aucun état modifié.')
    dates=[str(d.index[-1].date()) for _,d in valid]
    day=max(dates)
    if s['last_day']==day:
        render(s,data,'Aucune nouvelle séance : état inchangé.');return
    # Pour éviter les signaux sur données décalées, ne traite que les symboles actualisés au même jour.
    today={x:d for x,d in valid if str(d.index[-1].date())==day}
    if len(today)<3:raise RuntimeError('Moins de trois symboles actualisés. Exécution annulée.')
    # Les signaux créés la veille sont exécutés à l\'ouverture de la séance suivante (modèle approximatif).
    pending=s.get('pending',{})
    for x,order in list(pending.items()):
        if x not in today:continue
        d=today[x]; open_price=float(d['Open'].iloc[-1]);price_cad=open_price*USD_CAD
        if not (math.isfinite(price_cad) and price_cad>0):continue
        if order=='SELL' and x in s['positions']:
            p=s['positions'].pop(x);proceeds=p['qty']*price_cad-FEE_CAD
            s['cash']+=proceeds;s['trades'].append({'date':day,'symbol':x,'side':'SELL','qty':p['qty'],'price_cad':round(price_cad,4),'net_cad':round(proceeds,2)})
        elif order=='BUY' and x not in s['positions'] and len(s['positions'])<MAX_POSITIONS:
            budget=min(MAX_POSITION_CAD,s['cash']-FEE_CAD);qty=int(budget/price_cad)
            if qty>0 and s['cash']>=qty*price_cad+FEE_CAD:
                cost=qty*price_cad+FEE_CAD;s['cash']-=cost
                s['positions'][x]={'qty':qty,'entry_cad':price_cad,'highest_cad':price_cad}
                s['trades'].append({'date':day,'symbol':x,'side':'BUY','qty':qty,'price_cad':round(price_cad,4),'net_cad':round(-cost,2)})
    new_pending={}
    for x,d in today.items():
        close=float(d['Close'].iloc[-1]);vol=float(d['Volume'].iloc[-1]);
        if not (math.isfinite(close) and math.isfinite(vol)):continue
        ma5=float(d['Close'].tail(5).mean());ma20=float(d['Close'].tail(20).mean());prev5=float(d['Close'].iloc[-6:-1].mean());prev20=float(d['Close'].iloc[-21:-1].mean());v20=float(d['Volume'].iloc[-21:-1].mean())
        if x in s['positions']:
            p=s['positions'][x];p['highest_cad']=max(p.get('highest_cad',p['entry_cad']),close*USD_CAD)
            change=close*USD_CAD/p['entry_cad']-1
            if change<=-0.06 or change>=0.12 or (prev5>=prev20 and ma5<ma20):new_pending[x]='SELL'
        elif 0.01<=close<=5 and prev5<=prev20 and ma5>ma20 and v20>0 and vol>=1.5*v20:
            new_pending[x]='BUY'
    equity=s['cash']+sum(p['qty']*float(today[x]['Close'].iloc[-1])*USD_CAD for x,p in s['positions'].items() if x in today)
    # Si une position ne dispose pas de cotation fraîche, valoriser à son dernier plus haut mémorisé est interdit : conserver le dernier prix connu.
    for x,p in s['positions'].items():
        if x not in today:equity+=p['qty']*p.get('last_cad',p['entry_cad'])
        else:p['last_cad']=float(today[x]['Close'].iloc[-1])*USD_CAD
    s['history'].append({'date':day,'equity_cad':round(equity,2)})
    # coupe-circuit pour les prochains achats si la perte du jour atteint 3% du capital de départ
    if len(s['history'])>=2 and equity<=s['history'][-2]['equity_cad']-30:
        new_pending={x:v for x,v in new_pending.items() if v!='BUY'}
    s['pending']=new_pending;s['last_day']=day
    save(s);render(s,data,'Simulation seulement. Aucune transaction réelle.')

def render(s,data,note):
    holdings=''.join(f"<tr><td>{html.escape(x)}</td><td>{p['qty']}</td><td>{p['entry_cad']:.3f} $</td></tr>" for x,p in s['positions'].items()) or '<tr><td colspan="3">Aucune position</td></tr>'
    trades=''.join(f"<tr><td>{html.escape(t['date'])}</td><td>{html.escape(t['symbol'])}</td><td>{t['side']}</td><td>{t['qty']}</td><td>{t['net_cad']:.2f} $</td></tr>" for t in s['trades'][-30:][::-1]) or '<tr><td colspan="5">Aucune transaction</td></tr>'
    equity=s['history'][-1]['equity_cad'] if s['history'] else START_CAD
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(f'''<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Robot de trading · Simulation</title><style>body{{font:16px -apple-system,Arial;background:#101827;color:#f5f7fb;margin:0;padding:22px;max-width:850px;margin:auto}}.card{{background:#1d2b3d;padding:20px;border-radius:15px;margin:15px 0}}h1{{font-size:26px}}.big{{font-size:36px;font-weight:750}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{text-align:left;padding:9px;border-bottom:1px solid #445}}.muted{{color:#b4c5d8}}.warn{{color:#ffcd70}}</style><h1>Robot de trading</h1><p class="warn">SIMULATION — Aucun ordre envoyé à Disnat</p><div class="card"><div class="muted">Valeur simulée</div><div class="big">{equity:,.2f} $ CAD</div><p>Liquidités : {s['cash']:,.2f} $ CAD</p><p>Dernière séance traitée : {html.escape(str(s['last_day']))}</p></div><div class="card"><h2>Positions</h2><table><tr><th>Symbole</th><th>Actions</th><th>Entrée CAD</th></tr>{holdings}</table></div><div class="card"><h2>Transactions virtuelles</h2><table><tr><th>Date</th><th>Titre</th><th>Type</th><th>Qté</th><th>Flux CAD</th></tr>{trades}</table></div><div class="card"><h2>Ordres prévus pour la prochaine séance</h2><p>{html.escape(', '.join(x+': '+v for x,v in s.get('pending',{}).items()) or 'Aucun')}</p></div><p class="muted">{html.escape(note)} Données Yahoo Finance non garanties, frais estimés de 1 $/ordre et taux fixe 1 USD = 1,38 CAD. Ni performance réelle ni conseil d'investissement. Dernière génération UTC : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}.</p></html>''',encoding='utf-8')

if __name__=='__main__':run()
