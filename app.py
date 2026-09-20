from __future__ import annotations

from datetime import date, timedelta
import hashlib
import hmac
import os
import secrets

import pandas as pd
import streamlit as st

from turni.exporters import (
    build_frames,
    export_excel,
    export_frame_excel,
    export_frame_pdf,
    export_pdf,
)
from turni.io import load_input_workbook
from turni.scheduler import solve_schedule


st.set_page_config(page_title="Turni centrale Dalmine", page_icon="📅", layout="wide")
st.markdown(
    """
    <style>
    .block-container {padding-top: 1.8rem; padding-bottom: 3rem;}
    [data-testid="stMetric"] {background: #f6f8fb; border: 1px solid #e2e7ef; padding: 0.8rem; border-radius: 0.6rem;}
    .status-box {padding: 0.9rem 1rem; border-radius: 0.55rem; background: #fff4e5; border-left: 5px solid #d97706; margin-bottom: 0.6rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


def require_web_password() -> None:
    if os.environ.get("TURNI_DESKTOP_MODE") == "1":
        return

    expected_password = str(st.secrets.get("APP_PASSWORD", "")).strip()
    if not expected_password:
        st.error("Accesso web non configurato. Contattare l'amministratore.")
        st.stop()

    if st.session_state.get("web_authenticated") is True:
        return

    st.title("Turni centrale di Dalmine")
    st.caption("Inserisci la password ricevuta per accedere alla demo.")
    supplied_password = st.text_input("Password", type="password")
    if st.button("Accedi", type="primary", use_container_width=True):
        if hmac.compare_digest(supplied_password, expected_password):
            st.session_state["web_authenticated"] = True
            st.rerun()
        else:
            st.error("Password non corretta.")
    st.stop()


require_web_password()


def calendar_for_display(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    doctor_columns = [column for column in frame.columns if column.startswith("Medico ")]
    result = frame.drop(columns=doctor_columns).copy()
    result["Medici assegnati"] = frame[doctor_columns].apply(
        lambda row: ", ".join(str(value) for value in row if pd.notna(value) and str(value).strip()),
        axis=1,
    )
    return result


def filtered_exports(frame: pd.DataFrame, title: str, file_stem: str, key_prefix: str) -> None:
    left, right = st.columns(2)
    left.download_button(
        "Esporta questa vista in Excel",
        data=export_frame_excel(frame),
        file_name=f"{file_stem}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        key=f"{key_prefix}_xlsx",
    )
    right.download_button(
        "Esporta questa vista in PDF",
        data=export_frame_pdf(frame, title),
        file_name=f"{file_stem}.pdf",
        mime="application/pdf",
        use_container_width=True,
        key=f"{key_prefix}_pdf",
    )


def generate(payload: bytes, year: int, month: int, seconds: int, requested_seed: str) -> None:
    actual_seed = requested_seed.strip() or secrets.token_hex(8)
    data = load_input_workbook(payload, year, month)
    result = solve_schedule(
        data,
        year,
        month,
        max_seconds_per_phase=float(seconds),
        seed=actual_seed,
    )
    st.session_state["result"] = result
    st.session_state["frames"] = build_frames(result)
    st.session_state["source_signature"] = (hashlib.sha256(payload).hexdigest(), year, month)


st.title("Turni centrale di Dalmine")
st.caption("Carica le disponibilità, genera la proposta mensile e controlla subito coperture e scoperture.")

with st.sidebar:
    st.header("Configurazione")
    today = date.today()
    year = int(st.number_input("Anno del calendario", min_value=2025, max_value=2100, value=today.year, step=1))
    month = int(st.number_input("Mese del calendario", min_value=1, max_value=12, value=today.month, step=1))
    seconds = int(st.slider("Tempo massimo di calcolo per fase", 5, 120, 20))
    with st.expander("Opzioni avanzate"):
        requested_seed = st.text_input(
            "Codice estrazione",
            value="",
            help="Lascia vuoto per una nuova estrazione casuale. Inserisci un codice già usato per riprodurre lo stesso spareggio.",
        )
    st.markdown("**Regole V1**")
    st.caption("Solo disponibilità dichiarate. Riposo minimo 11 ore. Priorità OVEST, poi BGEST, poi gli altri. I minimi contrattuali non sono usati.")
    if os.environ.get("TURNI_DESKTOP_MODE") == "1":
        st.divider()
        if st.button("Chiudi applicazione", use_container_width=True):
            os._exit(0)

uploaded = st.file_uploader(
    "File Excel delle risposte Google Forms",
    type=["xlsx"],
    help="Da Google Fogli: File > Scarica > Microsoft Excel (.xlsx).",
)

if uploaded is None:
    st.info("Carica il file Excel delle risposte per iniziare.")
    st.stop()

payload = uploaded.getvalue()
generate_col, reroll_col = st.columns([2, 1])
generate_clicked = generate_col.button("Genera calendario", type="primary", use_container_width=True)
reroll_clicked = reroll_col.button(
    "Nuova estrazione",
    use_container_width=True,
    disabled="result" not in st.session_state,
    help="Ricalcola con un nuovo spareggio casuale mantenendo le stesse regole.",
)

if generate_clicked or reroll_clicked:
    try:
        seed = "" if reroll_clicked else requested_seed
        with st.spinner("Controllo del file e generazione del calendario in corso…"):
            generate(payload, year, month, seconds, seed)
    except Exception as exc:
        st.error(f"Impossibile generare il calendario: {exc}")

if "result" not in st.session_state:
    st.stop()

current_signature = (hashlib.sha256(payload).hexdigest(), year, month)
if st.session_state.get("source_signature") != current_signature:
    st.warning("Il file, il mese o l'anno sono cambiati. Premi Genera calendario per aggiornare i risultati.")
    st.stop()

result = st.session_state["result"]
frames = st.session_state["frames"]
calendar = frames["Calendario"].copy()
assignments = frames["Assegnazioni"].copy()
doctor_summary = frames["Riepilogo medici"].copy()
shortages = frames["Scoperture"].copy()

filled = int(calendar["Assegnati"].sum()) if not calendar.empty else 0
required = int(calendar["Richiesti"].sum()) if not calendar.empty else 0
uncovered = required - filled
coverage = filled / required if required else 0

st.divider()
metric_columns = st.columns(4)
metric_columns[0].metric("Copertura", f"{coverage:.0%}")
metric_columns[1].metric("Posizioni richieste", required)
metric_columns[2].metric("Assegnate", filled)
metric_columns[3].metric("Scoperte", uncovered)

download_excel, download_pdf = st.columns(2)
download_excel.download_button(
    "Scarica report completo Excel",
    data=export_excel(result),
    file_name=f"calendario_turni_{result.month}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
)
download_pdf.download_button(
    "Scarica report completo PDF",
    data=export_pdf(result),
    file_name=f"calendario_turni_{result.month}.pdf",
    mime="application/pdf",
    use_container_width=True,
)

tab_summary, tab_calendar, tab_doctors, tab_shifts, tab_checks = st.tabs(
    ["Sintesi", "Calendario", "Medici", "Cerca turno", "Controlli"]
)

with tab_summary:
    st.subheader("Situazione del mese")
    if uncovered == 0:
        st.success("Tutte le posizioni sono coperte.")
    else:
        st.markdown(
            f'<div class="status-box"><strong>{uncovered} posizioni scoperte</strong><br>Controlla per prime le righe con il maggior numero di posti mancanti.</div>',
            unsafe_allow_html=True,
        )
        critical = shortages.sort_values(["Scoperti", "Data"], ascending=[False, True]).head(12)
        st.dataframe(critical, use_container_width=True, hide_index=True)

    if not calendar.empty:
        daily = calendar.groupby("Data", as_index=False)[["Assegnati", "Scoperti"]].sum()
        st.subheader("Copertura giornaliera")
        st.bar_chart(daily, x="Data", y=["Assegnati", "Scoperti"], stack=True, color=["#2F75B5", "#D97706"])

with tab_calendar:
    st.subheader("Vista calendario")
    minimum_date = calendar["Data"].min()
    maximum_date = calendar["Data"].max()
    controls = st.columns([1.2, 1.2, 2, 2])
    time_view = controls[0].radio("Periodo", ["Mese", "Settimana", "Giorno"], horizontal=True)
    reference_date = controls[1].date_input(
        "Data di riferimento",
        value=minimum_date,
        min_value=minimum_date,
        max_value=maximum_date,
        disabled=time_view == "Mese",
    )
    selected_codes = controls[2].multiselect(
        "Turni",
        options=sorted(calendar["Codice"].unique()),
        default=sorted(calendar["Codice"].unique()),
    )
    selected_status = controls[3].multiselect(
        "Stato",
        options=["Scoperto", "Parziale", "Completo"],
        default=["Scoperto", "Parziale", "Completo"],
    )
    doctor_query = st.text_input("Cerca un medico nel calendario", placeholder="Nome o cognome")

    visible = calendar[calendar["Codice"].isin(selected_codes) & calendar["Stato"].isin(selected_status)].copy()
    if time_view == "Giorno":
        visible = visible[visible["Data"] == reference_date]
    elif time_view == "Settimana":
        week_start = reference_date - timedelta(days=reference_date.weekday())
        visible = visible[(visible["Data"] >= week_start) & (visible["Data"] <= week_start + timedelta(days=6))]
    visible = calendar_for_display(visible)
    if doctor_query.strip():
        visible = visible[visible["Medici assegnati"].str.contains(doctor_query.strip(), case=False, na=False)]
    st.dataframe(visible, use_container_width=True, hide_index=True)
    filtered_exports(
        visible,
        f"Calendario {time_view.lower()} - {result.month}",
        f"vista_calendario_{time_view.lower()}_{result.month}",
        "calendar_view",
    )

with tab_doctors:
    st.subheader("Turni per medico")
    doctor_query = st.text_input("Cerca medico", placeholder="Nome, cognome o email", key="doctor_search")
    summary_visible = doctor_summary.copy()
    if doctor_query.strip():
        search_text = summary_visible[["Nome", "Cognome", "Email"]].fillna("").agg(" ".join, axis=1)
        summary_visible = summary_visible[search_text.str.contains(doctor_query.strip(), case=False, na=False)]
    st.dataframe(summary_visible, use_container_width=True, hide_index=True)

    doctor_names = sorted(assignments["Medico"].unique()) if not assignments.empty else []
    selected_doctor = st.selectbox("Apri il dettaglio", ["Tutti i medici"] + doctor_names)
    doctor_assignments = assignments if selected_doctor == "Tutti i medici" else assignments[assignments["Medico"] == selected_doctor]
    st.dataframe(doctor_assignments, use_container_width=True, hide_index=True)
    filtered_exports(
        doctor_assignments,
        f"Turni assegnati - {selected_doctor}",
        f"turni_medici_{result.month}",
        "doctor_view",
    )

with tab_shifts:
    st.subheader("Ricerca turno")
    filters = st.columns(3)
    date_range = filters[0].date_input(
        "Intervallo date",
        value=(calendar["Data"].min(), calendar["Data"].max()),
        min_value=calendar["Data"].min(),
        max_value=calendar["Data"].max(),
    )
    shift_codes = filters[1].multiselect(
        "Tipo di turno",
        options=sorted(calendar["Codice"].unique()),
        default=sorted(calendar["Codice"].unique()),
        key="shift_search_codes",
    )
    shift_status = filters[2].multiselect(
        "Copertura",
        options=["Scoperto", "Parziale", "Completo"],
        default=["Scoperto", "Parziale", "Completo"],
        key="shift_search_status",
    )
    shift_visible = calendar[calendar["Codice"].isin(shift_codes) & calendar["Stato"].isin(shift_status)].copy()
    if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
        shift_visible = shift_visible[(shift_visible["Data"] >= date_range[0]) & (shift_visible["Data"] <= date_range[1])]
    shift_visible = calendar_for_display(shift_visible)
    st.dataframe(shift_visible, use_container_width=True, hide_index=True)
    filtered_exports(
        shift_visible,
        f"Ricerca turni - {result.month}",
        f"ricerca_turni_{result.month}",
        "shift_view",
    )

with tab_checks:
    st.subheader("Controlli e tracciabilità")
    st.caption("Le informazioni contrattuali sono mostrate nei dati ma non vengono usate per assegnare i turni nella V1.")
    st.dataframe(frames["Controlli"], use_container_width=True, hide_index=True)
    st.dataframe(frames["Parametri"], use_container_width=True, hide_index=True)
