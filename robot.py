"""Simulateur de trading éducatif, sans accès à un courtier."""
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import yfinance as yf

ROOT = Path(__file__).parent
STATE = ROOT / 'etat.json'
HISTORY = ROOT / 'transactions.csv'
REPORT = ROOT / 'index.html'
TICKERS = ['SHOP.TO', 'NVDA', 'VNP.TO', 'GURU.TO', 'MTY.TO']
INITIAL = 1000.0
MAX_POSITION = 0.20
STOP_LOSS = 0.08
TAKE_PROFIT = 0.15

def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding='utf-8'))
    return {'cash': INITIAL, 'positions': {}, 'last_prices': {}, 'updated': None}

def prices():
    result = {}
    for ticker in TICKERS:
        try:
            df = yf.Ticker(ticker).history(period='65d', auto_adjust=True)
            if len(df) < 22:
                print('Données insuffisantes:', ticker)
                continue
            close = df['Close'].dropna()
            if len(close) < 22:
                continue
            # Signal simple: croisement moyenne 5 jours / 20 jours.
            recent = float(close.iloc[-5:].mean())
            slow = float(close.iloc[-20:].mean())
            prev_recent = float(close.iloc[-6:-1].mean())
            prev_slow = float(close.iloc[-21:-1].mean())
            result[ticker] = {'price': round(float(close.iloc[-1]), 4), 'buy': prev_recent <= prev_slow and recent > slow, 'sell': prev_recent >= prev_slow and recent < slow}
        except Exception as exc:
            print('Erreur de données', ticker, str(exc))
    return result

def main():
    state = load_state()
    data = prices()
    if not data:
        raise RuntimeError('Aucun prix disponible : état inchangé, aucun ordre simulé.')
    transactions = []
    positions = state['positions']
    cash = float(state['cash'])
    for ticker, info in data.items():
        if ticker not in positions:
            continue
        position = positions[ticker]
        price = info['price']
        if info['sell'] or price <= position['entry'] * (1 - STOP_LOSS) or price >= position['entry'] * (1 + TAKE_PROFIT):
            qty = int(position['qty'])
            cash += qty * price
            transactions.append([datetime.now(timezone.utc).isoformat(), 'VENTE', ticker, qty, price, round(qty * price, 2)])
            del positions[ticker]
    equity = cash + sum(float(pos['qty']) * data.get(ticker, {}).get('price', state.get('last_prices', {}).get(ticker, pos['entry'])) for ticker, pos in positions.items())
    for ticker, info in data.items():
        if not info['buy'] or ticker in positions or len(positions) >= 5:
            continue
        price = info['price']
        # Conversion CAD/USD volontairement non automatisée : éviter les erreurs de devises.
        # Les titres US ne sont pas négociés dans cette version CAD.
        if not ticker.endswith('.TO'):
            continue
        budget = min(cash, equity * MAX_POSITION)
        qty = int(budget // price)
        if qty < 1:
            continue
        cash -= qty * price
        positions[ticker] = {'qty': qty, 'entry': price}
        transactions.append([datetime.now(timezone.utc).isoformat(), 'ACHAT', ticker, qty, price, round(qty * price, 2)])
    state['cash'] = round(cash, 2)
    state['last_prices'].update({t: x['price'] for t, x in data.items()})
    state['updated'] = datetime.now(timezone.utc).isoformat()
    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding='utf-8')
    if transactions:
        first = not HISTORY.exists()
        with HISTORY.open('a', newline='', encoding='utf-8') as fh:
            writer = csv.writer(fh)
            if first:
                writer.writerow(['date_utc', 'action', 'symbole', 'quantite', 'prix', 'montant'])
            writer.writerows(transactions)
    equity = cash + sum(float(p['qty']) * state['last_prices'].get(t, p['entry']) for t, p in positions.items())
    import html
    rows = ''.join(f'<tr><td>{html.escape(t)}</td><td>{p["qty"]}</td><td>{p["entry"]:.2f} $</td><td>{state["last_prices"].get(t, p["entry"]):.2f} $</td></tr>' for t, p in positions.items()) or '<tr><td colspan="4">Aucune position actuellement</td></tr>'
    REPORT.write_text(f'''<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Mon robot trading — simulation</title><style>body{{font-family:system-ui;max-width:760px;margin:auto;padding:24px;background:#f6f8fa;color:#17212d}}main{{background:white;border-radius:16px;padding:22px}}table{{border-collapse:collapse;width:100%}}td,th{{border-bottom:1px solid #ddd;padding:12px;text-align:left}}.num{{font-size:2rem;font-weight:bold}}</style><main><h1>Mon robot trading</h1><p>SIMULATION SEULEMENT — aucun ordre réel</p><p>Valeur estimée du portefeuille</p><div class="num">{equity:.2f} $ CAD</div><p>Espèces : {cash:.2f} $ CAD</p><p>Dernière mise à jour (UTC) : {html.escape(state['updated'])}</p><h2>Positions simulées</h2><table><tr><th>Titre</th><th>Qté</th><th>Prix d'achat</th><th>Dernier prix</th></tr>{rows}</table><p>Les cours peuvent être différés. Simulation sans frais ni glissement. Aucun rendement garanti.</p></main></html>''', encoding='utf-8')
    print('Simulation terminée. Valeur CAD estimée:', round(equity, 2), 'Transactions:', len(transactions))

if __name__ == '__main__':
    main()
