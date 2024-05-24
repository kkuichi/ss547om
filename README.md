# Bakalárska práca

Bakalárska práca sa zaoberá klasifikačnými modelmi na predikciu binárneho atribútu. Praktická časť bola vypracovaná v súlade s metodológiou CRISP-DM za použitia Pythonu a jemu prislúchajúcich knižníc.

- **Názov**: Analýza dopravných nehôd metódami strojového učenia
- **Autor**: Sofia Schürgerová
- **Vedúci**: Ing. Anna Biceková, PhD.
- **Cieľ**: Vytvorenie klasifikačného modelu na predikciu nebezpečných diaľnic na základe vonkajších faktorov.

## Obsah
1. **Pochopenie dát**
    - Vizualizácie kategorických a numerických atribútov pomocou histogramov a boxplotov
2. **Príprava dát**
    -  Premenovanie atribútov a ich hodnôt
    - Odstránenie chýbajúcich hodnôt a atribútov s veľkým množstvom chýbajúcich dát
    - Pretypovani atribútov
    - Rozdelenie atribútov do viacerých atribútov
    - Vytvorenie cieľového atribútu
    - Rozdeleni dát na trénovaciu a testovaciu množinu
    - Použitie krokovej regresie na identifikáciu významných atribútov
3. **Modelovanie**
    - Naivný Bayesov klasifikátor
    - K - najbližších susedov
    - Náhodný les
    - AdaBoost
    - Logistická regresia
4. **Vyhodnotenie**
    - Vyhodnotenie modelov metrikami AUC, MCC a úspešnosť
    - Vykreslenie matíc zámen

## Návod na spustenie kódu
Praktická časť pozostáva zo 4 zdrojových kódov, ktoré je potrebné spustiť v nasledujúcom poradí:
1. Premenovanie.ipynb
2. Grafy.ipynb
3. Priprava.ipynb
4. Modelovanie.ipynb

Link na dataset: *https://www.kaggle.com/datasets/rafaelborgesgraunke/traffic-accidents-brazil-pt-br*