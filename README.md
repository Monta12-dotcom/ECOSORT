# ♻️ ECOSORT — Système Intelligent de Tri des Déchets

## Description
Système de tri automatique des déchets recyclables 
basé sur la vision par ordinateur et l'intelligence artificielle.
Développé dans le cadre du PCD — ENSI 2025/2026.

## Matériel utilisé
- Raspberry Pi 4
- Caméra USB
- Écran LCD 16x2 (I2C)
- Module LED RGB (Keyes)

## Technologies
- Python 3
- PyTorch — ResNet18 Fine-tuné
- OpenCV
- Flask + SQLite
- RPi.GPIO / RPLCD

## Catégories détectées
| Catégorie | Couleur LED |
|---|---|
| Plastique | 🔵 Bleu |
| Verre | 🟢 Vert |
| Métal | ⚪ Blanc |
| Papier | 🟡 Jaune |
| Carton | 🔴 Rouge |
| Déchet non triable | 🟣 Violet |

## Précision du modèle
- V1 : 88.02%
- V2 : 87.00%
- **V3 : ~90%** ✅

## Équipe
- KHECHINE Azza
- TRABELSI Montaha
- LETAIEF Chiraz

## Encadrante
Dr. Hela BOUKEF — ENSI 2025/2026
