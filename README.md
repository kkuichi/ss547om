# Systémy na podporu rozhodovania v medicíne
 
Webová aplikácia implementovaná v **Streamlit** určená pre lekárov. Systém umožňuje analýzu hospitalizovaných pacientov s COVID-19 prostredníctvom výpočtu medicínskych indexov, štatistického porovnávania pandémových vĺn a vizualizácie mortality. Rozhodovacia logika je postavená výhradne na pravidlách (rule-based) a referenčných hodnotách – nie na strojovom učení.
 
---
 
## Obsah
 
- [Štruktúra projektu](#štruktúra-projektu)
- [Popis modulov](#popis-modulov)
- [Záložky aplikácie](#záložky-aplikácie)
- [Inštalácia a spustenie](#inštalácia-a-spustenie)
- [Dáta](#dáta)
- [Autor](#autor)
---
 
## Štruktúra projektu
 
```
MASTER-THESIS/
│
├── app.py                      # Hlavná Streamlit aplikácia
│
├── modules/
│   ├── data_loader.py          # Načítanie a predspracovanie dát
│   ├── filters.py              # Filtre v bočnom paneli a výber indexov
│   ├── indices.py              # Výpočtové funkcie a register indexov
│   ├── state_manager.py        # Správa session state a histórie zmien
│   ├── statistical_tests.py    # Štatistické testy a výpočty
│   └── visualization.py        # Vizualizačné funkcie
│
├── data/
│   ├── vlna_1.csv              # Dáta – 1. vlna pandémie
│   ├── vlna_2.csv              # Dáta – 2. vlna pandémie
│   ├── vlna_3.csv              # Dáta – 3. vlna pandémie
│   └── vlna_4.csv              # Dáta – 4. vlna pandémie
│
├── requirements.txt
└── README.md
```
 
---
 
## Popis modulov
 
### `app.py`
 
Hlavný súbor aplikácie. Riadi celkovú štruktúru UI, navigáciu medzi záložkami a prepájanie všetkých modulov.
 
**Kľúčové časti:**
 
- **Konfigurácia a inicializácia** – nastavenie stránky (`st.set_page_config`), inicializácia session state pri prvom spustení, načítanie dát aktívnej vlny.
- **Navigácia** – horizontálna navigačná lišta implementovaná cez `st.columns` a tlačidlá, so zvýrazneným aktívnym tabom pomocou inline CSS. Záložky: *Databáza pacientov*, *Analýza indexov*, *Krivka mortality*, *Štatistická analýza*.
- **Sidebar** – pre záložky Databáza, Analýza a Mortalita sa vykresľujú demografické a klinické filtre; pre záložku Štatistická analýza sa zobrazujú nastavenia filtrovania odľahlých hodnôt.
**Funkcie:**
 
| Funkcia | Popis |
|---|---|
| `_render_patient_card(p_id)` | Zobrazí editovateľnú tabuľku všetkých odberov zvoleného pacienta s možnosťou uloženia zmien. |
| `_render_benchmark_card(...)` | Vykreslí kartu s hodnotou indexu pacienta a porovnaním s referenčnou skupinou (rovnaké pohlavie, vek ±5 rokov, rovnaká závažnosť). |
| `_stat_row(label, value, unit)` | Pomocná funkcia – generuje riadok HTML tabuľky pre štatistické karty mortality. |
| `_render_mortality_card(col, skupina, s, color)` | Vykreslí štatistickú kartu pre skupinu Exitus alebo Prepustenie (hospitalizácia, vek, pohlavie). |
| `_render_desc_stats(...)` | Zobrazí deskriptívne štatistiky (n, priemer, medián, Q1/Q3, min/max) pre jednu skupinu v štatistickej analýze. |
| `_render_desc_stats_from_dict(label, s)` | Obal nad `_render_desc_stats` – prijíma slovník z `statistical_tests`. |
| `_render_statistical_metrics(p_value, cliffs_d)` | Zobrazí p-hodnotu (vrátane vedeckého zápisu pre p < 0,0001) a Cliff's delta s interpretáciou veľkosti účinku. |
| `_make_boxplot(...)` | Vykreslí Plotly boxplot dvoch skupín. Ak je aktívny outlier filter, automaticky zobrazí filtrované dáta. |
| `_render_result_container(...)` | Obaľovací kontajner pre výsledok jedného indexu – farebný banner podľa štatistickej významnosti, metriky a boxplot vedľa seba. |
 
---
 
### `modules/data_loader.py`
 
Zodpovedá za načítanie CSV súborov pandémových vĺn a ich predspracovanie do konzistentnej podoby.
 
**Konštanty:**
 
- `PRIORITY_COLS` – zoznam stĺpcov, ktoré sa zobrazujú ako prvé (ID, demografické a klinické metadáta).
- `DATE_COLS` – stĺpce, ktoré sa automaticky konvertujú na formát dátumu.
**Funkcie:**
 
| Funkcia | Popis |
|---|---|
| `load_wave_data(wave)` | Načíta CSV súbor pre danú vlnu (1–4), odstráni prázdne a nepomenované stĺpce, skonvertuje dátumové stĺpce a zoradí stĺpce podľa `PRIORITY_COLS`. V prípade chyby vráti prázdny DataFrame so štandardnou štruktúrou. |
 
---
 
### `modules/filters.py`
 
Obsahuje všetky filtre zobrazované v bočnom paneli (sidebar) a komponent pre výber skupín indexov.
 
**Konštanty:**
 
- `CLINICAL_FILTER_TESTS` – slovník klinických testov dostupných vo filtri (názov stĺpca, referenčné minimum a maximum, jednotka, popis, formát zobrazenia). Obsahuje: S-CRP, S-IL6, S-FER, D-dimér HS, Neu abs, Ly abs, PLT, WBC, S-Kreat, S-Alb, PT (INR), S-AST, S-ALT.
**Pomocné funkcie:**
 
| Funkcia | Popis |
|---|---|
| `_col_range(df, col)` | Vráti (min, max) pre číselný stĺpec DataFrame. |
| `_fmt_val(val, fmt)` | Naformátuje hodnotu podľa zadaného formátu (celé číslo alebo desatinné miesta). |
| `_apply_date_mask(mask, date_range, col, df)` | Aplikuje dátumový filter na boolovskú masku riadkov. |
| `_reset_filter_state()` | Vymaže všetky kľúče filtrov zo `st.session_state` podľa prefixov a inkrementuje `editor_key`. |
 
**Hlavné funkcie:**
 
| Funkcia | Popis |
|---|---|
| `_render_index_filter(idx_name, df, w_key)` | Vykreslí interaktívny filter pre jeden klinický index s preset tlačidlami (Pod normou / V norme / Nad normou / Vlastný rozsah) podľa referenčných hodnôt z `INDEX_THRESHOLDS`. Vráti zvolený rozsah (min, max) alebo `None`. |
| `render_sidebar_filters(df)` | Vykreslí kompletný sidebar pre záložky Databáza, Analýza indexov a Krivka mortality. Obsahuje sekcie: výber vlny, demografia, dátumy, klinické testy, klinické indexy. Vráti vyfiltrovaný DataFrame a zvolenú vlnu. |
| `render_sidebar_stat_filters()` | Vykreslí sidebar pre záložku Štatistická analýza – nastavenia filtrovania odľahlých hodnôt (metódy: IQR, Z-skóre, percentilové orezanie, manuálny rozsah). Vráti `outlier_cfg` slovník. |
| `render_index_group_selector(key_prefix)` | Dvojkrokový UI komponent pre výber indexov: najprv skupina (multiselect), potom konkrétne indexy z každej zvolenej skupiny. Vráti zoznam názvov vybraných indexov. |
 
---
 
### `modules/indices.py`
 
Definuje všetky výpočtové funkcie medicínskych indexov a register pre ich programatické použitie.
 
Každá výpočtová funkcia prijíma DataFrame a vracia `pd.Series` vypočítaných hodnôt. Delenie nulou je ošetrené nahradením nuly hodnotou `np.nan`.
 
**Implementované indexy podľa skupín:**
 
| Skupina | Indexy |
|---|---|
| **Hematologické** | NLR (Neutrophil-to-Lymphocyte Ratio), PLR (Platelet-to-Lymphocyte Ratio), dNLR (Derived NLR), SII (Systemic Immune-Inflammation Index) |
| **Biochemické** | CAR (CRP-to-Albumin Ratio), CLR (CRP-to-Lymphocyte Ratio), Ferritin/Ly, FAR (Fibrinogen-to-Albumin Ratio), BUN/Cr, De Ritis (AST/ALT), AST/PLT, LDH/Albumin |
| **Koagulačné** | DLR (D-dimer-to-Lymphocyte Ratio), D-dimér/Albumin, Fibrinogen/Ly, PLT/Fibrinogen |
| **Kardiošpecifické** | BLR (BNP/Lymphocyte Ratio) |
 
**Kľúčové objekty:**
 
| Objekt | Popis |
|---|---|
| `INDEX_GROUPS` | Dvojúrovňový slovník `{skupina: {názov_indexu: funkcia}}` – používa sa pre UI (výber skupín) aj výpočty. |
| `INDEX_REGISTRY` | Plochý slovník `{názov_indexu: funkcia}` – hlavný register pre priame volanie výpočtov kdekoľvek v aplikácii. |
| `INDEX_THRESHOLDS` | Slovník referenčných medzí pre každý index (`low`, `high`, `unit`) – používa sa v filtroch a vizualizáciách. |
 
---
 
### `modules/state_manager.py`
 
Spravuje stav aplikácie počas behu (session state) a implementuje mechanizmus undo/redo pre editáciu dát.
 
**Funkcie:**
 
| Funkcia | Popis |
|---|---|
| `initialize_session_state()` | Inicializuje všetky potrebné kľúče `st.session_state` s predvolenými hodnotami pri prvom spustení. Kľúče: `master_data`, `original_data`, `history_stack`, `redo_stack`, `current_wave`, `editor_key`, `selected_p_ids`. |
| `load_new_wave(wave_id)` | Načíta dáta zvolenej vlny cez `data_loader`, uloží pôvodný stav do `original_data` a resetuje históriu zmien. |
| `_persist(df)` | Interná funkcia – uloží aktuálny stav DataFrame na disk (CSV) pre aktívnu vlnu. |
| `save_changes(updated_df)` | Uloží upravený DataFrame: pridá aktuálny stav do zásobníka histórie, nastaví nový `master_data` a zavolá `_persist`. |
| `undo_last_action()` | Vráti stav o jeden krok späť (vytiahne z `history_stack`, presunie do `redo_stack`). |
| `redo_action()` | Posunie stav o jeden krok vpred (vytiahne z `redo_stack`, presunie do `history_stack`). |
| `reset_to_original()` | Obnoví dáta do stavu pri načítaní vlny (z `original_data`), aktuálny stav uloží do histórie. |
 
---
 
### `modules/statistical_tests.py`
 
Implementuje štatistické testy a orchestračnú logiku pre záložku Štatistická analýza.
 
**Pomocné funkcie:**
 
| Funkcia | Popis |
|---|---|
| `compute_cliffs_delta(data1, data2)` | Vypočíta Cliff's delta ako mieru veľkosti účinku v rozsahu [−1, 1]. Interpretácia: < 0,147 zanedbateľný, 0,147–0,330 malý, 0,330–0,474 stredný, ≥ 0,474 veľký. |
| `apply_outlier_filter(series, method, ...)` | Filtruje odľahlé hodnoty zo série podľa zvolenej metódy: `none`, `iqr`, `zscore`, `percentile`, `manual`. |
| `_load_wave(wave_id)` | Načíta CSV súbor pre danú vlnu. |
| `_calc_index(df, index_name)` | Vypočíta index pre DataFrame a vráti sériu bez `NaN` a nekonečných hodnôt. |
| `_desc_stats(series, n_pacientov)` | Vypočíta deskriptívne štatistiky: n, priemer, medián, Q1, Q3, min, max. |
| `_last_per_patient(df)` | Vráti posledný záznam (odber) na pacienta – používa sa pri analýze mortality. |
| `_mann_whitney(data1, data2)` | Vykoná Mann-Whitney U test (dvojstranný). Vráti (p-hodnota, Cliff's delta) alebo `None` pri nedostatku dát (< 5 záznamov). |
 
**Hlavné testovacie funkcie:**
 
| Funkcia | Popis |
|---|---|
| `perform_mann_whitney_test(df1, df2, index_name, outlier_cfg)` | Porovná distribúciu indexu medzi dvoma vlnami (všetky záznamy). Vráti slovník s deskriptívnymi štatistikami, p-hodnotou, Cliff's delta a surovými dátami pre boxploty. |
| `perform_mortality_between_waves(df1, df2, index_name, outlier_cfg, skupina1, skupina2)` | Porovná index medzi zvolenými skupinami (Exitus/Prepustenie) z dvoch rôznych vĺn. Pracuje s posledným odberom na pacienta. |
| `run_statistical_analysis(wave1_id, wave2_id, selected_indices, outlier_cfg)` | Spustí `perform_mann_whitney_test` pre všetky zvolené indexy medzi dvoma vlnami. Vráti trojicu: DataFrame výsledkov, zoznam neúspešných indexov, slovník dát pre boxploty. |
| `run_mortality_between_waves(wave1_id, wave2_id, selected_indices, outlier_cfg, skupina1, skupina2)` | Spustí `perform_mortality_between_waves` pre všetky zvolené indexy. Vráti dvojicu: zoznam výsledkov, zoznam neúspešných indexov. |
 
---
 
### `modules/visualization.py`
 
Obsahuje funkcie na tvorbu interaktívnych Plotly grafov a výpočet štatistík pre záložky Analýza indexov a Krivka mortality.
 
**Konštanty:**
 
- `_INDEX_COMPONENTS` – mapovanie názvov indexov na dvojicu vstupných premenných zobrazovaných v hover tooltipe grafu.
**Funkcie:**
 
| Funkcia | Popis |
|---|---|
| `plot_patient_index_trend(p_data, index_name)` | Vykreslí časový priebeh hodnôt indexu pre jedného pacienta. Farebne odlišuje hodnoty v norme (zelená) a mimo normy (červená) podľa `INDEX_THRESHOLDS`. Hover zobrazuje dátum, hodnotu indexu a hodnoty vstupných premenných. |
| `plot_mortality_trend(df)` | Vykreslí kumulatívnu krivku exitov a prepustených pacientov podľa dĺžky hospitalizácie. Hover obsahuje deň, počet nových udalostí, kumulatív, percentuálny podiel a priemerný vek. |
| `compute_mortality_stats(df)` | Vypočíta deskriptívne štatistiky pre skupiny Exitus a Prepustenie (hospitalizácia, vek, pohlavie). Vráti slovník s kľúčmi `exitus` a `prepustenie`. |
| `compute_index_benchmark(wave_df, index_name, pohlavie, vek, zavaznost, index_fn, vek_pasmo)` | Vypočíta referenčné štatistiky indexu z historických dát pre skupinu pacientov so zhodným pohlavím, podobným vekom (±`vek_pasmo`, predvolene ±5 rokov) a rovnakou závažnosťou. Vráti `None` ak je menej ako 3 záznamy. |
 
---
 
## Záložky aplikácie
 
### Databáza pacientov
Prehľad hospitalizovaných pacientov aktívnej vlny s možnosťou filtrovania podľa demografických údajov, dátumov, klinických testov a vypočítaných indexov. Výberom pacienta v tabuľke sa zobrazí jeho editovateľná karta s históriou odberov. Zmeny je možné uložiť, vrátiť späť (undo), zopakovať (redo) alebo obnoviť do pôvodného stavu.
 
### Analýza indexov
Výpočet a vizualizácia časového vývoja zvolených medicínskych indexov pre vybraných pacientov (max. 5). Pre každý index sa zobrazuje farebne kódovaný graf s referenčnými pásmami a benchmarkové porovnanie s podobnými pacientmi z rovnakej vlny.
 
### Krivka mortality
Kumulatívna krivka exitov a prepustených pacientov zo zvolenej skupiny v závislosti od dĺžky hospitalizácie. Doplnená súhrnnými štatistikami (počty, mortalita, štatistiky hospitalizácie, veku a pohlavia) pre obe skupiny.
 
### Štatistická analýza
Mann-Whitney U test s výpočtom Cliff's delta pre porovnanie distribúcií indexov medzi dvoma zvolenými vlnami. Obsahuje dve pod-záložky: všeobecné porovnanie vĺn a porovnanie s ohľadom na mortalitu (Exitus vs. Prepustenie). Výsledky sú doplnené boxplotmi a deskriptívnymi štatistikami.
 
---
 
## Inštalácia a spustenie
 
### Požiadavky
 
- Python 3.10 alebo novší
### Postup
 
```bash
# 1. Klonovanie repozitára
git clone <url-repozitara>
cd MASTER-THESIS
 
# 2. Vytvorenie virtuálneho prostredia
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
.venv\Scripts\activate           # Windows
 
# 3. Inštalácia závislostí
pip install -r requirements.txt
 
# 4. Spustenie aplikácie
streamlit run app.py
```
 
Aplikácia sa otvorí v prehliadači na adrese `http://localhost:8501`.
 
---
 
## Dáta
 
Dátové súbory (`data/vlna_1.csv` – `data/vlna_4.csv`) nie sú súčasťou tohto repozitára z dôvodu ochrany zdravotných údajov. Súbory pochádzajú z klinického výskumného projektu a ich zverejnenie nie je povolené.
 
Každý súbor obsahuje záznamy hospitalizovaných pacientov s COVID-19 s laboratórnymi hodnotami z jednotlivých odberov. Štruktúra: demografické údaje, dátumy, dĺžka hospitalizácie, závažnosť priebehu ochorenia a 47 laboratórnych parametrov (hematologické, biochemické, koagulačné a imunologické hodnoty).
 
---
 
## Autor
 
**Autor diplomovej práce:** Bc. Sofia Schürgerová  
**Vedúci práce:** doc. Ing. František Babič, PhD.  
**Ústav umelej inteligencie, Fakulta elektrotechniky a informatiky Technickej univerzity v Košiciach**  
**Rok:** 2026
