# -*- coding: utf-8 -*-
"""
CARRY TRADE AUD/JPY - version simple
Alexandre Magnan-Dupont

Le carry trade le plus connu : on emprunte en yen (taux tres bas) pour placer
en dollar australien (taux plus eleve). Chaque mois on achete AUD/JPY a 1 mois
et on regarde ce que ca rapporte.

Besoin uniquement de pandas et matplotlib. Lance le script, puis copie le bloc
"RESULTATS" affiche dans la console. Les graphiques sont dans le dossier output/.
"""
import os
import ssl
import urllib.request

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import pandas as pd

START = "1999-01-01"
COST_BPS = 2          # cout de roulement du forward chaque mois (2 bp)

# Series FRED
SERIES = {
    "AUDUSD": "DEXUSAL",            # USD pour 1 AUD (quotidien)
    "USDJPY": "DEXJPUS",            # JPY pour 1 USD (quotidien)
    "taux_AUD": "IR3TIB01AUM156N",  # taux 3 mois Australie (mensuel, %)
    "taux_JPY": "IR3TIB01JPM156N",  # taux 3 mois Japon (mensuel, %)
}

CRISES = {
    "Crise financiere (sept.-dec. 2008)": ("2008-09", "2008-12"),
    "Covid (fevr.-mars 2020)": ("2020-02", "2020-03"),
    "Debouclage du carry yen (juil.-aout 2024)": ("2024-07", "2024-08"),
}

# "ME" = fin de mois depuis pandas 2.2, "M" avant
MOIS = "ME" if tuple(int(x) for x in pd.__version__.split(".")[:2]) >= (2, 2) else "M"


# ----------------------------------------------------------------------------
# 1. Donnees : lues dans data/ (deja telechargees), sinon telechargees sur FRED
# ----------------------------------------------------------------------------
def load(series_id):
    path = os.path.join("data", series_id + ".csv")
    dl = os.path.join(os.path.expanduser("~/Downloads"), series_id + ".csv")
    if not os.path.exists(path) and os.path.exists(dl):
        path = dl
    if not os.path.exists(path):
        os.makedirs("data", exist_ok=True)
        url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=" + series_id
        try:
            import certifi
            ctx = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            ctx = ssl.create_default_context()
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 Chrome/129.0"})
        try:
            with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
                open(path, "w").write(r.read().decode())
        except Exception:
            raise SystemExit("Impossible de telecharger " + series_id +
                             ". Ouvre ce lien dans ton navigateur puis relance : " + url)
    df = pd.read_csv(path, na_values=".")
    s = pd.Series(pd.to_numeric(df.iloc[:, 1], errors="coerce").values,
                  index=pd.to_datetime(df.iloc[:, 0]))
    return s.dropna()


audusd = load(SERIES["AUDUSD"])
usdjpy = load(SERIES["USDJPY"])
spot = (audusd * usdjpy).dropna()                       # AUD/JPY = JPY pour 1 AUD
spot = spot.loc[START:].resample(MOIS).last()           # dernier cours du mois

taux = pd.DataFrame({"AUD": load(SERIES["taux_AUD"]),
                     "JPY": load(SERIES["taux_JPY"])}) / 100
taux.index = taux.index + pd.offsets.MonthEnd(0)
taux = taux.loc[START:].ffill(limit=3)

data = pd.DataFrame({"spot": spot}).join(taux).dropna()

# ----------------------------------------------------------------------------
# 2. Backtest : chaque fin de mois t, on achete AUD/JPY a 1 mois
#    Rendement du mois t+1 = variation du spot + differentiel de taux / 12
# ----------------------------------------------------------------------------
diff = data["AUD"] - data["JPY"]                         # differentiel de taux
res = pd.DataFrame({
    "spot": data["spot"].pct_change(),                   # gain/perte de change
    "carry": diff.shift(1) / 12,                         # taux connu en t, gagne en t+1
})
res["couts"] = -COST_BPS / 1e4
res = res.dropna()
res["total"] = res["spot"] + res["carry"] + res["couts"]

r = res["total"]
richesse = (1 + r).cumprod()
drawdown = richesse / richesse.cummax() - 1

stats = {
    "Periode": f"{r.index[0]:%m/%Y} - {r.index[-1]:%m/%Y}",
    "Rendement annualise": f"{r.mean() * 12:.1%}",
    "  dont carry (taux)": f"{res['carry'].mean() * 12:.1%}",
    "  dont spot (change)": f"{res['spot'].mean() * 12:.1%}",
    "  dont couts": f"{res['couts'].mean() * 12:.1%}",
    "Volatilite annualisee": f"{r.std() * 12 ** 0.5:.1%}",
    "Ratio de Sharpe": f"{r.mean() / r.std() * 12 ** 0.5:.2f}",
    "Skewness (mensuel)": f"{r.skew():.2f}",
    "Perte maximale (max drawdown)": f"{drawdown.min():.1%}",
    "Pire mois": f"{r.min():.1%} ({r.idxmin():%m/%Y})",
    "Meilleur mois": f"{r.max():.1%} ({r.idxmax():%m/%Y})",
    "% de mois positifs": f"{(r > 0).mean():.0%}",
    "Differentiel de taux moyen": f"{diff.mean():.2%}",
    "Differentiel actuel": f"{diff.iloc[-1]:.2%} ({diff.index[-1]:%m/%Y})",
}
for nom, (a, b) in CRISES.items():
    x = r.loc[a:b]
    stats[nom] = f"{(1 + x).prod() - 1:+.1%}" if len(x) else "n.d."

# ----------------------------------------------------------------------------
# 3. Graphiques
# ----------------------------------------------------------------------------
os.makedirs("output", exist_ok=True)
BLEU, ORANGE, VERT, GRIS = "#2a78d6", "#eb6834", "#1baf7a", "#52514e"
plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": "#e4e3df", "font.size": 10})

fig, ax = plt.subplots(figsize=(9, 4.5))
for col, c, nom in [("carry", BLEU, "Carry (differentiel de taux)"),
                    ("total", VERT, "Total"), ("spot", ORANGE, "Spot AUD/JPY")]:
    cum = (1 + res[col]).cumprod() - 1
    ax.plot(cum.index, cum, color=c, lw=2, label=f"{nom} : {cum.iloc[-1]:+.0%}")
for a, b in CRISES.values():
    ax.axvspan(pd.Timestamp(a), pd.Timestamp(b) + pd.offsets.MonthEnd(0), color="#e4e3df")
ax.axhline(0, color=GRIS, lw=0.8)
ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
ax.set_title("Carry trade AUD/JPY : rendement cumule", loc="left", fontweight="bold")
ax.legend(frameon=False, loc="upper left")
fig.tight_layout()
fig.savefig("output/1_rendement_cumule.png", dpi=150)

fig, ax = plt.subplots(figsize=(9, 3))
ax.fill_between(drawdown.index, drawdown, 0, color=ORANGE, alpha=0.35)
ax.plot(drawdown.index, drawdown, color=ORANGE, lw=1.2)
ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
ax.set_title("Perte depuis le plus haut (drawdown)", loc="left", fontweight="bold")
fig.tight_layout()
fig.savefig("output/2_drawdown.png", dpi=150)

fig, ax = plt.subplots(figsize=(9, 3.5))
ax.plot(data.index, data["AUD"], color=BLEU, lw=2, label="Taux 3M Australie")
ax.plot(data.index, data["JPY"], color=ORANGE, lw=2, label="Taux 3M Japon")
ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
ax.set_title("L'ecart de taux, source du carry", loc="left", fontweight="bold")
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig("output/3_taux.png", dpi=150)

# ----------------------------------------------------------------------------
# 4. Resultats a copier
# ----------------------------------------------------------------------------
print("\n========== RESULTATS (a copier) ==========")
for k, v in stats.items():
    print(f"{k:<45} {v}")
print("==========================================")
print("Graphiques enregistres dans le dossier output/")
