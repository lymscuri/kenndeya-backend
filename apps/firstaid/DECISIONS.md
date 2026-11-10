# Décisions — apps/firstaid

Journal court des règles qui ne sont pas dans les protocoles eux-mêmes, pour le médecin relecteur.

## 2026-11-10 — Règle de routage du classifieur

Le classifieur (POST `/api/v1/firstaid/classify/`) ne rédige aucune consigne : il choisit un
identifiant de protocole publiable, ou `none`. Son prompt porte, pour chaque candidat, le titre
et la description du protocole, et la règle suivante :

> L'âge, la grossesse, la cause (chute, malaise, accident) ou le lieu ne changent pas le scénario ;
> seul compte l'état de la personne. Si la personne est inconsciente, ne réagit pas ou ne se
> réveille pas et que sa respiration n'est pas décrite, choisir `unconscious_breathing` : son
> parcours vérifie ensuite la respiration. Si la personne est consciente, ou si la situation est
> autre (saignement, étouffement, douleur, malaise sans perte de connaissance…) et qu'aucun
> scénario de la liste ne la décrit, répondre `none`.

La phrase citant `unconscious_breathing` n'est émise que si ce protocole fait partie des
candidats publiables du moment ; le reste de la règle reste vrai quand d'autres protocoles seront
ajoutés. Motivation : le texte « ma femme est enceinte et elle ne se réveille pas » était classé
`none` au lieu de `unconscious_breathing`.

## 2026-11-10 — Entrée « saignement abondant » dans la règle de routage

Même mécanique conditionnelle que pour `unconscious_breathing` : si `severe_bleeding` fait partie
des candidats publiables, le prompt ajoute :

> Si la personne saigne abondamment ou sans arrêt (le sang coule ou gicle, « beaucoup de sang »),
> choisir `severe_bleeding`, quelle que soit la cause ou la partie du corps.

et retire « saignement » des exemples de situations menant à `none`. Quand `severe_bleeding` n'est
pas publiable, la règle reste celle du 2026-11-10 ci-dessus, « saignement » compris dans les
exemples de `none`.
