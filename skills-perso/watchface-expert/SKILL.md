---
name: watchface-expert
description: Expert terrain des cadrans Galaxy Watch / Wear OS (Watch Face Format) et des applis compagnons de complications. Règles constatées sur montre réelle (rendu WFF, emplacements, toucher, AOD), accès aux données Samsung Health (score d'énergie, sommeil…), Health Services, Data Layer téléphone-montre, chaîne générateur Python → validateur → CI GitHub → APK, publication. À utiliser pour concevoir, coder, déboguer ou publier un cadran ou une appli de complications, ou pour répondre à « peut-on afficher telle donnée sur un cadran ? ». Complète le skill samsung-watchface (bases WFF, mémoire, design, Watch Face Studio).
---

# Expert terrain : cadrans Wear OS et données santé

Ce skill rassemble ce qu'on a **appris en construisant et en testant** un vrai cadran (Prisme)
et une appli de complications santé (Santé Sync) sur une Galaxy Watch8 Classic (Wear OS 6) et
sur l'émulateur.

Les bases (versions WFF, structure du projet, budget mémoire, règles de design, Watch Face
Studio) sont dans le skill **samsung-watchface** : le charger aussi.

Règle d'or : **ce qui est marqué [montre] a été constaté sur l'appareil et prime sur la
documentation.**

## Références à charger selon le besoin

| Fichier | Quand le lire |
|---|---|
| `references/wff-regles-terrain.md` | Pour écrire ou déboguer le XML d'un cadran : rendu, masques, emplacements, toucher, AOD |
| `references/donnees-sante.md` | Pour toute question « peut-on afficher X ? » ; API Samsung Health Data SDK et Health Services avec leurs signatures exactes |
| `references/appli-complications.md` | Pour une appli qui fournit des complications ou relie le téléphone et la montre (architecture, manifeste, pièges, publication) |
| `references/chaine-outils.md` | Générateur, maquettes, validateur, CI GitHub, mesure de l'AOD, contraintes réseau |
| `scripts/wff.py` | Bibliothèque Python qui émet à la fois le XML WFF et un aperçu SVG. À copier dans le projet |

## Méthode qui a marché

1. **Maquette avant code.** L'utilisateur choisit sur images, pas sur APK.
   - Rendre la version actuelle et 2 ou 3 variantes côte à côte (SVG, puis Playwright, puis
     PNG).
   - Montrer aussi le cadran sur une montre. Valider le style avant d'écrire le XML.
2. **Ne jamais écrire le XML WFF à la main.** Utiliser un générateur Python (`scripts/wff.py`)
   qui produit le XML et un aperçu SVG à partir des mêmes primitives. L'aperçu sert de
   contrôle visuel et devient l'image `preview.png` du paquet.
3. **Valider** le XML avec le validateur officiel `google/watchface`, à la version déclarée,
   à chaque génération.
4. **Construire en CI** (GitHub Actions, Java 17). Un APK debug est signé avec une clé debug
   **versionnée**, pour que les mises à jour s'installent par-dessus. L'utilisateur installe
   avec Wear Installer ou `adb install -r`.
5. **Tester sur la montre réelle** et faire envoyer des captures. L'émulateur ment sur certains
   points : moteur des emplacements, Samsung Health absent.
6. **Mesurer l'AOD** (moins de 15 % de pixels allumés) à chaque changement.
7. **Avant d'affirmer une limite, la vérifier** : documentation officielle, puis test sur
   l'appareil. Une affirmation trop rapide (« impossible ») a été démentie par l'utilisateur ;
   un test à 10 minutes l'aurait évitée.

## Les 12 règles qui coûtent le plus cher si on les ignore

1. **[montre]** Les dégradés (`LinearGradient`, `RadialGradient`) ne sont pas rendus. Utiliser
   des aplats et des PNG translucides.
2. **[montre]** `Font > Outline` n'est pas rendu. Faire le contour avec 12 copies décalées en
   cercle, puis le texte par-dessus.
3. **[montre]** `dashIntervals` dérive sur les arcs. Dessiner une `Line` par graduation.
4. **[montre]** La branche `Complication type="EMPTY"` n'est **pas dessinée**. Dessiner la
   donnée par défaut **hors** de l'emplacement. Chaque type non vide redessine d'abord le fond
   (patch), puis la donnée de la source.
5. Un emplacement doit accepter **tous les types** (`SHORT_TEXT LONG_TEXT RANGED_VALUE
   GOAL_PROGRESS MONOCHROMATIC_IMAGE SMALL_IMAGE PHOTO_IMAGE WEIGHTED_ELEMENTS EMPTY`). Sinon
   des sources disparaissent du sélecteur.
6. Les x, y, width et height des `Part*`, `Group` et `ComplicationSlot` doivent être des
   **entiers**.
7. Un `ColorOption` porte **au plus 5 couleurs**. Dériver les autres par transparence.
8. Les gabarits de texte n'ont pas de `%%` fiable : mettre le « % » dans un `PartText`
   séparé.
9. `Launch target` accepte un raccourci système ou un **nom de paquet**. Le placer sur un
   `Group` de la taille de la zone sensible. Rendre **chaque donnée touchable**.
10. **Score d'énergie et score de sommeil** : la complication Samsung est réservée à ses
    propres cadrans. Le Health Data SDK ne fonctionne **que sur le téléphone** ; sur la
    montre il renvoie l'erreur 3000. Il faut donc une appli téléphone plus le Data Layer.
11. Le Data Layer exige le **même applicationId et la même clé** sur le téléphone et la
    montre.
12. Une appli montre sans activité `LAUNCHER` semble ne pas s'installer, puisqu'elle n'a pas
    d'icône. Toujours fournir un écran et une icône adaptative.

## Ce que l'utilisateur attend (retours réels)

- **Lisibilité avant tout**, sur une montre et sans lunettes.
  - Données en grand : environ 36 à 48 px sur 438.
  - Chiffres de l'heure en un seul bloc, avec un contour contrasté, pas coupés en deux
    couleurs.
- **Personnalisation forte** : 15 à 20 palettes tendance, chaque emplacement modifiable.
- **Le cadran doit se comporter comme ceux de Samsung** : toucher une donnée ouvre l'appli.
- **Être honnête sur ce qui est vérifié ou non** : donner le lien de l'APK, ce qui a changé et
  ce qu'il faut vérifier sur la montre.
