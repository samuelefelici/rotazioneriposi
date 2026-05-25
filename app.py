from datetime import datetime

import pandas as pd
import streamlit as st

from pdf_report import build_pdf_report
from scheduler import GIORNI, SearchParams, search_solutions


st.set_page_config(page_title="Rotazione Riposi", page_icon="📊", layout="wide")

st.markdown(
    """
    <style>
    .hero {
        background: linear-gradient(135deg, #0F4C5C 0%, #1E847F 60%, #D9A441 100%);
        border-radius: 18px;
        padding: 24px;
        color: #ffffff;
        box-shadow: 0 12px 28px rgba(15, 76, 92, 0.25);
        margin-bottom: 16px;
    }
    .hero h1 { margin: 0; font-size: 2.1rem; letter-spacing: 0.5px; }
    .hero p { margin-top: 8px; font-size: 1.05rem; max-width: 920px; }
    .ticker {
        background: #0E1117;
        color: #C8FACC;
        font-family: 'JetBrains Mono', 'Consolas', monospace;
        font-size: 0.85rem;
        padding: 12px 14px;
        border-radius: 10px;
        height: 230px;
        overflow-y: auto;
        border: 1px solid #1E847F;
        box-shadow: inset 0 0 14px rgba(30, 132, 127, 0.25);
    }
    .ticker .ln { display:block; white-space: nowrap; }
    .ticker .ok { color:#7CFFB2; }
    .ticker .inf { color:#FF8C8C; }
    .ticker .skip { color:#FFD580; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <h1>Rotazione Riposi Planner</h1>
      <p>
        Inserisci domanda e vincoli, avvia la ricerca su (N, K), guarda l'algoritmo CP-SAT
        scorrere in tempo reale e scegli la rotazione migliore dalla classifica per vedere il dettaglio completo.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Input modello")

    domanda_feriali = st.number_input("Turni feriali richiesti", min_value=1, value=51, step=1)
    domanda_domenica = st.number_input("Turni domenicali base", min_value=1, value=15, step=1)

    mode = st.radio(
        "Buffer domenicale",
        ["Usa forza feriale reale", "Usa percentuale"],
        horizontal=False,
    )

    forza_feriale_reale = None
    riserva_domenica_pct = None
    if mode == "Usa forza feriale reale":
        forza_feriale_reale = st.number_input(
            "Forza feriale reale (es. 66)", min_value=1, value=66, step=1
        )
    else:
        riserva_domenica_pct = st.number_input(
            "Riserva domenicale %", min_value=0.0, value=25.0, step=1.0
        )

    st.divider()

    riposi_anno_target = st.number_input("Riposi annui target", min_value=1.0, value=54.0, step=0.5)
    tol_riposi = st.number_input("Tolleranza riposi annui", min_value=0.0, value=1.0, step=0.1)
    max_consec = st.number_input("Max giorni consecutivi lavoro", min_value=1, value=6, step=1)
    balance_weekday = st.checkbox("Bilanciamento Lun-Sab", value=True)

    st.divider()

    st.subheader("Range ricerca")
    col_a, col_b = st.columns(2)
    with col_a:
        n_min = st.number_input("N min", min_value=1, value=11, step=1)
        k_min = st.number_input("K min", min_value=1, value=1, step=1)
    with col_b:
        n_max = st.number_input("N max", min_value=1, value=56, step=1)
        k_max = st.number_input("K max", min_value=1, value=4, step=1)

    timeout_per_attempt = st.slider("Timeout per tentativo (s)", 1, 20, 4)
    top_n = st.slider("Top risultati da mostrare", 5, 30, 12)

run = st.button("Avvia calcolatore", type="primary", use_container_width=True)

if "last_results" not in st.session_state:
    st.session_state.last_results = []
    st.session_state.selected_pos = 1

if run:
    if n_min > n_max or k_min > k_max:
        st.error("Range non valido: controlla N/K min-max.")
        st.stop()

    total = (n_max - n_min + 1) * (k_max - k_min + 1)
    done = 0

    st.subheader("Algoritmo in esecuzione")
    progress = st.progress(0)
    metric_row = st.columns(4)
    m_try = metric_row[0].empty()
    m_ok = metric_row[1].empty()
    m_peak = metric_row[2].empty()
    m_tot = metric_row[3].empty()
    m_try.metric("Tentativi", "0")
    m_ok.metric("Fattibili", 0)
    m_peak.metric("Miglior picco", "-")
    m_tot.metric("Miglior totale", "-")

    ticker_box = st.empty()
    ticker_lines = []

    results = []

    for k in range(k_min, k_max + 1):
        for n in range(n_min, n_max + 1):
            done += 1

            if k * n < domanda_feriali:
                ticker_lines.append(
                    f"<span class='ln skip'>· N={n:>2} K={k} SKIP (capacita feriali insufficiente)</span>"
                )
            else:
                single_params = SearchParams(
                    riposi_anno_target=riposi_anno_target,
                    tol_riposi=tol_riposi,
                    domanda_feriali=domanda_feriali,
                    domanda_domenica=domanda_domenica,
                    max_consec=max_consec,
                    forza_feriale_reale=forza_feriale_reale,
                    riserva_domenica_pct=riserva_domenica_pct,
                    balance_weekday=balance_weekday,
                    n_min=n,
                    n_max=n,
                    k_min=k,
                    k_max=k,
                    timeout_per_attempt=timeout_per_attempt,
                )
                partial_results, _ = search_solutions(single_params)

                if partial_results:
                    r = partial_results[0]
                    results.append(r)
                    ticker_lines.append(
                        f"<span class='ln ok'>✓ N={n:>2} K={k} | picco={r['max_extra']:>2} "
                        f"tot={r['total_extra']:>3} R/anno={r['riposi_anno']:.2f} "
                        f"drv={r['tot_autisti']:>3}</span>"
                    )
                else:
                    ticker_lines.append(
                        f"<span class='ln inf'>× N={n:>2} K={k} infattibile/timeout</span>"
                    )

            progress.progress(done / total)
            fattibili = len(results)
            best_peak = min((r["max_extra"] for r in results), default="-")
            best_total = min((r["total_extra"] for r in results), default="-")
            m_try.metric("Tentativi", f"{done}/{total}")
            m_ok.metric("Fattibili", fattibili)
            m_peak.metric("Miglior picco", best_peak)
            m_tot.metric("Miglior totale", best_total)

            visible = ticker_lines[-14:]
            ticker_box.markdown(
                f"<div class='ticker'>{''.join(visible)}</div>",
                unsafe_allow_html=True,
            )

    results = sorted(
        results,
        key=lambda r: (
            r["max_extra"],
            r["total_extra"],
            abs(r["delta_riposi"]),
            r["tot_autisti"],
            r["N"],
        ),
    )

    st.session_state.last_results = results
    st.session_state.selected_pos = 1
    st.success(f"Ricerca completata: {len(results)} configurazioni fattibili su {total} tentativi.")

results = st.session_state.last_results

if results:
    st.subheader("Migliori rotazioni")

    rows = []
    for idx, r in enumerate(results[:top_n], start=1):
        rows.append(
            {
                "Pos": idx,
                "N": r["N"],
                "K": r["K"],
                "Driver": r["tot_autisti"],
                "T": r["T"],
                "Riposi/anno": round(r["riposi_anno"], 2),
                "Picco eccedenza": r["max_extra"],
                "Totale eccedenza": r["total_extra"],
                "Dom eff": r["dom_domenica_eff"],
            }
        )

    ranking_df = pd.DataFrame(rows)

    st.caption("Clicca una riga per vedere il dettaglio della rotazione")
    event = st.dataframe(
        ranking_df,
        use_container_width=True,
        height=380,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    selected_pos = st.session_state.selected_pos
    if event is not None and getattr(event, "selection", None):
        rows_sel = event.selection.get("rows") if isinstance(event.selection, dict) else getattr(event.selection, "rows", None)
        if rows_sel:
            selected_pos = rows_sel[0] + 1
            st.session_state.selected_pos = selected_pos

    if selected_pos > len(results):
        selected_pos = 1
        st.session_state.selected_pos = 1

    top = results[selected_pos - 1]

    st.markdown(f"### Dettaglio rotazione #{selected_pos} — N={top['N']} · K={top['K']}")

    info_cols = st.columns(6)
    info_cols[0].metric("Driver", top["tot_autisti"])
    info_cols[1].metric("Riposi/ciclo", top["T"])
    info_cols[2].metric("Riposi/anno", f"{top['riposi_anno']:.2f}")
    info_cols[3].metric("Picco eccedenza", top["max_extra"])
    info_cols[4].metric("Totale eccedenza", top["total_extra"])
    info_cols[5].metric("Dom base → eff", f"{top['dom_domenica_base']} → {top['dom_domenica_eff']}")

    pattern_data = []
    for i, row in enumerate(top["pattern"], start=1):
        pattern_data.append(
            {"Sett": f"S{i:02}", **{GIORNI[d]: ("R" if cell else "") for d, cell in enumerate(row)}}
        )
    pattern_df = pd.DataFrame(pattern_data)

    stats_rows = []
    for g in GIORNI:
        d = top["demand"][g]
        l = top["al_lavoro"][g]
        e = top["extra"][g]
        stats_rows.append(
            {
                "Giorno": g,
                "Domanda": d,
                "In servizio": l,
                "Eccedenza": e,
                "Copertura %": round((l / d) * 100, 1) if d else 0.0,
            }
        )
    stats_df = pd.DataFrame(stats_rows)

    col_left, col_right = st.columns([1.35, 1])
    with col_left:
        st.markdown("**Pattern settimanale**")
        st.dataframe(pattern_df, use_container_width=True, height=420, hide_index=True)
    with col_right:
        st.markdown("**Coperture per giorno**")
        st.dataframe(stats_df, use_container_width=True, hide_index=True)
        st.bar_chart(stats_df.set_index("Giorno")[["Domanda", "In servizio"]])

    summary = {
        "Data report": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "Configurazioni fattibili": len(results),
        "Rotazione selezionata": f"#{selected_pos} — N={top['N']} K={top['K']}",
        "Driver totali": top["tot_autisti"],
        "Picco eccedenza": top["max_extra"],
        "Totale eccedenza": top["total_extra"],
        "Dom base -> eff": f"{top['dom_domenica_base']} -> {top['dom_domenica_eff']}",
        "Fattore riserva": f"{top['riserva_factor']:.3f}",
    }

    pdf_bytes = build_pdf_report(summary, ranking_df, pattern_df)
    st.download_button(
        "Esporta dettaglio in PDF",
        data=pdf_bytes,
        file_name=f"rotazione_{top['N']}x{top['K']}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
else:
    st.info("Imposta i parametri nella sidebar e premi 'Avvia calcolatore'.")
