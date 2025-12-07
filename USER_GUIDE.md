# 📘 Guide Utilisateur Complet - Polymarket Scanner

Ce guide explique comment tirer le meilleur parti de votre **Scanner Polymarket**. Le bot est conçu pour identifier des inefficacités de marché grâce à plusieurs stratégies distinctes.

---

## 🎯 1. Scanner (Surveillance Générale)

L'onglet principal pour une vue d'ensemble du marché.

-   **Objectif** : Voir tout ce qui bouge.
-   **Utilisation** :
    -   Par défaut, **tous les marchés** sont affichés (Filtres à 0).
    -   Utilisez le bouton "Paramètres" en haut à droite pour filtrer par :
        -   **Volume** : Pour éviter les marchés illiquides.
        -   **Score** : Notre algorithme propriétaire (0-10) qui note l'activité.
        -   **Whales** : Filtrer les marchés où les "gros poissons" sont actifs.
-   **Astuce** : C'est ici que vous trouverez les paris sportifs (NBA, Football) en faisant défiler la liste, car ils sont souvent moins bien notés que la politique mais offrent de bonnes opportunités.

---

## ⚖️ 2. Équilibrage (45-55%)

Stratégie de "Coin Flip" ou de marchés incertains.

-   **Objectif** : Trouver des marchés où le prix est très proche de 50cts (0.50$).
-   **Pourquoi ?** :
    -   Idéal pour le **market making** (fournir de la liquidité des deux côtés).
    -   Souvent signe d'un événement très disputé où la volatilité va exploser.
-   **Fonctionnement** : N'affiche que les marchés où le prix du YES est compris entre 0.45$ et 0.55$.

---

## 🔎 3. Pro Insights (Stratégies Avancées)

Le cœur de l'analyse "Smart Money". Sélectionnez une sous-stratégie en cliquant sur les boutons colorés :

### 🐋 A. Whale (Suivre l'argent intelligent)
-   **Le Signal** : "WHALE BUY: YES/NO".
-   **Logique** : Le bot détecte un volume anormalement élevé (>25k$ en 24h) sur un marché.
-   **Action** : Si une baleine achète massivement du YES, c'est souvent qu'elle a une information ou une conviction forte. **Copy-trading**.

### 🛡️ B. Safe Yield (Arbitrage & Hedge)
-   **Le Signal** : "SAFE YIELD: +X%".
-   **Logique** : La somme des prix de toutes les issues est inférieure à 1.00$ (ou 0.98$ pour couvrir les frais).
-   **Exemple** : YES à 40cts + NO à 55cts = 95cts.
-   **Action** : Achetez **TOUTES les issues** (YES et NO). Vous payez 0.95$ pour recevoir 1.00$ quoi qu'il arrive. **Profit garanti sans risque**.

### 🦅 C. Scalp (Spread Inefficace)
-   **Le Signal** : "SCALP SPREAD: X cts".
-   **Logique** : L'écart entre le meilleur acheteur (Bid) et le meilleur vendeur (Ask) est trop grand (> 3cts).
-   **Action** : Placez un ordre d'achat juste au-dessus du meilleur Bid, et un ordre de vente juste en dessous du meilleur Ask. Vous capturez la différence (le spread) en jouant le rôle de teneur de marché.

### 🐻 D. Fade (Contrarian)
-   **Le Signal** : "FADE HYPE".
-   **Logique** : Le marché est en surchauffe (Euphorie excessive, prix > 60cts) mais les fondamentaux ou le sentiment social (Fear & Greed) suggèrent le contraire.
-   **Action** : Pariez **contre** la foule (Achetez NO quand tout le monde achète YES).

---

## 📊 4. Quant (Analyse Quantitative Monte Carlo)

L'approche mathématique pure pour les marchés financiers (Crypto, Stocks).

-   **Objectif** : Trouver un "Edge" mathématique.
-   **Comment ça marche ?** :
    1.  Le bot regarde un marché (ex: "Bitcoin > 100k en 2024").
    2.  Il récupère l'historique du prix du Bitcoin (Binance, Yahoo).
    3.  Il lance **10,000 simulations** (Monte Carlo) pour voir combien de fois le Bitcoin dépasse 100k.
    4.  Il compare sa probabilité (ex: 60%) au prix de Polymarket (ex: 40cts).
-   **Lecture** :
    -   <span style="color:green">**Edge Positif (+)**</span> : Polymarket sous-estime l'événement. **Opportunité d'ACHAT**.
    -   <span style="color:red">**Edge Négatif (-)**</span> : Polymarket surestime l'événement. **Opportunité de VENTE**.

---

## 🛠 Dépannage Rapide

-   **Je ne vois pas de marchés ?** Vérifiez que vos filtres (Volume, Score) sont à 0.
-   **Erreur API / Rien ne charge ?** Le backend doit tourner. Lancez `./LANCER.command` (Mac) ou relancez le backend manuellement.
-   **Erreur "Monte Carlo" ?** Assurez-vous d'avoir une connexion internet pour que le bot puisse récupérer les prix historiques sur Yahoo/Binance.

---
*Scanner Polymarket - V 2.1*
