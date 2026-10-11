# Carry trade AUD/JPY (2002 – 2026)

Backtest simple du carry trade le plus classique : emprunter en yen pour placer en
dollar australien, via un forward 1 mois roulé chaque mois.

**Résultats :** 6,1 % par an (dont 3,3 % de carry et 3,0 % de change), Sharpe 0,46,
skewness −0,93, perte maximale −42 % (2008–2009).
Rapport complet : [Rapport_Carry_AUDJPY.pdf](Rapport_Carry_AUDJPY.pdf)

## Méthode
- Données FRED : AUD/USD et USD/JPY quotidiens, taux interbancaires 3 mois (OECD)
- Rendement mensuel = variation du cours AUD/JPY + (taux AUD − taux JPY) / 12
- Coûts : 2 points de base par roulement

## Lancer
```bash
pip install pandas matplotlib
python carry_audjpy.py
```
Les résultats s'affichent dans la console, les graphiques sont enregistrés dans `output/`.

---
Alexandre Magnan-Dupont — EDHEC Business School / ESTP
