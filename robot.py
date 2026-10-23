"""Robot de paper trading v2 (1000 CAD), sans connexion à un courtier.

IMPORTANT :
- Utilise des cours quotidiens Yahoo Finance, parfois différés.
- Ce n'est PAS encore un robot d'actualité ou un moteur de cotations temps réel.
- Le fichier workflow de GitHub devra ensuite être adapté afin de conserver
  durablement les nouveaux fichiers et de tester la branche de façon isolée.
- Aucune transaction réelle.
"""

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import yfinance as yf

ROOT = Path(__file__).resolve().parent
# Séparer complètement la V2 de l'ancien état sur la branche main.
STATE = ROOT / "etat_v2.json"
HISTORY = ROOT / "transactions_v2.csv"
REPORT = ROOT / "index_v2.html"

INITIAL_CAD = 1000.0
FEE_CAD = 1.0                 # Hypothèse de frais par opération fictive
RISK_FRACTION = 0.005         # 0,5 % du portefeuille par opération
DAILY_BRAKE_FRACTION = 0.03   # -3 % : stop aux nouveaux achats
MAX_POSITION_FRACTION = 0.35  # 35 % du capital par titre
MAX_POSITIONS = 4
STOP_MIN_FRACTION = 0.05      # Stop de 5 % minimum sur les titres volatils
TRAIL_FRACTION = 0.08         # Stop suiveur de 8 % après hausse confirmée
MAX_SPREAD_UNKNOWN = True     # Les spreads intrajournaliers ne sont pas mesurés

# Tous les symboles achetables sont en CAD. Pas de conversion USD implicite.
WATCHLIST = ["GURU.TO", "VNP.TO", "MTY.TO", "KFR.V"]
BUYABLE = ["GURU.TO", "KFR.V"]  # MTY et VNP restent surveillés seulement
TZ = ZoneInfo("America/Toronto")
HEADERS = [
    "date_utc", "date_quebec", "id_operation", "action", "symbole",
    "quantite", "prix_cad", "frais_cad", "montant_brut_cad",
    "cash_apres_cad", "motif", "source_cours", "type_execution",
]


def now_utc():
    return datetime.now(timezone.utc)


def default_state():
    return {
        "version": 2,
        "currency": "CAD",
        "cash": INITIAL_CAD,
        "positions": {},
        "last_prices": {},
        "last_price_dates": {},
        "start_day": None,
        "start_day_equity": INITIAL_CAD,
        "halt_new_buys": False,
        "last_processed_session": {},
        "last_update_utc": None,
    }


def load_state():
    if not STATE.exists():
        return default_state()
    state = json.loads(STATE.read_text(encoding="utf-8"))
    if state.get("version") != 2 or state.get("currency") != "CAD":
        raise ValueError("État incompatible : aucun ordre simulé exécuté")
    return state


def atomic_save(state):
    tmp = STATE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(STATE)


def append_transactions(rows):
    if not rows:
        return
    existing = set()
    if HISTORY.exists():
        with HISTORY.open(encoding="utf-8", newline="") as stream:
            for row in csv.DictReader(stream):
                existing.add(row["id_operation"])
    with HISTORY.open("a", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=HEADERS)
        if stream.tell() == 0:
            writer.writeheader()
        for row in rows:
            if row["id_operation"] not in existing:
                writer.writerow(row)


def market_data():
    result = {}
    for ticker in WATCHLIST:
        try:
            data = yf.Ticker(ticker).history(period="80d", interval="1d", auto_adjust=True)
            data = data.dropna(subset=["Close", "Volume"])
            if len(data) < 23:
                print("Historique insuffisant :", ticker)
                continue
            closes = data["Close"]
            volumes = data["Volume"]
            price = float(closes.iloc[-1])
            if not math.isfinite(price) or price <= 0:
                continue
            session = str(data.index[-1].date())
            fast = float(closes.iloc[-5:].mean())
            slow = float(closes.iloc[-20:].mean())
            prev_fast = float(closes.iloc[-6:-1].mean())
            prev_slow = float(closes.iloc[-21:-1].mean())
            daily_volume = float(volumes.iloc[-1])
            avg_volume = float(volumes.iloc[-21:-1].mean())
            result[ticker] = {
                "price": round(price, 4),
                "session": session,
                "buy": prev_fast <= prev_slow and fast > slow,
                "sell": prev_fast >= prev_slow and fast < slow,
                "momentum": fast > slow and price > fast,
                "volume_ok": avg_volume > 0 and daily_volume >= 1.4 * avg_volume,
                "volume": int(daily_volume),
                "relative_volume": round(daily_volume / avg_volume, 2) if avg_volume else 0,
            }
        except Exception as exc:
            print("Données indisponibles :", ticker, str(exc))
    return result


def equity(state, quotes):
    amount = float(state["cash"])
    for ticker, pos in state["positions"].items():
        price = quotes.get(ticker, {}).get("price", state["last_prices"].get(ticker, pos["entry"]))
        amount += int(pos["qty"]) * float(price)
    return amount


def entry_forbidden(session, local_date):
    # Ne prend pas une cotation datée d'hier pour une exécution d'aujourd'hui.
    return session != local_date


def make_trade(ts, action, ticker, qty, price, fee, cash_after, reason, session):
    return {
        "date_utc": ts.isoformat(),
        "date_quebec": ts.astimezone(TZ).isoformat(),
        "id_operation": f"v2-{session}-{action}-{ticker}",
        "action": action,
        "symbole": ticker,
        "quantite": qty,
        "prix_cad": round(price, 4),
        "frais_cad": round(fee, 2),
        "montant_brut_cad": round(price * qty, 2),
        "cash_apres_cad": round(cash_after, 2),
        "motif": reason,
        "source_cours": "Yahoo Finance / yfinance, historique quotidien ajusté",
        "type_execution": "SIMULATION au dernier cours quotidien (pas un fill marché)",
    }


def render_report(state, quotes, decisions, value):
    import html
    def safe(s):
        return html.escape(str(s))
    rows = []
    for t, p in state["positions"].items():
        px = quotes.get(t, {}).get("price", state["last_prices"].get(t, p["entry"]))
        rows.append(f"<tr><td>{safe(t)}</td><td>{p['qty']}</td><td>{p['entry']:.4f}</td><td>{px:.4f}</td><td>{p['stop']:.4f}</td></tr>")
    body = "".join(rows) or '<tr><td colspan="5">Aucune position</td></tr>'
    decisions_html = "".join(f"<li>{safe(x)}</li>" for x in decisions)
    REPORT.write_text(f'''<!doctype html><html lang="fr"><meta charset="utf-8">
<title>Robot trading V2 — simulation</title><style>body{{font-family:system-ui;max-width:850px;margin:24px auto;padding:20px;background:#f6f8fa;color:#17212d}}main{{background:white;padding:24px;border-radius:14px}}table{{width:100%;border-collapse:collapse}}td,th{{padding:10px;border-bottom:1px solid #ddd;text-align:left}}</style>
<main><h1>Robot trading V2 — 1 000 $ CA fictifs</h1><p><b>Aucun ordre réel</b>. Cours quotidiens possiblement différés; transactions à prix indicatif, sans garantie d'exécution.</p>
<h2>État</h2><p>Valeur estimée : <b>{value:.2f} CAD</b> | Espèces : {state['cash']:.2f} CAD</p>
<p>Frein nouvelles entrées : {"ACTIVÉ" if state['halt_new_buys'] else "inactif"} | Dernière mise à jour UTC : {safe(state['last_update_utc'])}</p>
<h2>Positions</h2><table><tr><th>Titre</th><th>Qté</th><th>Entrée</th><th>Référence</th><th>Stop</th></tr>{body}</table>
<h2>Décisions</h2><ul>{decisions_html}</ul>
<p>Cette V2 ne vérifie pas les nouvelles ni les spreads en direct. Tester d'abord sur une branche isolée.</p></main></html>''', encoding="utf-8")


def main():
    ts = now_utc()
    local_date = str(ts.astimezone(TZ).date())
    state = load_state()
    quotes = market_data()
    if not quotes:
        raise RuntimeError("Aucune cotation valide : état inchangé")
    decisions = []
    transactions = []
    positions = state["positions"]
    # Les signaux quotidiens ne sont utilisables qu'une fois par séance et titre.
    # Pas de traitement intrajournalier prétendant disposer de prix temps réel.
    for t, q in quotes.items():
        state["last_prices"][t] = q["price"]
        state["last_price_dates"][t] = q["session"]
    value_before = equity(state, quotes)
    if state.get("start_day") != local_date:
        state["start_day"] = local_date
        state["start_day_equity"] = value_before
        state["halt_new_buys"] = False

    # Vente prioritaire : stop prédéfini, stop suiveur, ou croisement baissier.
    for ticker, position in list(positions.items()):
        q = quotes.get(ticker)
        if not q or entry_forbidden(q["session"], local_date):
            decisions.append(f"{ticker} : conserver, prix d'aujourd'hui non confirmé")
            continue
        price = q["price"]
        if state["last_processed_session"].get(ticker) == q["session"]:
            continue
        position["highest"] = max(float(position.get("highest", position["entry"])), price)
        # Le stop ne peut jamais être abaissé une fois la position ouverte.
        if position["highest"] >= position["entry"] * 1.08:
            position["stop"] = max(position["stop"], round(position["highest"] * (1 - TRAIL_FRACTION), 4))
        reason = "stop" if price <= position["stop"] else ("croisement baissier" if q["sell"] else "")
        if reason:
            qty = int(position["qty"])
            gross = qty * price
            state["cash"] = round(float(state["cash"]) + gross - FEE_CAD, 2)
            transactions.append(make_trade(ts, "VENTE", ticker, qty, price, FEE_CAD, state["cash"], reason, q["session"]))
            del positions[ticker]
            decisions.append(f"{ticker} : VENTE FICTIVE indicative ({reason}), {qty} à {price:.4f} CAD")
        else:
            decisions.append(f"{ticker} : CONSERVER, stop {position['stop']:.4f} CAD")
        state["last_processed_session"][ticker] = q["session"]

    value_after_sales = equity(state, quotes)
    baseline = max(0.01, float(state["start_day_equity"]))
    if value_after_sales <= baseline * (1 - DAILY_BRAKE_FRACTION):
        state["halt_new_buys"] = True

    for ticker in BUYABLE:
        q = quotes.get(ticker)
        if not q or entry_forbidden(q["session"], local_date):
            continue
        if state["last_processed_session"].get(ticker) == q["session"]:
            continue
        if ticker in positions or not (q["buy"] and q["momentum"] and q["volume_ok"]):
            continue
        if state["halt_new_buys"] or len(positions) >= MAX_POSITIONS:
            decisions.append(f"{ticker} : achat suspendu (frein ou nombre de positions)")
            continue
        price = q["price"]
        stop = round(price * (1 - STOP_MIN_FRACTION), 4)
        risk_budget = value_after_sales * RISK_FRACTION
        per_share_risk = price - stop
        # Budget de risque : frais d'achat + réserve pour vente et glissement hypothétique.
        available_risk = risk_budget - 2 * FEE_CAD - 1.0
        if available_risk <= 0 or per_share_risk <= 0:
            continue
        qty_risk = math.floor(available_risk / per_share_risk)
        qty_capital = math.floor(max(0, float(state["cash"]) - FEE_CAD) / price)
        qty_concentration = math.floor(value_after_sales * MAX_POSITION_FRACTION / price)
        qty = min(qty_risk, qty_capital, qty_concentration)
        if qty < 1:
            decisions.append(f"{ticker} : taille insuffisante selon le risque")
            continue
        state["cash"] = round(float(state["cash"]) - qty * price - FEE_CAD, 2)
        positions[ticker] = {"qty": qty, "entry": price, "stop": stop, "highest": price, "entry_date": q["session"]}
        transactions.append(make_trade(ts, "ACHAT", ticker, qty, price, FEE_CAD, state["cash"], "croisement 5j/20j + volume relatif", q["session"]))
        decisions.append(f"{ticker} : ACHAT FICTIF indicatif {qty} à {price:.4f} CAD, stop {stop:.4f} CAD")
        state["last_processed_session"][ticker] = q["session"]

    state["last_update_utc"] = ts.isoformat()
    # Important : écriture CSV avant l'état ; une reprise garde des IDs d'opération déterministes.
    append_transactions(transactions)
    atomic_save(state)
    value = equity(state, quotes)
    render_report(state, quotes, decisions, value)
    for d in decisions:
        print(d)
    print(f"V2 éducative : portefeuille estimé {value:.2f} CAD, cash {state['cash']:.2f} CAD, nouvelles lignes {len(transactions)}")


if __name__ == "__main__":
    main()
