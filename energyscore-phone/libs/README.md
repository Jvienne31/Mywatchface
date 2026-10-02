# Santé Sync : SDK Samsung Health Data

L'appli téléphone (`energyscore-phone`) lit Samsung Health avec le **Samsung Health Data SDK**
(fichier `.aar`). Elle envoie les valeurs à l'appli montre (`energyscore-watch`), qui les
propose en complications dans Prisme et dans tout autre cadran.

Les deux applis ont le même identifiant `com.jvienne.santesync` et la même clé, ce
qu'exige le Data Layer Wear OS. Installez l'APK téléphone sur le téléphone et l'APK montre
sur la montre.

## D'où vient le .aar

- **Compilation automatique (GitHub Actions, `build-sante.yml`)** : copie du SDK 1.0.0
  publiée dans le dépôt open source `the-momentum/open_wearables_android_sdk`. Elle est figée
  sur un commit et vérifiée par SHA-256. Elle n'est pas versionnée ici.
- **Copie officielle** :
  1. Connectez-vous avec votre compte Samsung sur https://developer.samsung.com/health/data.
  2. Téléchargez le SDK.
  3. Copiez le `.aar` dans ce dossier, puis compilez dans Android Studio.

  Le fichier est ignoré par Git : la licence Samsung interdit de le redistribuer.

## Sur le téléphone : mode développeur Samsung Health

1. Ouvrez *Samsung Health > Paramètres > À propos de Samsung Health*.
2. Touchez une dizaine de fois le numéro de version.
3. Activez **Developer mode for data read**.

Ce mode permet de lire ses propres données sans accord partenaire avec Samsung, pour un
usage personnel.

## Données transmises (26 complications)

Toutes sont définies dans `energyscore-watch/tools/gen_metrics.py`. Ce fichier génère le code
des deux applis.

| Famille | Données |
|---|---|
| Scores | énergie, sommeil |
| Sommeil | durée (avec l'objectif) |
| Activité | pas (avec l'objectif), distance, calories actives (avec l'objectif) et totales, temps actif (avec l'objectif), étages |
| Alimentation | eau (avec l'objectif), calories consommées (avec l'objectif) |
| Cœur | fréquence cardiaque (dernière, min et max du jour), SpO2, tension |
| Mesures | température cutanée et corporelle, glycémie |
| Corps | poids, masse grasse, muscle squelettique, IMC |
| Dernière séance | durée, distance, VO2 max |

Le code de lecture (`HealthReader.kt`) suit les signatures exactes du SDK 1.0.0, relevées
avec `javap` dans le `.aar`.

La synchronisation se fait au lancement de l'appli, avec le bouton, puis automatiquement
toutes les 30 minutes (WorkManager).
