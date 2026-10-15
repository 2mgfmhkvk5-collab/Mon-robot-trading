# Mon robot trading — simulation

Simulation éducative de 1 000 $ CAD, sans connexion à Disnat et sans ordres réels.

## Installation depuis Safari sur iPhone
1. Ouvrir le dépôt GitHub `Mon-robot-trading`, onglet Code.
2. Charger `robot.py`, `requirements.txt` et `README.md` à la racine du dépôt (menu Add file / Upload files).
3. Remplacer `.github/workflows/main.yml` par celui de cette archive. Ne pas créer un second fichier `main.yml`.
4. Enregistrer (Commit changes).
5. Dans Actions, ouvrir « Robot trading - simulation », puis « Run workflow » pour tester.
6. Consulter `index.html` et `etat.json` dans le dépôt après une exécution réussie.

Le fichier `.github/workflows/main.yml` exécute la simulation les jours ouvrables à 16 h 30 UTC, soit 12 h 30 au Québec durant l'heure d'été et 11 h 30 durant l'heure d'hiver. Les horaires GitHub ne sont pas garantis à la minute.

## Stratégie et limites
- Signal : croisement des moyennes mobiles de clôture 5 et 20 jours.
- Titres canadiens suivis pour les ordres : SHOP.TO, VNP.TO, GURU.TO, MTY.TO. NVDA est observé mais non négocié, pour éviter les erreurs de conversion USD/CAD.
- Taille maximum par nouvelle position : 20 % de la valeur du portefeuille.
- Vente simulée : signal inverse, baisse de 8 % ou hausse de 15 % depuis le prix d'entrée, évalués uniquement à l'exécution quotidienne.
- Pas de vente à découvert, levier ou marge.
- Les frais, impôts, slippage et changements de devise ne sont pas simulés. Les prix historiques Yahoo Finance ne sont pas garantis et peuvent être différés.
- Les données de portefeuille sont enregistrées dans le dépôt : garder le dépôt privé si souhaité.
- Le robot ne doit jamais recevoir des identifiants de courtage.

## Tableau de bord
`index.html` est généré après la première exécution. Ouvrir ce fichier depuis GitHub pour voir le HTML brut; pour un tableau de bord web rendu, activer GitHub Pages uniquement si l'exposition publique de ces données est acceptable. Le fichier `etat.json` fournit également le solde et les positions.

## Attention
Ne pas mettre en production réelle. La stratégie n'est pas validée par backtest, les arrêts de pertes ne sont pas garantis entre deux exécutions, et l'automatisation GitHub Actions peut échouer ou être retardée.
