# Mywatchface : état du projet

Mise à jour : 3 octobre 2026. Branche de travail : `claude/sweet-johnson-122okj`.

## Modules

| Dossier | Quoi | État |
|---|---|---|
| `prisme/` | **Cadran Prisme** (WFF v2, sans code) : 18 palettes, 7 emplacements, 2 dômes, AOD, réglage des secondes, batterie rouge sous 20 % | Fonctionne sur la Watch8 Classic (validé le 3 octobre 2026). Doc : `prisme/docs/GUIDE.md` |
| `energyscore-phone/` | **Santé Sync, téléphone** : lit Samsung Health (Health Data SDK) et envoie à la montre toutes les 30 min | Fonctionne en mode développeur Samsung Health |
| `energyscore-watch/` | **Santé Sync, montre** : 26 complications, mesures en direct (Health Services), toucher → Samsung Health, tuile « Santé du jour », écran en Compose | Fonctionne |
| `race/` | Reproduction de S4U Race (exercice) | **Ne pas publier** : copie d'un cadran existant |
| `concepts/` | Maquettes : Prisme, Méridien (luxe), Strate, Palettes, Nocturne | Méridien et Strate gardés pour plus tard |
| `app/` | Ancien projet | — |

Les APK sont construits par GitHub Actions : `build-prisme.yml`, `build-sante.yml` et
`build-race.yml`. Chaque exécution donne un APK à télécharger dans l'onglet Actions.

Le savoir-faire acquis est consigné dans le skill `.claude/skills/watchface-expert/SKILL.md`.
Claude Code le charge automatiquement dans ce dépôt.

## Ce qu'on a établi sur Samsung Health

Chaque point est vérifié, sur la montre ou dans la documentation.

- **Score d'énergie et score de sommeil.** Samsung propose bien une complication, mais
  réservée à ses propres cadrans : elle est absente de la liste proposée à Prisme, même avec
  tous les types de complication acceptés.
- **Health Data SDK.** Il est prévu pour le téléphone uniquement (« Target device: Android
  smartphones », notes de version 1.1.0). Testé sur la montre : erreur 3000 « Samsung
  Health is not installed ».
- **Données disponibles sur la montre.** Health Services (Wear OS) donne pas, distance,
  calories et étages ; Health Sensor SDK donne les capteurs bruts. Aucun des deux ne donne de
  score.
- **Solution retenue.** L'appli téléphone lit le SDK puis transmet à la montre par le Data
  Layer. Le Data Layer exige le même applicationId et la même signature des deux côtés.

## Publication, plus tard

### Prisme (Play Store et Galaxy Store)

- [ ] Compte développeur Google Play (25 $, une fois).
- [ ] Clé de signature de production : à créer et à garder hors du dépôt. Les APK actuels
      sont signés avec une clé debug versionnée.
- [ ] Construire un AAB en release, avec versionCode et versionName.
- [ ] Fiche : titre, descriptions FR et EN, captures (montre et 18 palettes), icône
      512 × 512, image de présentation.
- [ ] Vérifier les exigences Google pour les cadrans WFF : format, aperçu, pas de code.
- [ ] Galaxy Store : compte vendeur Samsung, conditions actuelles pour les cadrans tiers à
      vérifier.
- [ ] Option : appli téléphone compagnon, qui aide à installer le cadran sur la montre.

### Santé Sync (une seule fiche pour le téléphone et la montre)

- [ ] **Accord partenaire Samsung Health Data SDK** : obligatoire pour distribuer, car le mode
      développeur ne sert qu'aux tests. Le téléchargement officiel du SDK demande un compte
      Samsung **business**.
- [ ] Remplacer la copie publique du SDK 1.0.0 (CI) par le SDK officiel 1.1.0 : il ajoute
      l'apnée du sommeil et le rythme cardiaque irrégulier.
- [ ] Politique de confidentialité, section « Sécurité des données », déclaration des applis
      de santé, justification de `ACTIVITY_RECOGNITION`.
- [ ] Même clé de production pour l'APK téléphone et l'APK montre.

## Idées en attente

- Second cadran : Méridien ou Strate (maquettes dans `concepts/`), après Prisme.
- Toucher l'heure pour ouvrir le réveil : écarté (pas de double toucher en WFF, un toucher simple se déclenche par accident).
- Voir aussi la section « Idées » du skill.
