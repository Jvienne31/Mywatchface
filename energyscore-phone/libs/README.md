# SDK Samsung Health Data à déposer ici

Ce module a besoin du fichier `.aar` du **Samsung Health Data SDK** (ex: `health-data-api-1.1.0.aar`)
pour compiler. Il n'est pas distribué sur Maven — Samsung ne le publie qu'en téléchargement direct,
réservé aux comptes développeur.

## Marche à suivre

1. Créer/se connecter à un compte sur https://developer.samsung.com
2. Aller sur https://developer.samsung.com/health/data (section "Samsung Health Data SDK")
3. Télécharger le SDK — le zip contient le `.aar`, le javadoc, la licence, et un projet
   d'exemple ("Hello SDK") avec du vrai code de lecture de données (permissions, requêtes).
4. Copier le `.aar` ici : `energyscore-phone/libs/`
5. Dans l'appli **Samsung Health** du téléphone : Paramètres → à propos → (menu développeur) →
   activer **"Developer mode for data read"**. Ce mode permet de lire ses propres données
   (dont `EnergyScoreType`) sans passer par le programme partenaire Samsung, tant que l'appli
   reste un usage personnel non distribué publiquement.
6. Rebuild le module `energyscore-phone`.

## Pourquoi ce n'est pas déjà fait automatiquement

- Le SDK n'est accessible qu'après connexion à un compte développeur Samsung — impossible à
  télécharger depuis cet environnement (accès direct à developer.samsung.com bloqué ici).
- La licence Samsung ne permet pas de redistribuer le `.aar` dans un dépôt Git — c'est pour ça
  qu'il est dans `.gitignore`.

## État du code dans ce module

`MainActivity.kt` contient déjà toute la logique autour (permission UI, synchronisation vers la
montre via le Data Layer Wear OS, affichage du statut) — seule la fonction `readEnergyScore()`
est un squelette à finaliser une fois le SDK réel disponible, en s'inspirant du projet d'exemple
"Hello SDK" fourni dans le zip téléchargé à l'étape 3.
