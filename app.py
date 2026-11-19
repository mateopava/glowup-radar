"""ZONA LIBRE: la interfaz de GlowUp Radar para Seoru.
La zona fija (core/) carga el modelo, valida los datos, predice, decide y explica; aquí solo armamos lo que ve la gerencia.

Para verla en el computador:   streamlit run app.py"""
import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from core import (cargar_config, cargar_metadata, cargar_modelo, cargar_resultados, etiqueta, evaluar,
                  hay_modelo, texto_razon, validar)

config = cargar_config()
st.set_page_config(page_title=config["titulo"], layout="wide")
CARPETA_MODELO = Path(__file__).resolve().parent / "model"


# ---------------------------------------------------------------------------------------------
# Encabezado
# ---------------------------------------------------------------------------------------------
col_logo, col_titulo = st.columns([1, 6])
with col_logo:
    if config["logo"] and Path(config["logo"]).exists():
        st.image(config["logo"], width=120)
with col_titulo:
    st.title(config["titulo"])
    st.caption(f"{config['cliente']} · {config['descripcion']}")

if not hay_modelo():
    st.info("Todavía no hay modelo en la carpeta model/. Sigan la guía del README.")
    st.divider()
    st.caption(config["pie"])
    st.stop()


@st.cache_resource
def recursos():
    return cargar_metadata(), cargar_modelo(), cargar_resultados()


@st.cache_data
def extras():
    # archivos que exporta nuestro cuaderno (sección 10) además de los de la plantilla
    extra = json.loads((CARPETA_MODELO / "extra.json").read_text(encoding="utf-8"))
    temas = pd.read_csv(CARPETA_MODELO / "temas.csv")
    comparacion = pd.read_csv(CARPETA_MODELO / "comparacion_modelos.csv")
    return extra, temas, comparacion


meta, modelo, resultados = recursos()
extra, temas, comparacion = extras()
m = meta["metricas"]
evento = meta["evento"]
RANGOS_VALOR = ["menos de US$100.000", "US$100.000 a US$500.000", "US$500.000 a US$2 millones",
                "US$2 a US$10 millones", "más de US$10 millones"]
RANGOS_MESES = ["1–3 meses", "4–6 meses", "7–9 meses", "10–12 meses"]


def millones(valor):
    """US$ en millones con coma decimal: 2871901 -> 'US$2,87 M'; los negativos llevan el signo adelante."""
    signo = "−" if valor < -0.5 else ""
    return signo + f"US${abs(valor) / 1e6:,.2f} M".replace(",", "X").replace(".", ",").replace("X", ".")


def porcentaje(valor, decimales=1):
    return f"{valor * 100:.{decimales}f} %".replace(".", ",")


def accion_tema(tema):
    fila = temas[temas["Tema"] == tema]
    return fila["Acción para Seoru"].iloc[0] if len(fila) else ""


# ---------------------------------------------------------------------------------------------
# La recomendación va arriba y dice claramente que la regla empata con el modelo
# ---------------------------------------------------------------------------------------------
a, b = m["intervalo_diferencia"]
st.info(
    f"**Recomendación:** para decidir si firmar, la **regla de la constancia** basta: "
    f"{extra['regla_final'].lower()}. En la prueba de 2024 la regla y el radar costaron lo mismo, "
    f"{millones(m['costo_regla'])} por cada 100 importadores evaluados (el ahorro del radar frente a la regla va de "
    f"{millones(a)} a {millones(b)}, así que no es distinto de cero). El radar sirve para **ordenar** a los aprobados, explicar cada recomendación "
    f"y mostrar quién vende lo mismo que Seoru."
)

pestanas = st.tabs(["Lista de 20", "Radar 2026", "Consultar un importador", "Evaluar uno nuevo",
                    "¿Cuánto vale el radar?", "Cómo decide"])

COLUMNAS_TABLA = {
    "puesto_lista": st.column_config.NumberColumn("Puesto", format="%d"),
    "importador": "Importador",
    "nit_publico": "NIT",
    "prob_pct": st.column_config.NumberColumn("Prob. de abandono", format="%.1f %%"),
    "decision": "Radar",
    "decision_regla_txt": "Regla",
    "tema": "Tipo de productos",
    "afinidad_pct": st.column_config.NumberColumn("Afinidad con Seoru", format="%.0f %%"),
    "rango_valor": "Valor importado",
    "rango_meses": "Meses con importaciones",
    "dueno_marca_txt": "Dueño de marca",
    "razones": "Razones del radar",
}
tabla = resultados.copy()
tabla["prob_pct"] = tabla["probabilidad"] * 100


# ---------------------------------------------------------------------------------------------
# 1. Lista de 20 para la diligencia debida
# ---------------------------------------------------------------------------------------------
with pestanas[0]:
    st.subheader("Los 20 importadores para empezar la diligencia debida")
    pesos = extra["pesos_lista"]
    st.markdown(
        f"Entran los importadores que el radar recomienda firmar (con o sin garantías), menos los dueños de marca: "
        f"filiales de multinacionales o venta por catálogo que importan sus propias marcas y no distribuirían una "
        f"competidora. Quedan **{extra['elegibles']} elegibles**. Se ordenan con un puntaje en percentiles: "
        f"**riesgo {pesos['riesgo']:.0%}** (menos probabilidad de abandono, más puntos), "
        f"**afinidad con Seoru {pesos['afinidad']:.0%}** (sérums, limpiadores y solares faciales) y "
        f"**tamaño {pesos['tamano']:.0%}** (capacidad de distribución)."
    )
    lista = tabla[tabla["en_lista_20"] == "Sí"].sort_values("puesto_lista")
    st.dataframe(lista[["puesto_lista", "importador", "prob_pct", "decision", "tema", "afinidad_pct", "rango_valor",
                        "rango_meses", "razones"]],
                 column_config=COLUMNAS_TABLA, hide_index=True, width="stretch")
    st.caption("Lo probamos con 2024: una lista de 20 armada con este criterio no tuvo abandonos, frente a 9 % del grupo "
               "elegible. Con 20 empresas un solo abandono mueve el porcentaje 5 puntos, así que es una señal, no una prueba.")


# ---------------------------------------------------------------------------------------------
# 2. Radar 2026: los importadores de 2025 con filtros
# ---------------------------------------------------------------------------------------------
with pestanas[1]:
    st.subheader("Radar 2026: recomendación para cada importador de 2025")
    conteo = tabla["decision"].value_counts()
    c1, c2, c3 = st.columns(3)
    for col, d in zip((c1, c2, c3), meta["decisiones"]):
        col.metric(d, int(conteo.get(d, 0)))

    f1, f2, f3 = st.columns(3)
    decisiones = f1.multiselect("Recomendación del radar", meta["decisiones"], default=meta["decisiones"])
    tipos = f2.multiselect("Tipo de productos", sorted(tabla["tema"].unique()), placeholder="Todos")
    valores = f3.multiselect("Valor importado", RANGOS_VALOR, placeholder="Todos")
    f4, f5, f6 = st.columns(3)
    meses = f4.multiselect("Meses con importaciones", RANGOS_MESES, placeholder="Todos")
    texto = f5.text_input("Buscar por nombre o NIT")
    sin_duenos = f6.checkbox("Ocultar dueños de marca", value=False)

    vista = tabla[tabla["decision"].isin(decisiones)]
    if tipos:
        vista = vista[vista["tema"].isin(tipos)]
    if valores:
        vista = vista[vista["rango_valor"].isin(valores)]
    if meses:
        vista = vista[vista["rango_meses"].isin(meses)]
    if texto.strip():
        t = texto.strip().lower()
        vista = vista[vista["importador"].str.lower().str.contains(t, regex=False)
                      | vista["nit_publico"].astype(str).str.contains(t, regex=False)]
    if sin_duenos:
        vista = vista[vista["dueno_marca_txt"] == "No"]
    vista = vista.sort_values("probabilidad")
    st.write(f"{len(vista)} importadores (de menor a mayor riesgo)")
    st.dataframe(vista[["importador", "nit_publico", "prob_pct", "decision", "decision_regla_txt", "tema", "afinidad_pct",
                        "rango_valor", "rango_meses", "dueno_marca_txt"]],
                 column_config=COLUMNAS_TABLA, hide_index=True, width="stretch")
    st.download_button("Descargar esta vista (CSV)", vista.drop(columns=["prob_pct"]).to_csv(index=False).encode("utf-8-sig"),
                       file_name="radar_2026_filtrado.csv", mime="text/csv")


# ---------------------------------------------------------------------------------------------
# 3. Consultar un importador por nombre o NIT
# ---------------------------------------------------------------------------------------------
with pestanas[2]:
    st.subheader("Consultar un importador")
    opciones = (tabla["importador"] + " · NIT " + tabla["nit_publico"].astype(str)).tolist()
    elegido = st.selectbox("Escriban el nombre o el NIT", opciones, index=None, placeholder="Por ejemplo: Mesprit")
    if elegido:
        fila = tabla.iloc[opciones.index(elegido)]
        c1, c2, c3 = st.columns(3)
        c1.metric(f"Probabilidad de {evento}", porcentaje(fila["probabilidad"]))
        c2.metric("Recomendación del radar", fila["decision"])
        c3.metric("Decisión de la regla", fila["decision_regla_txt"])
        puesto = int(fila["puesto_lista"])
        st.markdown(
            f"- **Tipo de productos:** {fila['tema']}. {accion_tema(fila['tema'])}\n"
            f"- **Afinidad con Seoru:** {fila['afinidad_pct']:.0f} % de sus productos notificados se parecen a los de Seoru\n"
            f"- **Valor importado:** {fila['rango_valor']} · **Meses con importaciones:** {fila['rango_meses']}\n"
            f"- **Lista de 20:** {'puesto ' + str(puesto) if puesto > 0 else 'no está'}"
            + (" · es **dueño de marca**, así que no ocupa cupo en la diligencia debida" if fila["dueno_marca_txt"] == "Sí" else "")
        )
        razones = [r for r in str(fila.get("razones", "")).split(" · ") if r and r != "nan"]
        if razones:
            st.markdown("**Razones principales del radar**")
            for r in razones:
                st.markdown(f"- {r}")
        if fila["decision"] != fila["decision_regla_txt"]:
            st.warning("El radar y la regla no coinciden en este importador: vale la pena revisarlo con más cuidado.")
        st.caption("Las razones dicen en qué se apoya el modelo, no qué pasaría si el importador cambiara algo. "
                   "Las variables de aduana se muestran en rangos por la licencia de los datos.")


# ---------------------------------------------------------------------------------------------
# 4. Evaluar un importador nuevo (formulario de la plantilla)
# ---------------------------------------------------------------------------------------------
with pestanas[3]:
    st.subheader("Evaluar un importador que no está en la lista")
    st.caption("Cada campo arranca con un valor típico. Cambien los que conozcan del importador y presionen Evaluar.")
    valores_nuevos = {}
    with st.form("nuevo"):
        columnas = st.columns(2)
        for i, col in enumerate(meta["columnas"]):
            nombre = col["nombre"]
            with columnas[i % 2]:
                if col["tipo"] == "numérica":
                    valores_nuevos[nombre] = st.number_input(etiqueta(meta, nombre), value=float(col["referencia"]), key=nombre)
                elif col["tipo"] == "categórica":
                    valores_nuevos[nombre] = st.selectbox(etiqueta(meta, nombre), col.get("categorias") or [""], key=nombre)
                else:
                    valores_nuevos[nombre] = st.text_area(etiqueta(meta, nombre), key=nombre)
        enviado = st.form_submit_button("Evaluar")
    if enviado:
        datos, errores, avisos = validar(pd.DataFrame([valores_nuevos]), meta)
        for e in errores:
            st.error(e)
        for aviso in avisos:
            st.warning(aviso)
        if not errores:
            r = evaluar(modelo, meta, datos)[0]
            c1, c2 = st.columns(2)
            c1.metric(f"Probabilidad de {evento}", porcentaje(r["probabilidad"]))
            c2.metric("Recomendación", r["decision"])
            if r["razones"]:
                st.markdown("**Razones principales**")
                for razon in r["razones"]:
                    st.markdown(f"- {texto_razon(razon, meta)}")
            st.caption("Las razones muestran de qué depende la predicción, no qué pasaría si algo cambiara.")


# ---------------------------------------------------------------------------------------------
# 5. Cuánto vale el radar frente a la regla
# ---------------------------------------------------------------------------------------------
with pestanas[4]:
    st.subheader("¿Cuánto vale el radar?")
    sin_criterio = min(m["costo_no_firmar_con_nadie"], m["costo_firmar_con_todos"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Costo con el radar", millones(m["costo_modelo"]))
    c2.metric("Costo con la regla", millones(m["costo_regla"]))
    c3.metric("Ahorro del radar frente a la regla", millones(m["costo_regla"] - m["costo_modelo"]))
    c4.metric("Ahorro frente a decidir sin criterio", millones(sin_criterio - m["costo_modelo"]))
    st.markdown(
        f"Para decidir si firmar, **el radar no le gana a la regla**: el ahorro es de {millones(m['costo_regla'] - m['costo_modelo'])} "
        f"por cada 100 importadores y su intervalo de 95 % va de {millones(a)} a {millones(b)}, así que incluye el cero. "
        f"Las dos herramientas ahorran unos {millones(sin_criterio - m['costo_modelo'])} por cada 100 frente a la mejor "
        f"decisión sin criterio. El valor del radar está en el orden de la lista, las razones y el encaje con Seoru."
    )
    graf = comparacion.copy()
    graf["Costo"] = graf["Costo por 100"] / 1e6
    graf["Desde"] = graf["IC inf"] / 1e6
    graf["Hasta"] = graf["IC sup"] / 1e6
    graf["Grupo"] = graf["Decisión"].map(lambda d: "Regla" if d == "Regla simple" else
                                         ("Sin criterio" if d in ("Firmar con todos", "Garantías a todos", "No firmar con nadie") else "Modelos"))
    orden = graf.sort_values("Costo")["Decisión"].tolist()
    barras = alt.Chart(graf).mark_bar().encode(
        x=alt.X("Costo:Q", title="Costo de los errores por cada 100 importadores, prueba 2024 (US$ millones)"),
        y=alt.Y("Decisión:N", sort=orden, title=None),
        color=alt.Color("Grupo:N", scale=alt.Scale(domain=["Regla", "Modelos", "Sin criterio"],
                                                   range=["#eb6834", "#2a78d6", "#9aa0a6"]), legend=alt.Legend(title=None)),
        tooltip=[alt.Tooltip("Costo:Q", format=".2f"), alt.Tooltip("Desde:Q", format=".2f"), alt.Tooltip("Hasta:Q", format=".2f")])
    errores_graf = alt.Chart(graf).mark_rule(color="black").encode(x="Desde:Q", x2="Hasta:Q", y=alt.Y("Decisión:N", sort=orden))
    st.altair_chart(barras + errores_graf, width="stretch")
    detalle = comparacion[["Decisión", "Costo por 100", "IC inf", "IC sup", "Dif. vs regla", "Sensibilidad", "Precisión", "AUC"]].copy()
    for c in ["Costo por 100", "IC inf", "IC sup", "Dif. vs regla"]:
        detalle[c] = detalle[c] / 1e6
    st.dataframe(detalle, hide_index=True, width="stretch",
                 column_config={c: st.column_config.NumberColumn(c + " (US$ M)", format="%.2f")
                                for c in ["Costo por 100", "IC inf", "IC sup", "Dif. vs regla"]})
    st.caption("Supuestos del caso: firmar con un importador que abandona cuesta US$250.000; no firmar con uno que habría "
               "funcionado, US$50.000; las garantías cuestan US$20.000 y, si el importador abandona igual, se pierden "
               "US$100.000 más. Medido en los 484 importadores de 2024 con el modelo entrenado en 2023; intervalos por "
               "bootstrap de 1.000 muestras.")


# ---------------------------------------------------------------------------------------------
# 6. Cómo decide
# ---------------------------------------------------------------------------------------------
with pestanas[5]:
    st.subheader("Cómo decide el radar")
    limites = [0.0] + meta["umbrales"] + [1.0]
    filas = [{"Probabilidad de abandono": f"{porcentaje(limites[i], 0)} a {porcentaje(limites[i + 1], 0)}", "Recomendación": d}
             for i, d in enumerate(meta["decisiones"])]
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Umbrales del radar** (elegidos con los costos del caso)")
        st.table(pd.DataFrame(filas))
    with c2:
        st.markdown("**Regla de la constancia** (reajustada con 2023 y 2024)")
        st.markdown(extra["regla_final"])
        st.markdown(f"**Modelo:** {m['modelo']}. Entrenado con {meta['n_entrenamiento']} importadores-año.")
    st.markdown("**Qué vende cada importador y qué haría Seoru** (temas sacados de los nombres de sus productos notificados)")
    t = temas.copy()
    t["Abandono"] = (t["Abandono"] * 100).round(0)
    st.dataframe(t[["Tema", "Importadores-año", "Abandono", "Importadores 2025", "Acción para Seoru"]], hide_index=True, width="stretch",
                 column_config={"Abandono": st.column_config.NumberColumn("Abandono 2023–2024", format="%.0f %%")})
    st.caption("El radar se apoya sobre todo en los meses con importaciones y en la parte del valor importada en el segundo "
               "semestre. Son señales de cómo le va al importador, no palancas: pedirle que compre más meses no lo vuelve "
               "mejor socio.")


# Pie de página (debe quedar)
st.divider()
st.caption(config["pie"])
