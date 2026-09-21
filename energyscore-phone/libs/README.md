# SDK Samsung Health Data à déposer ici

Ce module a besoin du fichier `.aar` du **Samsung Health Data SDK** (ex: `health-data-api-1.1.0.aar`)
pour compiler. Il n'est pas distribué sur Maven — Samsung ne le publie qu'en téléchargement direct,
réservé aux comptes développeur.

**Attention à ne pas confondre deux comptes différents :**
- **Compte Google Play / developer.android.com** (celui déjà utilisé pour Android Studio) →
  ne donne **pas** accès au SDK Samsung, ce sont deux portails indépendants.
- **Compte Samsung** sur **developer.samsung.com** → c'est celui-là qu'il faut, un Samsung
  Account classique suffit (le même que pour un Galaxy Watch/téléphone), aucun frais ni
  partenariat requis pour la lecture en mode développeur.

## Marche à suivre

1. Se connecter avec un compte Samsung sur https://developer.samsung.com (pas le compte Google
   Play Console)
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

`MainActivity.kt` contient le vrai appel SDK (pas un squelette) : récupération du store,
permission, filtre temporel, lecture, envoi à la montre — reconstruit à partir d'exemples de code
officiels réels trouvés pour un type de donnée équivalent (fréquence cardiaque). Deux détails
précis restent à confirmer une fois le `.aar` en place, marqués `TODO` dans le fichier :
- le nom exact du champ de valeur sur `EnergyScoreType` (`DataType.EnergyScoreType.SCORE` est une
  supposition raisonnable mais non vérifiée contre le javadoc) ;
- si `requestPermissions` s'utilise directement comme fonction suspend ou demande un callback.

Android Studio règle les deux en quelques secondes via l'autocomplétion dès que le SDK est
importé — pas besoin de redemander, juste corriger si le nom proposé diffère.
