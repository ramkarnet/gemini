import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="RAMKAR QUANT v31", layout="wide", page_icon="📈")

# --- CUSTOM CSS (Neon & Dark Mode) ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; padding: 15px; border-radius: 10px; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #238636; color: white; }
    .birikim-card { border: 2px solid #ff4b4b; padding: 20px; border-radius: 15px; background-color: #1c1c1c; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR (MFS Kontrol) ---
with st.sidebar:
    st.title("🛡️ MFS LIGHT")
    usd_try = st.number_input("Haftalık USD/TRY %", value=1.2)
    cds = st.number_input("5Y CDS", value=280)
    vix = st.number_input("VIX Endeksi", value=18)
    xu100_ema = st.toggle("XU100 > EMA50", value=True)
    
    # MFS Karar Mekanizması
    mfs_status = "YEŞİL" if (usd_try < 3 and cds < 450 and vix < 30 and xu100_ema) else "KIRMIZI"
    
    if mfs_status == "YEŞİL":
        st.success("MFS: ON - İŞLEM YAPILABİLİR")
    else:
        st.error("MFS: OFF - NAKİTTE KAL!")

# --- ANA EKRAN ---
st.title("🚀 RAMKAR v31 RADAR")
st.subheader("Haftalık Algoritmik Tarama Sonuçları")

# Örnek Veri Seti (Burayı senin Excel çıktınla bağlayacağız)
data = {
    'Hisse': ['OFSYM', 'KCAER', 'MIATK', 'ASELS'],
    'Skor': ['6/6', '6/6', '5/6', '4/6'],
    'RKP': [0.68, 0.62, 0.45, 0.38],
    'Etiket': ['🔥 BİRİKİM', '🚀 TREND', '➖ NORMAL', '❄️ DAĞITIM'],
    'Mesafe %': [8.2, 12.5, 4.1, 18.2],
    'ADX': [32, 29, 24, 21]
}
df = pd.DataFrame(data)

# --- METRİKLER ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Taranan Hisse", "217")
col2.metric("Radar Kilit (6/6)", len(df[df['Skor'] == '6/6']))
col3.metric("Birikim Etiketli", len(df[df['Etiket'] == '🔥 BİRİKİM']))
col4.metric("MFS Durumu", mfs_status)

st.divider()

# --- RADAR KİLİT LİSTESİ ---
st.header("🎯 Radar Kilit (6/6) Adayları")
onayli_hisseler = df[df['Skor'] == '6/6']

cols = st.columns(len(onayli_hisseler))
for i, (index, row) in enumerate(onayli_hisseler.iterrows()):
    with cols[i]:
        st.markdown(f"""
        <div class="birikim-card">
            <h3>{row['Hisse']}</h3>
            <h2 style='color: #238636;'>RKP: {row['RKP']}</h2>
            <p><b>Durum:</b> {row['Etiket']}</p>
            <p><b>ADX:</b> {row['ADX']} | <b>Mesafe:</b> %{row['Mesafe %']}</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button(f"{row['Hisse']} Detayına Git", key=row['Hisse']):
            st.toast(f"{row['Hisse']} için Google Trends verileri çekiliyor...")

st.divider()

# --- GÖRSELLEŞTİRME ---
st.header("📊 RKP vs Mesafe Analizi")
fig = px.scatter(df, x="Mesafe %", y="RKP", size="ADX", color="Etiket",
                 hover_name="Hisse", title="Hisse Kalite Dağılımı (Büyüklük = ADX Gücü)")
st.plotly_chart(fig, use_container_width=True)

# --- GOOGLE TRENDS SİMÜLASYONU ---
st.header("📈 Sosyal Kanıt (Google Trends)")
tab1, tab2 = st.tabs(["Trends/Fiyat Korelasyonu", "Sektörel Dağılım"])

with tab1:
    # Sahte Trends Verisi
    chart_data = pd.DataFrame({
        'Hafta': pd.date_range(start='2025-11-01', periods=10, freq='W'),
        'Fiyat': [100, 105, 102, 110, 115, 120, 135, 140, 155, 160],
        'Trends Arama': [10, 12, 8, 15, 10, 5, 4, 3, 2, 1]  # SESSİZ KALKIŞ!
    })
    
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=chart_data['Hafta'], y=chart_data['Fiyat'], name='Fiyat'))
    fig2.add_trace(go.Bar(x=chart_data['Hafta'], y=chart_data['Trends Arama'], name='Google Trends', opacity=0.3))
    st.plotly_chart(fig2, use_container_width=True)
    st.info("💡 Fiyat yükselirken Google Trends'in düşmesi 'Sessiz Kalkış' sinyalidir.")

st.success("RAMKAR v31 - 'Disiplin > Duygu'")
