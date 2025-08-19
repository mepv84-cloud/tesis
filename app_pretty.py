import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# =====================
# CONFIG + THEME TWEAKS
# =====================
st.set_page_config(page_title="Dashboard de Laboratorio", layout="wide", page_icon="📊")

# Minimal CSS for "cards" + compact tables
st.markdown("""
<style>
/* Card */
.card {background: white; border-radius: 16px; padding: 18px; box-shadow: 0 4px 16px rgba(0,0,0,.06);}
.card h3 {margin: 0 0 6px 0; font-size: 1rem; color: #374151;}
.card .big {font-weight: 700; font-size: 1.8rem; line-height: 1.1;}
/* Subtle caption */
.caption {color:#6b7280; font-size: .8rem}
/* Compact dataframes */
[data-testid="stDataFrameResizable"] div[data-baseweb="base-input"] {font-size:.85rem}
/* Tighter container spacing */
.block-container {padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1200px;}
</style>
""", unsafe_allow_html=True)

# =====================
# MOCK / STATE
# =====================
STAGE_DEADLINES = {
    "Ingreso": 5,
    "Pesaje": 70,
    "Ataque": 300,
    "Lectura": 60,
    "Reporte": 60,
    "Validación de resultados": 5,
}
SHEET_DEADLINE_LABEL = "8h 20m"

def ensure_state():
    if "sheets" not in st.session_state:
        created_at = datetime.now()
        samples = []
        for i in range(1, 21):
            samples.append({
                "id": i, "name": f"Muestra {i}", "addedAt": created_at,
                "stages": [{"name": n, "start": None, "end": None, "completed": False} for n in STAGE_DEADLINES.keys()],
                "type": "Metálico" if i % 2 == 0 else "No Metálico",
                "analyst": "—",
            })
        st.session_state.sheets = [{
            "id": "s1",
            "name": created_at.strftime("%d-%m-%Y") + "/1",
            "createdAt": created_at,
            "dateKey": created_at.strftime("%Y-%m-%d"),
            "samples": samples,
        }]
    if "expanded" not in st.session_state:
        st.session_state.expanded = set()
ensure_state()

sheets = st.session_state.sheets
all_samples = [s for sh in sheets for s in sh["samples"]]

def sample_progress(stages):
    total = len(stages)
    done = sum(1 for x in stages if x["completed"])
    return (done/total)*100 if total else 0

def sheet_progress(sh):
    vals = [sample_progress(s["stages"]) for s in sh["samples"]]
    return sum(vals)/len(vals) if vals else 0

# =====================
# SIDEBAR NAV
# =====================
tab = st.sidebar.radio("Secciones", ["Panel", "KPI", "Ingreso de Muestras"], index=0)
st.sidebar.markdown(f"<span class='caption'>SLA global: <b>{SHEET_DEADLINE_LABEL}</b></span>", unsafe_allow_html=True)

# =====================
# DASH CARDS
# =====================
def metric_card(title, value):
    st.markdown(f"""
    <div class="card">
        <h3>{title}</h3>
        <div class="big">{value}</div>
    </div>
    """, unsafe_allow_html=True)

# =====================
# KPI BASE
# =====================
compliance_general = 87
compliance_by_stage = [
    {"name": "Ingreso", "value": 95},
    {"name": "Pesaje", "value": 85},
    {"name": "Ataque", "value": 80},
    {"name": "Lectura", "value": 75},
    {"name": "Reporte", "value": 70},
    {"name": "Validación", "value": 90},
]
total_muestras = len(all_samples)
muestras_completas = sum(1 for s in all_samples if all(x["completed"] for x in s["stages"]))
muestras_en_curso = total_muestras - muestras_completas

# =====================
# PANEL
# =====================
if tab == "Panel":
    c1, c2, c3, c4 = st.columns(4)
    with c1: metric_card("Tiempo Promedio", "4.2h")
    with c2: metric_card("T. por Etapa", "Ver en KPI")
    with c3: metric_card("% Cumplimiento", f"{compliance_general}%")
    with c4: metric_card("% por Etapa", "Ver en KPI")

    st.markdown("### Hojas de trabajo")
    for sh in sheets:
        prog = round(sheet_progress(sh), 0)
        top = st.columns([3,2,1,3,1])
        with top[0]: st.subheader(sh["name"])
        with top[1]: st.caption(sh["createdAt"].strftime("%d-%m-%Y %H:%M"))
        with top[2]: st.metric("# Muestras", len(sh["samples"]))
        with top[3]: st.progress(int(prog))
        with top[4]:
            key = f"exp_{sh['id']}"
            show = key in st.session_state.expanded
            if st.button("Ocultar" if show else "Ver", key=f"btn_{key}"):
                if show: st.session_state.expanded.remove(key)
                else: st.session_state.expanded.add(key)

        if key in st.session_state.expanded:
            df = pd.DataFrame([
                {
                    "ID": s["id"],
                    "Nombre": s["name"],
                    "Tipo": s["type"],
                    "Analista": s["analyst"],
                    "Progreso (%)": round(sample_progress(s["stages"]), 0),
                    "Deadline": SHEET_DEADLINE_LABEL,
                } for s in sh["samples"]
            ])
            st.dataframe(df, use_container_width=True, height=320)

# =====================
# KPI (Plotly para estilo cercano a Recharts)
# =====================
elif tab == "KPI":
    left, right = st.columns([1,2])

    with left:
        st.markdown("#### Cumplimiento General")
        fig = go.Figure(data=[go.Pie(
            labels=["Cumplido", "Incumplido"],
            values=[compliance_general, 100 - compliance_general],
            hole=.6
        )])
        fig.update_layout(margin=dict(l=0,r=0,t=0,b=0), showlegend=True)
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"SLA global: {SHEET_DEADLINE_LABEL}")

    with right:
        st.markdown("#### Resumen Operacional")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Muestras totales", f"{total_muestras}")
        c2.metric("En curso", f"{muestras_en_curso}")
        c3.metric("Completadas", f"{muestras_completas}")
        c4.metric("T. resp. promedio", "4.2h")

    st.markdown("#### % Cumplimiento por Etapa")
    df_stage = pd.DataFrame(compliance_by_stage)
    fig2 = px.bar(df_stage, x="name", y="value", labels={"name":"Etapa", "value":"%"})
    fig2.update_yaxes(range=[0,100])
    st.plotly_chart(fig2, use_container_width=True)

    st.markdown("#### Tiempo promedio por etapa (min)")
    avg_by_stage = []
    for stg in STAGE_DEADLINES.keys():
        base = STAGE_DEADLINES[stg]
        factor = 0.9 + ((ord(stg[0]) % 5) * 0.03)
        avg_by_stage.append({"etapa": stg, "minutos": int(round(base * factor))})
    df_avg = pd.DataFrame(avg_by_stage)
    fig3 = px.bar(df_avg, x="etapa", y="minutos", labels={"etapa":"Etapa", "minutos":"Minutos"})
    st.plotly_chart(fig3, use_container_width=True)
    st.caption("* Valores simulados a partir de deadlines.")

    st.markdown("#### Distribución de TAT por muestra (min)")
    # Simular histogramas de TAT
    total_base = sum(STAGE_DEADLINES.values())
    simulated = []
    for i, s in enumerate(all_samples):
        base_id = s["id"] if isinstance(s["id"], int) else i
        factor = 0.85 + ((base_id % 7) * 0.04)
        simulated.append(int(round(total_base * factor)))
    buckets = [
        {"rango": "0-120", "min": 0, "max": 120},
        {"rango": "121-240", "min": 121, "max": 240},
        {"rango": "241-360", "min": 241, "max": 360},
        {"rango": "361-480", "min": 361, "max": 480},
        {"rango": "481-600", "min": 481, "max": 600},
        {"rango": ">600", "min": 601, "max": float("inf")},
    ]
    counts = []
    for b in buckets:
        counts.append({
            "rango": b["rango"],
            "muestras": sum(1 for v in simulated if b["min"] <= v <= b["max"])
        })
    df_hist = pd.DataFrame(counts)
    fig4 = px.bar(df_hist, x="rango", y="muestras", labels={"rango":"TAT (min)", "muestras":"# Muestras"})
    st.plotly_chart(fig4, use_container_width=True)
    st.caption(f"* Muestras consideradas: {len(all_samples)}. Mock para demo.")

# =====================
# INGRESO
# =====================
else:
    st.markdown("### Crear nueva hoja de trabajo")
    if "bulk_rows" not in st.session_state:
        st.session_state.bulk_rows = [{"id": "", "name": "", "type": "Metálico", "analyst": ""}]

    df_input = pd.DataFrame(st.session_state.bulk_rows)
    edited = st.data_editor(
        df_input, num_rows="dynamic", use_container_width=True, hide_index=True,
        column_config={
            "id": st.column_config.TextColumn("ID"),
            "name": st.column_config.TextColumn("Nombre/Descripción"),
            "type": st.column_config.SelectboxColumn("Tipo", options=["Metálico","No Metálico"]),
            "analyst": st.column_config.TextColumn("Analista"),
        }
    )

    cA, cB = st.columns([1,2])
    with cA:
        if st.button("Cancelar"):
            st.session_state.bulk_rows = [{"id": "", "name": "", "type": "Metálico", "analyst": ""}]
            st.rerun()
    with cB:
        if st.button("Guardar hoja", type="primary"):
            rows = edited.to_dict(orient="records")
            valid = []
            for r in rows:
                rid = str(r.get("id","")).strip()
                nm = str(r.get("name","")).strip()
                tp = r.get("type","Metálico")
                an = str(r.get("analyst","")).strip()
                if rid and tp in ("Metálico","No Metálico"):
                    valid.append({"id": rid, "name": nm, "type": tp, "analyst": an})
            if not valid:
                st.warning("No hay filas válidas para guardar.")
            else:
                created_at = datetime.now()
                samples = []
                for r in valid:
                    try:
                        rid_cast = int(r["id"])
                    except Exception:
                        rid_cast = r["id"]
                    samples.append({
                        "id": rid_cast,
                        "name": r["name"] or f"Muestra {r['id']}",
                        "addedAt": created_at,
                        "stages": [{"name": n, "start": None, "end": None, "completed": False} for n in STAGE_DEADLINES.keys()],
                        "type": r["type"],
                        "analyst": r["analyst"] or "—",
                    })
                new_sheet = {
                    "id": f"s{np.random.randint(10**8)}",
                    "name": created_at.strftime("%d-%m-%Y") + "/2",
                    "createdAt": created_at,
                    "dateKey": created_at.strftime("%Y-%m-%d"),
                    "samples": samples,
                }
                st.session_state.sheets = [new_sheet] + st.session_state.sheets
                st.session_state.bulk_rows = [{"id": "", "name": "", "type": "Metálico", "analyst": ""}]
                st.success(f"Hoja creada: {new_sheet['name']}")
                st.rerun()
