# Météo PV 43

Appli de l'équipe PV : sommes de températures et pluie des 13 stations Météo-France de Haute-Loire.

- **Données** : Météo-France, « Données climatologiques de base – quotidiennes » (data.gouv.fr), téléchargées chaque matin.
- **Calculs** : identiques au fichier Excel de l'équipe (base 0 bornée 0–18 °C depuis le 1er février, base 6 avec TX plafonnée à 30 °C depuis le 20/04, 01/05, 10/05, 20/05, pluie, ETP AP3C).
- **Accès** : les données sont chiffrées dans la page. Sans le mot de passe, rien n'est lisible.

## Changer le mot de passe

Settings → Secrets and variables → Actions → `PV43_MDP` → Update. Puis Actions → « Mise à jour quotidienne » → Run workflow.
Chacun devra saisir le nouveau mot de passe à la prochaine ouverture.

## Lancer une mise à jour à la main

Actions → « Mise à jour quotidienne » → Run workflow.

## Organisation

- `scripts/calc.js` : les formules (sommes, pluie, ETP)
- `scripts/template.html` : l'affichage
- `scripts/extract.py` : lecture du fichier Météo-France
- `scripts/build.py` : repères et chiffrement
- `scripts/update.sh` : téléchargement + construction de l'appli dans `site/`
- `static/` : icônes, manifeste et mode hors connexion
- `.github/workflows/mise-a-jour.yml` : la tâche quotidienne
