import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# --- 1. SAYFA KONFİGÜRASYONU & CSS ---
st.set_page_config(page_title="RAMKAR PRO v31", layout="wide", page_icon="🦅")

# Wall Street Dark Tema & Neon Efektler
st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    h1, h2, h3 { color: #e0e0e0; font-family: 'Helvetica Neue', sans-serif; }
    .gold-text { color: #d4af37; font-weight: bold; }
    .neon-green { color: #00ff41; font-weight: bold; text-shadow: 0 0 10px #00ff41; }
    .neon-red { color: #ff0043; font-weight: bold; text-shadow: 0 0 10px #ff0043; }
    
    /* Özel Kart Tasarımı */
    .stock-card {
        background: linear-gradient(145deg, #1a1a1a, #0d0d0d);
        border: 1px solid #333;
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
        transition: transform 0.3s;
    }
    .stock-card:hover { transform: scale(1.02); border-color: #d4af37; }
    
    /* Metrik Kutuları */
    div[data-testid="stMetricValue"] { font-size: 24px; color: #d4af37; }
</style>
""", unsafe_allow_html=True)

# --- 2. HİSSE LİSTESİ (Örnek Katılım 30 - Burayı 217 Hisse ile Doldurabilirsin) ---
# Performans için şimdilik önemli hisseleri ekledim.
HISSEN_LISTESI = [
    "THYAO.IS", "ASELS.IS", "BIMAS.IS", "EREGL.IS", "FROTO.IS", "GUBRF.IS", 
    "HEKTS.IS", "KRDMD.IS", "KOZAL.IS", "KOZAA.IS", "ODAS.IS", "PETKM.IS", 
    "SASA.IS", "SISE.IS", "TUPRS.IS", "VESTL.IS", "KONTR.IS", "GESAN.IS", 
    "SMART.IS", "ALFAS.IS", "EUPWR.IS", "ASTOR.IS", "KCAER.IS", "MIATK.IS",
    "OYAKC.IS", "PGSUS.IS", "SAHOL.IS", "TOASO.IS", "TTKOM.IS", "TCELL.IS"
]

# --- 3. RAMKAR MOTORU (CORE ENGINE) ---
@st.cache_data(ttl=3600) # 1 saat cache tutar, hız kazandırır
def get_stock_data(symbol):
    try:
        # Veri Çekme (2 Yıllık)
        df = yf.download(symbol, period="2y", interval="1d", progress=False)
        if df.empty: return None
        
        # Haftalık Resample (TradingView Uyumu için Kritik)
        # 'Open' ilk gün, 'Close' son gün, 'High' en yüksek, 'Low' en düşük, 'Volume' toplam
        logic = {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}
        df_w = df.resample('W-FRI').agg(logic)
        
        # Boş veri kontrolü
        if len(df_w) < 50: return None 

        return df_w
    except Exception as e:
        return None

def analyze_stock(symbol, df_w):
    try:
        # --- İNDİKATÖRLER (Wilder's RMA Mantığı) ---
        # 1. EMA 20
        df_w['EMA20'] = ta.ema(df_w['Close'], length=20)
        
        # 2. Stochastic RSI
        stoch = ta.stochrsi(df_w['Close'], length=14, rsi_length=14, k=3, d=3)
        if stoch is not None:
            df_w['stoch_k'] = stoch.iloc[:, 0]
            df_w['stoch_d'] = stoch.iloc[:, 1]
        
        # 3. ADX ve DI
        adx = ta.adx(df_w['High'], df_w['Low'], df_w['Close'], length=14)
        if adx is not None:
            df_w['ADX'] = adx.iloc[:, 0]
            df_w['DI_plus'] = adx.iloc[:, 1]
            df_w['DI_minus'] = adx.iloc[:, 2]
            
        # 4. MFI
        df_w['MFI'] = ta.mfi(df_w['High'], df_w['Low'], df_w['Close'], df_w['Volume'], length=14)
        
        # 5. Parabolic SAR
        psar = ta.psar(df_w['High'], df_w['Low'], df_w['Close'], af0=0.02, af=0.02, max_af=0.2)
        if psar is not None:
             # psar fonksiyonu bazen long/short diye iki kolon döner, birleştirilmiş hali genelde ilki veya logic ile alınır
             # Basitlik için long/short birleşimini alıyoruz (pandas_ta yapısına göre)
             df_w['PSAR'] = psar.iloc[:, 0].combine_first(psar.iloc[:, 1])

        # --- SON HAFTA ANALİZİ ---
        current = df_w.iloc[-1]
        
        # NaN kontrolü
        if pd.isna(current['EMA20']) or pd.isna(current['ADX']): return None

        # --- 6/6 KRİTERLERİ ---
        # K1: Trend
        k1 = (current['Close'] > current['EMA20']) and (current['stoch_k'] > current['stoch_d'])
        # K2: Güç
        k2 = (current['ADX'] >= 28) and (current['DI_plus'] > current['DI_minus'])
        # K3: Hacim (Son hacim > 20 haftalık ortalama * 1.2)
        vol_avg = df_w['Volume'].rolling(20).mean().iloc[-1]
        k3 = current['Volume'] >= (vol_avg * 1.2)
        # K4: Güvenlik (SAR)
        k4 = current['Close'] > current['PSAR']
        # K5: Mesafe (Aşırı alım kontrolü)
        mesafe = ((current['Close'] - current['EMA20']) / current['EMA20']) * 100
        k5 = -2 <= mesafe <= 30
        # K6: Para Girişi
        k6 = current['MFI'] > 50

        total_score = sum([k1, k2, k3, k4, k5, k6])
        
        # RKP HESABI
        rkp = (0.5 * min(current['ADX']/50, 1)) + (0.3 * (current['MFI']/100)) - (0.2 * (1 - min(abs(mesafe)/20, 1)))

        # SESSİZ BİRİKİM ETİKETİ (Sadece Bilgi)
        # Basitleştirilmiş SB mantığı
        sb_label = "➖ NORMAL"
        if total_score == 6:
            if current['MFI'] > 60 and mesafe < 10: sb_label = "🔥 BİRİKİM"
            elif mesafe > 15: sb_label = "⚠️ PAHALI"
            else: sb_label = "🚀 TREND"

        return {
            "Hisse": symbol.replace(".IS", ""),
            "Skor": total_score,
            "Skor_Str": f"{total_score}/6",
            "RKP": round(rkp, 2),
            "Fiyat": round(current['Close'], 2),
            "ADX": round(current['ADX'], 1),
            "Mesafe": round(mesafe, 1),
            "MFI": round(current['MFI'], 1),
            "Etiket": sb_label,
            "Hacim_Kat": round(current['Volume'] / vol_avg, 1)
        }

    except Exception as e:
        return None

# --- 4. ARAYÜZ (SIDEBAR - MFS) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2910/2910312.png", width=100)
    st.title("RAMKAR v31")
    st.markdown("---")
    st.subheader("🛡️ MFS LIGHT")
    
    col1, col2 = st.columns(2)
    usd = col1.number_input("USD %", value=1.2, step=0.1)
    cds = col2.number_input("CDS", value=280, step=10)
    vix = st.slider("VIX", 0, 50, 18)
    xu100 = st.toggle("XU100 > EMA50", value=True)
    
    mfs_active = (usd < 3) and (cds < 450) and (vix < 30) and xu100
    
    if mfs_active:
        st.success("✅ PİYASA GÜVENLİ")
    else:
        st.error("⛔ RİSKLİ PİYASA (NAKİT)")
        
    st.markdown("---")
    st.info("Version: 31.0.4\nLast Update: 2026-01-11")

# --- 5. ANA EKRAN VE TARAMA ---
st.title("🦅 ALGORİTMİK PİYASA RADARI")
st.markdown("RAMKAR v31 Sistem Mimarisi: **Trend + Momentum + Hacim + Volatilite**")

if mfs_active:
    if st.button("🚀 TARAMAYI BAŞLAT", type="primary"):
        results = []
        progress_text = "Hisseler taranıyor, indikatörler hesaplanıyor..."
        my_bar = st.progress(0, text=progress_text)
        
        for i, symbol in enumerate(HISSEN_LISTESI):
            df_w = get_stock_data(symbol)
            if df_w is not None:
                res = analyze_stock(symbol, df_w)
                if res:
                    results.append(res)
            my_bar.progress((i + 1) / len(HISSEN_LISTESI))
            
        my_bar.empty()
        
        # --- SONUÇLARI GÖSTERME ---
        if results:
            df_res = pd.DataFrame(results)
            
            # Sadece 6/6 Olanları Al
            radar_kilit = df_res[df_res['Skor'] == 6].sort_values(by='RKP', ascending=False)
            
            # --- TAB 1: RADAR KİLİT ---
            tab1, tab2 = st.tabs(["🎯 RADAR KİLİT (6/6)", "📋 TÜM LİSTE"])
            
            with tab1:
                if not radar_kilit.empty:
                    st.markdown(f"### 🔥 Tespit Edilen {len(radar_kilit)} Fırsat")
                    
                    # Şık Kart Görünümü
                    cols = st.columns(3)
                    for idx, row in radar_kilit.reset_index().iterrows():
                        with cols[idx % 3]:
                            color = "#00ff41" if row['Etiket'] == "🔥 BİRİKİM" else "#d4af37"
                            st.markdown(f"""
                            <div class="stock-card">
                                <div style="display:flex; justify-content:space-between; align-items:center;">
                                    <h2 style="margin:0; color:{color};">{row['Hisse']}</h2>
                                    <span style="background:{color}; color:#000; padding:2px 8px; border-radius:4px; font-weight:bold;">{row['Etiket']}</span>
                                </div>
                                <div style="margin-top:10px; display:flex; justify-content:space-between;">
                                    <div><small style="color:#888;">RKP PUANI</small><br><span style="font-size:24px; color:#fff;">{row['RKP']}</span></div>
                                    <div><small style="color:#888;">FİYAT</small><br><span style="font-size:24px; color:#fff;">{row['Fiyat']} ₺</span></div>
                                </div>
                                <hr style="border-color:#333;">
                                <div style="display:flex; justify-content:space-between; font-size:14px; color:#aaa;">
                                    <span>ADX: {row['ADX']}</span>
                                    <span>Hacim: {row['Hacim_Kat']}x</span>
                                    <span>MFI: {row['MFI']}</span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    # --- GRAFİK ANALİZİ SEÇİMİ ---
                    st.markdown("---")
                    st.subheader("📈 Derinlemesine Grafik Analizi")
                    selected_stock = st.selectbox("İncelemek istediğin hisseyi seç:", radar_kilit['Hisse'].tolist())
                    
                    if selected_stock:
                        # Seçilen hissenin verisini tekrar al (Cache'den gelir, hızlıdır)
                        symbol_full = selected_stock + ".IS"
                        chart_data = get_stock_data(symbol_full)
                        
                        # Analiz fonksiyonunu tekrar çağırıp son indikatörleri eklemiş oluyoruz
                        analyze_stock(symbol_full, chart_data) 
                        
                        # Plotly Grafiği
                        fig = go.Figure()
                        
                        # Mum Grafiği
                        fig.add_trace(go.Candlestick(x=chart_data.index,
                                        open=chart_data['Open'], high=chart_data['High'],
                                        low=chart_data['Low'], close=chart_data['Close'],
                                        name='Fiyat'))
                        
                        # EMA 20
                        fig.add_trace(go.Scatter(x=chart_data.index, y=chart_data['EMA20'], 
                                                 line=dict(color='orange', width=2), name='EMA 20'))
                        
                        # SAR
                        fig.add_trace(go.Scatter(x=chart_data.index, y=chart_data['PSAR'], 
                                                 mode='markers', marker=dict(color='cyan', size=4), name='SAR Stop'))

                        fig.update_layout(
                            title=f"{selected_stock} Haftalık Analiz",
                            template="plotly_dark",
                            height=500,
                            xaxis_rangeslider_visible=False
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        st.info("💡 Mavi noktalar (SAR) stop seviyesidir. Turuncu çizgi (EMA20) ana trend desteğidir.")

                else:
                    st.warning("Bu hafta hiçbir hisse 6/6 kriterini geçemedi. Nakitte kalmak da bir pozisyondur.")
            
            with tab2:
                st.dataframe(df_res.style.applymap(lambda x: 'color: #00ff41' if x == "6/6" else 'color: #ff4b4b', subset=['Skor_Str']), use_container_width=True)
        else:
            st.error("Veri alınamadı veya liste boş.")

else:
    st.markdown("""
    <div style="text-align: center; padding: 50px; border: 2px solid #ff0043; border-radius: 20px; background-color: #1a0505;">
        <h1 class="neon-red">SİSTEM KİLİTLENDİ</h1>
        <h3>MFS (Makro Filtre) Kırmızı Alarm Veriyor</h3>
        <p>Piyasa koşulları şu an işlem yapmak için elverişli değil. Sermayeni koru.</p>
    </div>
    """, unsafe_allow_html=True)
