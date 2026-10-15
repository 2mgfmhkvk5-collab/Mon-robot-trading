# Robot iPhone / iPad — simulation uniquement

Ce projet n'a AUCUN accès à Disnat. Il ne passe aucun ordre réel.

## Installation depuis Safari sur iPhone/iPad

1. Créez un compte sur https://github.com (offre gratuite).
2. Créez un dépôt **public** nommé `robot-trading-demo` (sans données personnelles). Les transactions simulées et le portefeuille seront publics. Un dépôt privé nécessite de vérifier les conditions de GitHub Pages selon votre offre.
3. Dans Safari, ouvrez votre dépôt et utilisez « Ajouter un fichier » → « Téléverser des fichiers ». Décompressez le ZIP dans l'app Fichiers et importez `robot.py`, `requirements.txt`, `state.json` et le dossier `docs` avec son fichier `index.html` (ce dernier est généré après la première exécution). Importez aussi `.github/workflows/robot.yml` en respectant exactement l'arborescence. Sur iPhone, l'interface peut exiger « Demander le site pour ordinateur » et il peut être plus simple de créer les dossiers avec « Create new file » et leur chemin complet.
4. Dans **Settings → Actions → General**, vérifiez que les Actions sont autorisées et que **Workflow permissions** est réglé sur **Read and write permissions**.
5. Ouvrez **Actions → Simulation trading quotidienne → Run workflow** pour lancer un essai. Si le lancement échoue, ouvrez le journal de l'Action. Ne supposez pas qu'un ordre a été exécuté.
6. Ouvrez **Settings → Pages → Build and deployment → Deploy from a branch → main → /docs → Save**. Le lien Pages sera affiché dans Settings → Pages après publication. Il peut prendre quelques minutes à apparaître.
7. Dans Safari, ouvrez ce lien et faites **Partager → Sur l'écran d'accueil** pour un accès direct.

## Limites importantes

- Exécution programmée en semaine à 23 h 30 UTC, après la clôture américaine; GitHub Actions peut être retardé ou désactivé en cas d'inactivité.
- Les données Yahoo Finance peuvent être manquantes, retardées ou révisées. L'historique est ajusté et les cours sont approximatifs.
- Les ordres virtuels sont calculés à l'ouverture du jour suivant un signal; le système ne vérifie pas toutes les conditions intrajournalières et n'est pas un backtest fiable.
- Le stop de 6 % est vérifié à la clôture, puis la vente virtuelle a lieu à l'ouverture suivante : il ne garantit PAS une perte limitée à 6 %.
- Le taux USD/CAD est volontairement fixé à 1,38 pour cette démonstration. Les frais sont hypothétiques (1 CAD/ordre), et le spread, la liquidité et la fiscalité ne sont pas modélisés.
- Les symboles de départ sont des exemples et peuvent être au-dessus de 5 USD ou changer de secteur. Seuls les achats dont le cours du signal est entre 0,01 et 5 USD sont envisagés.
- Les historiques de prix ne prouvent pas qu'une stratégie sera rentable. Aucun service gratuit n'est garanti permanent ou sans limites.
- Aucune API Disnat n'est utilisée. Ne partagez jamais vos identifiants bancaires ou codes 2FA avec un robot.
