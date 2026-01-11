import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="RAMKAR TURBO v31", layout="wide", page_icon="🚀")

# --- CSS (Aynı Stil) ---
st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    h1, h2, h3 { color: #e0e0e0; }
    .stock-card {
        background: linear-gradient(145deg, #1a1a1a, #0d0d0d);
        border: 1px solid #333;
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# --- HİSSE LİSTESİ (Test için 30 tane, sonra 217'yi ekle) ---
HISSEN_LISTESI = [
    "THYAO.IS", "ASELS.IS", "BIMAS.IS", "EREGL.IS", "FROTO.IS", "GUBRF.IS", 
    "HEKTS.IS", "KRDMD.IS", "KOZAL.IS", "KOZAA.IS", "ODAS.IS", "PETKM.IS", 
    "SASA.IS", "SISE.IS", "TUPRS.IS", "VESTL.IS", "KONTR.IS", "GESAN.IS", 
    "SMART.IS", "ALFAS.IS", "EUPWR.IS", "ASTOR.IS", "KCAER.IS", "MIATK.IS",
    "OYAKC.IS", "PGSUS.IS", "SAHOL.IS", "TOASO.IS", "TTKOM.IS", "TCELL.IS"
]

# --- TEK HİSSE ANALİZ FONKSİYONU ---
def analyze_single_stock(symbol):
    try:
        # Veri Çekme (Sadece Gerekli Sütunlar)
        df = yf.download(symbol, period="2y", interval="1d", progress=False)
        if df.empty or len(df) < 50: return None
        
        # Resample (Haftalık)
        logic = {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}
        df_w = df.resample('W-FRI').agg(logic)
        
        # --- HESAPLAMALAR ---
        # EMA20
        df_w['EMA20'] = ta.ema(df_w['Close'], length=20)
        
        # StochRSI
        stoch = ta.stochrsi(df_w['Close'], length=14, rsi_length=14, k=3, d=3)
        if stoch is not None:
            df_w['stoch_k'] = stoch.iloc[:, 0]
            df_w['stoch_d'] = stoch.iloc[:, 1]
        
        # ADX
        adx = ta.adx(df_w['High'], df_w['Low'], df_w['Close'], length=14)
        if adx is not None:
            df_w['ADX'] = adx.iloc[:, 0]
            df_w['DI_plus'] = adx.iloc[:, 1]
            df_w['DI_minus'] = adx.iloc[:, 2]
            
        # MFI & SAR
        df_w['MFI'] = ta.mfi(df_w['High'], df_w['Low'], df_w['Close'], df_w['Volume'], length=14)
        psar = ta.psar(df_w['High'], df_w['Low'], df_w['Close'], af0=0.02, af=0.02, max_af=0.2)
        if psar is not None:
             df_w['PSAR'] = psar.iloc[:, 0].combine_first(psar.iloc[:, 1])

        # --- SON BAR KONTROLÜ ---
        c = df_w.iloc[-1]
        
        # Hata önleme
        if pd.isna(c['EMA20']) or pd.isna(c['ADX']): return None

        # 6/6 KRİTERLERİ
        vol_avg = df_w['Volume'].rolling(20).mean().iloc[-1]
        
        checks = [
            (c['Close'] > c['EMA20']) and (c['stoch_k'] > c['stoch_d']), # K1
            (c['ADX'] >= 28) and (c['DI_plus'] > c['DI_minus']),         # K2
            c['Volume'] >= (vol_avg * 1.2),                              # K3
            c['Close'] > c['PSAR'],                                      # K4
            -2 <= (((c['Close'] - c['EMA20']) / c['EMA20']) * 100) <= 30,# K5
            c['MFI'] > 50                                                # K6
        ]
        
        score = sum(checks)
        mesafe = ((c['Close'] - c['EMA20']) / c['EMA20']) * 100
        
        # RKP
        rkp = (0.5 * min(c['ADX']/50, 1)) + (0.3 * (c['MFI']/100)) - (0.2 * (1 - min(abs(mesafe)/20, 1)))
        
        # Etiket
        etiket = "➖ NORMAL"
        if score == 6:
            if c['MFI'] > 60 and mesafe < 10: etiket = "🔥 BİRİKİM"
            elif mesafe > 15: etiket = "⚠️ PAHALI"
            else: etiket = "🚀 TREND"

        return {
            "Hisse": symbol.replace(".IS", ""),
            "Skor": score,
            "RKP": round(rkp, 2),
            "Fiyat": round(c['Close'], 2),
            "ADX": round(c['ADX'], 1),
            "Mesafe": round(mesafe, 1),
            "Etiket": etiket
        }

    except Exception:
        return None

# --- ARAYÜZ ---
st.sidebar.title("RAMKAR v31")
mfs = st.sidebar.checkbox("MFS (Piyasa) Onayı", value=True)

st.title("🚀 RAMKAR TURBO TARAMA")

if st.button("TARAMAYI BAŞLAT (HIZLI MOD)"):
    if not mfs:
        st.error("MFS Kapalı! İşlem yapılmaz.")
    else:
        results = []
        status_text = st.empty()
        bar = st.progress(0)
        
        # --- MULTITHREADING MOTORU (BURASI HIZLANDIRIR) ---
        status_text.text("Motorlar çalışıyor... Çoklu tarama başladı...")
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Hisseleri 10'ar 10'ar paralel tarar
            futures = list(executor.map(analyze_single_stock, HISSEN_LISTESI))
            
            for i, res in enumerate(futures):
                if res:
                    results.append(res)
                bar.progress((i + 1) / len(HISSEN_LISTESI))
        
        status_text.text("Tarama Tamamlandı!")
        
        # --- SONUÇ GÖSTERİMİ ---
        if results:
            df = pd.DataFrame(results)
            radar = df[df['Skor'] == 6].sort_values(by='RKP', ascending=False)
            
            if not radar.empty:
                st.success(f"🎯 {len(radar)} Adet 'Radar Kilit' Hisse Bulundu!")
                
                cols = st.columns(3)
                for idx, row in radar.reset_index().iterrows():
                    with cols[idx % 3]:
                        color = "#00ff41" if row['Etiket'] == "🔥 BİRİKİM" else "#d4af37"
                        st.markdown(f"""
                        <div class="stock-card">
                            <h2 style="color:{color}">{row['Hisse']}</h2>
                            <p><b>{row['Etiket']}</b> | RKP: {row['RKP']}</p>
                            <p>Fiyat: {row['Fiyat']} | ADX: {row['ADX']}</p>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.warning("6/6 Kriterine uyan hisse yok.")
                
            with st.expander("Tüm Liste"):
                st.dataframe(df)
        else:
            st.error("Veri çekilemedi. Bağlantıyı kontrol et.")
