import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import time
from datetime import datetime, timedelta

# 1. Configuración de la página y Estilo Corporativo
st.set_page_config(page_title="Quiniela Platco 2026", page_icon="🏆", layout="wide", initial_sidebar_state="collapsed")

estilo_corporativo = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Montserrat', sans-serif;
    }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    
    /* Paleta Corporativa: Azul oscuro, gris y acentos amarillos sobre fondo claro */
    h1, h2, h3 { color: #1A2530 !important; } /* Azul oscuro corporativo para títulos */
    
    div[data-testid="metric-container"] {
        background-color: #F8F9FA; /* Gris muy claro para las tarjetas */
        border-left: 6px solid #F1C40F; /* Borde amarillo corporativo */
        border-radius: 8px;
        padding: 5% 5% 5% 10%;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
    }
</style>
"""
st.markdown(estilo_corporativo, unsafe_allow_html=True)

banderas = {
    "México": "🇲🇽", "Sudáfrica": "🇿🇦", "Corea del Sur": "🇰🇷", "República Checa": "🇨🇿",
    "Canadá": "🇨🇦", "Bosnia y Herzegovina": "🇧🇦", "Qatar": "🇶🇦", "Suiza": "🇨🇭",
    "Brasil": "🇧🇷", "Marruecos": "🇲🇦", "Haití": "🇭🇹", "Escocia": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
    "Estados Unidos": "🇺🇸", "Paraguay": "🇵🇾", "Australia": "🇦🇺", "Turquía": "🇹🇷",
    "Alemania": "🇩🇪", "Curazao": "🇨🇼", "Costa de Marfil": "🇨🇮", "Ecuador": "🇪🇨",
    "Países Bajos": "🇳🇱", "Japón": "🇯🇵", "Suecia": "🇸🇪", "Túnez": "🇹🇳",
    "Bélgica": "🇧🇪", "Egipto": "🇪🇬", "Irán": "🇮🇷", "Nueva Zelanda": "🇳🇿",
    "España": "🇪🇸", "Cabo Verde": "🇨🇻", "Arabia Saudita": "🇸🇦", "Uruguay": "🇺🇾",
    "Francia": "🇫🇷", "Senegal": "🇸🇳", "Irak": "🇮🇶", "Noruega": "🇳🇴",
    "Argentina": "🇦🇷", "Argelia": "🇩🇿", "Austria": "🇦🇹", "Jordania": "🇯🇴",
    "Portugal": "🇵🇹", "RD Congo": "🇨🇩", "Uzbekistán": "🇺🇿", "Colombia": "🇨🇴",
    "Inglaterra": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Croacia": "🇭🇷", "Ghana": "🇬🇭", "Panamá": "🇵🇦"
}
def obtener_bandera(pais): return banderas.get(pais, "🏳️")

# 3. Inicializar la Memoria
if 'usuario_autenticado' not in st.session_state:
    st.session_state.usuario_autenticado = False
    st.session_state.correo, st.session_state.nombre, st.session_state.departamento = "", "", ""

def calcular_puntos(pred_l, pred_v, real_l, real_v, estatus):
    if estatus != "Finalizado" or pd.isna(real_l) or pd.isna(real_v) or real_l == "" or real_v == "": return 0
    try: pred_l, pred_v, real_l, real_v = int(pred_l), int(pred_v), int(real_l), int(real_v)
    except ValueError: return 0
    if pred_l == real_l and pred_v == real_v: return 3
    dif_pred, dif_real = pred_l - pred_v, real_l - real_v
    if (dif_pred > 0 and dif_real > 0) or (dif_pred < 0 and dif_real < 0) or (dif_pred == 0 and dif_real == 0): return 1
    return 0

# 4. Conexión a la Base de Datos
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

try:
    import json
    # Ahora lee de la bóveda secreta, no del archivo físico
    cred_dict = json.loads(st.secrets["google_json"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(cred_dict, scope)
    client = gspread.authorize(creds)
    
    sheet = client.open("Quiniela_Platco_BD")
    
    ws_usuarios = sheet.worksheet("Usuarios")
    df_usuarios = pd.DataFrame(ws_usuarios.get_all_records())
    df_partidos = pd.DataFrame(sheet.worksheet("Partidos").get_all_records())
    df_pronosticos = pd.DataFrame(sheet.worksheet("Pronosticos").get_all_records())
    
    # Procesar cruce de datos globalmente para usarlo en múltiples pestañas
    df_cruce = pd.DataFrame()
    if not df_pronosticos.empty and not df_partidos.empty:
        df_cruce = pd.merge(df_pronosticos, df_partidos, on='ID_Partido', how='left')
        df_cruce['Puntos_Ganados'] = df_cruce.apply(lambda r: calcular_puntos(r['Pred_L'], r['Pred_V'], r['Goles_L'], r['Goles_V'], r['Estatus']), axis=1)

    if not st.session_state.usuario_autenticado:
        st.title("🔐 Acceso a la Quiniela Platco")
        st.markdown("---")
        col_login, col_registro = st.columns(2)
        with col_login:
            st.subheader("Entrar a mi cuenta")
            with st.form("form_login"):
                correo_login = st.text_input("Correo electrónico (@platco.com)")
                pin_login = st.text_input("Tu PIN de 4 dígitos", type="password")
                if st.form_submit_button("Iniciar Sesión"):
                    if not df_usuarios.empty:
                        usuario_match = df_usuarios[(df_usuarios['Correo'] == correo_login) & (df_usuarios['PIN'] == int(pin_login) if pin_login.isdigit() else False)]
                        if not usuario_match.empty:
                            st.session_state.update(usuario_autenticado=True, correo=usuario_match['Correo'].values[0], nombre=usuario_match['Nombre'].values[0], departamento=usuario_match['Departamento'].values[0])
                            st.rerun()
                        else: st.error("Correo o PIN incorrectos.")
                    else: st.error("No hay usuarios registrados aún.")

        with col_registro:
            st.subheader("Soy nuevo, quiero jugar")
            with st.form("form_registro"):
                nuevo_correo, nuevo_nombre = st.text_input("Tu Correo Platco"), st.text_input("Tu Nombre y Apellido")
                nuevo_depto = st.selectbox("Tu Departamento", ["Operaciones", "Recursos Humanos", "Finanzas", "IT", "Ventas", "Otro"])
                nuevo_pin = st.text_input("Crea un PIN numérico (Ej: 1234)", type="password")
                if st.form_submit_button("Crear mi cuenta"):
                    if "" in [nuevo_correo, nuevo_nombre, nuevo_pin]: st.warning("Llena todos los campos.")
                    elif not nuevo_pin.isdigit(): st.error("El PIN debe ser numérico.")
                    elif not df_usuarios.empty and nuevo_correo in df_usuarios['Correo'].values: st.error("Ese correo ya existe.")
                    else:
                        ws_usuarios.append_row([nuevo_correo, nuevo_nombre, nuevo_depto, int(nuevo_pin)])
                        st.success("¡Cuenta creada! Inicia sesión a la izquierda.")
    else:
        col_t, col_b = st.columns([4, 1])
        with col_t:
            st.title("🏆 Quiniela Corporativa - Platco Mundial 2026")
            st.write(f"👤 Bienvenido/a, **{st.session_state.nombre}**")
        with col_b:
            st.write("")
            if st.button("🚪 Cerrar Sesión"):
                st.session_state.usuario_autenticado = False
                st.rerun()
        st.markdown("---")

        # NUEVA ESTRUCTURA DE PESTAÑAS (4 TABS)
        tab1, tab2, tab3, tab4 = st.tabs(["📝 Hacer Pronóstico", "📅 Calendario", "📊 Dashboard", "👤 Mis Pronósticos"])
        
        with tab1:
            partidos_pendientes = df_partidos[df_partidos['Estatus'] == 'Pendiente']
            opciones_partidos = [f"{obtener_bandera(row['Local'])} {row['Local']} vs {obtener_bandera(row['Visitante'])} {row['Visitante']} ({row['ID_Partido']})" for i, row in partidos_pendientes.iterrows()]
            
            with st.form("form_pronostico", clear_on_submit=True):
                partido_seleccionado = st.selectbox("Selecciona el Partido", opciones_partidos if opciones_partidos else ["No hay partidos pendientes"])
                col3, col4 = st.columns(2)
                with col3: goles_local = st.number_input("Goles Local", min_value=0, max_value=15, step=1)
                with col4: goles_visitante = st.number_input("Goles Visitante", min_value=0, max_value=15, step=1)
                    
                if st.form_submit_button("Guardar Mi Quiniela ⚽"):
                    if partido_seleccionado == "No hay partidos pendientes": st.error("No hay partidos.")
                    else:
                        id_partido = partido_seleccionado.split("(")[-1].replace(")", "")
                        fecha_partido = datetime.strptime(df_partidos[df_partidos['ID_Partido'] == id_partido]['Fecha_Hora'].values[0], "%Y-%m-%d %H:%M")
                        
                        if datetime.now() > fecha_partido - timedelta(minutes=30): 
                            st.error("⏳ ¡Tiempo agotado! El árbitro ya pitó.")
                        else:
                            df_usuario = df_pronosticos[(df_pronosticos['Usuario'] == st.session_state.correo) & (df_pronosticos['ID_Partido'] == id_partido)]
                            ws_pronosticos = sheet.worksheet("Pronosticos")
                            
                            if len(df_usuario) == 0:
                                ws_pronosticos.append_row([f"PR-{int(time.time())}", st.session_state.correo, st.session_state.nombre, st.session_state.departamento, id_partido, goles_local, goles_visitante, "", 1])
                                st.success("✅ ¡Gooooolazo! Tu pronóstico está en la red. 🥅")
                                st.balloons()   # 🎈 LLUVIA DE GLOBOS AL VOTAR
                                time.sleep(1.5) 
                                st.rerun()      
                            else:
                                intentos = df_usuario['Intentos'].values[0] if 'Intentos' in df_usuario.columns and not pd.isna(df_usuario['Intentos'].values[0]) else 1
                                if int(intentos) >= 2: 
                                    st.error("🚫 Roja directa. Ya utilizaste tu única oportunidad de cambio.")
                                else:
                                    fila = int(df_usuario.index[0]) + 2 
                                    ws_pronosticos.update_cell(fila, 6, goles_local)
                                    ws_pronosticos.update_cell(fila, 7, goles_visitante)
                                    ws_pronosticos.update_cell(fila, 9, 2)
                                    st.info("🔄 Cambio táctico realizado. Pronóstico actualizado.")
                                    st.balloons()   # 🎈 LLUVIA DE GLOBOS AL ACTUALIZAR
                                    time.sleep(1.5) 
                                    st.rerun()

        with tab2:
            df_mostrar = df_partidos.copy()
            df_mostrar['Local'] = df_mostrar['Local'].apply(lambda x: f"{obtener_bandera(x)} {x}")
            df_mostrar['Visitante'] = df_mostrar['Visitante'].apply(lambda x: f"{obtener_bandera(x)} {x}")
            st.subheader("Calendario de Partidos Oficiales")
            st.dataframe(df_mostrar, use_container_width=True)
            
        with tab3:
            st.subheader("📊 Dashboard de Resultados")
            if not df_cruce.empty:
                ranking = df_cruce.groupby(['Nombre', 'Departamento'])['Puntos_Ganados'].sum().reset_index()
                ranking = ranking.sort_values(by='Puntos_Ganados', ascending=False).reset_index(drop=True)
                ranking.index = ranking.index + 1 
                
                kpi1, kpi2, kpi3 = st.columns(3)
                total_jugadores = len(ranking)
                if total_jugadores > 0:
                    kpi1.metric("👥 Total de Jugadores", total_jugadores)
                    kpi2.metric("🥇 Líder Actual", ranking['Nombre'].iloc[0], f"{ranking['Puntos_Ganados'].iloc[0]} pts")
                    kpi3.metric("🏆 Depto. en Cabeza", df_cruce.groupby('Departamento')['Puntos_Ganados'].sum().idxmax())
                
                st.markdown("---")
                st.dataframe(ranking, use_container_width=True)
            else:
                st.info("Aún no hay predicciones para mostrar el ranking.")
                
        # NUEVA PESTAÑA: MIS PRONÓSTICOS
        with tab4:
            st.subheader("👤 Mis Pronósticos y Resultados")
            if not df_cruce.empty:
                # Filtramos solo los votos del usuario activo
                mis_votos = df_cruce[df_cruce['Usuario'] == st.session_state.correo].copy()
                
                if not mis_votos.empty:
                    # Limpiamos los datos para mostrarlos presentables
                    mis_votos['Partido'] = mis_votos['Local'].apply(obtener_bandera) + " " + mis_votos['Local'] + " vs " + mis_votos['Visitante'].apply(obtener_bandera) + " " + mis_votos['Visitante']
                    mis_votos['Mi Predicción'] = mis_votos['Pred_L'].astype(str) + " - " + mis_votos['Pred_V'].astype(str)
                    mis_votos['Resultado Real'] = mis_votos.apply(lambda x: f"{x['Goles_L']} - {x['Goles_V']}" if x['Estatus'] == 'Finalizado' else "Pendiente", axis=1)
                    
                    tabla_mostrar = mis_votos[['Partido', 'Mi Predicción', 'Resultado Real', 'Puntos_Ganados', 'Estatus']]
                    
                    # KPIs Personales
                    pts_totales = mis_votos['Puntos_Ganados'].sum()
                    aciertos_exactos = len(mis_votos[mis_votos['Puntos_Ganados'] == 3])
                    aciertos_tendencia = len(mis_votos[mis_votos['Puntos_Ganados'] == 1])
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("⭐ Mis Puntos Totales", pts_totales)
                    c2.metric("🎯 Aciertos Exactos (3 pts)", aciertos_exactos)
                    c3.metric("📈 Aciertos Tendencia (1 pt)", aciertos_tendencia)
                    
                    st.markdown("---")
                    st.dataframe(tabla_mostrar, use_container_width=True)
                else:
                    st.info("Aún no has guardado ningún pronóstico.")
            else:
                st.info("No hay datos en el sistema aún.")

except Exception as e:
    st.error("Error de conexión.")
    st.write(e)
