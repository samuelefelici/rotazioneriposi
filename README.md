# Rotazione Riposi - Streamlit

Applicazione Streamlit per calcolare e confrontare rotazioni turni con CP-SAT (OR-Tools), con monitoraggio live dell'algoritmo e report PDF.

## Avvio rapido

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Funzionalita

- Configurazione input completa (domanda, riposi, vincoli, range ricerca)
- Ricerca su griglia di configurazioni `(N, K)`
- Tracciamento live dei tentativi e del progresso
- Classifica delle migliori soluzioni
- Dettaglio della soluzione top (pattern, coperture, eccedenze)
- Export PDF con layout curato

## Note modello

- Vincolo riposi annuali con tolleranza
- Copertura minima giornaliera (domanda)
- Opzionale: bilanciamento feriali
- Vincolo ciclico sui giorni consecutivi lavorati
- Obiettivo lessicografico: minimizza picco eccedenza, poi totale eccedenza

