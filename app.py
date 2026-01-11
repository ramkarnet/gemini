import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="RAMKAR RADAR v31", layout="wide")

# --- 217 HİSSELİK LİSTE (Özetlenmiş Örnektir, Buraya Tüm Katılım Endeksini Ekle) ---
KATILIM_HİSSELERİ = ["OFSYM.IS", "KCAER.IS", "MIATK.IS", "ASELS.IS", "THYAO.IS", "SISE.IS", "EREGL.IS", "ASTOR.IS"] # +210 hisse buraya gelecek

# --- RAMKAR MOTORU (Hesaplama Fonksiyonu) ---
def ramkar_engine(symbol):
    try:
        # 1. Veri Çekme (Günlük çekip Haftalığa çeviriyoruz - Resample)
        df = yf.download(symbol, period="2y", interval="1d", progress=False)
        df_w = df.resample('W-FRI').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last', 'Volume':'sum'})
        
        # 2. İndikatörler (Wilder's RMA Uyumu ile)
        df_w['EMA20'] = ta.ema(df_w['Close'], length=20)
        stoch = ta.stochrsi(df_w['Close'], length=14, rsi_length=14, k=3, d=3)
        df_w['stoch_k'] = stoch['STOCHRSIk_14_14_3_3']
        df_w['stoch_d'] = stoch['STOCHRSId_14_14_3_3']
        
        adx = ta.adx(df_w['High'], df_w['Low'], df_w['Close'], length=14)
        df_w['ADX'] = adx['ADX_14']
        df_w['DI_plus'] = adx['DMP_14']
        df_w['DI_minus'] = adx['DMN_14']
        
        df_w['MFI'] = ta.mfi(df_w['High'], df_w['Low'], df_w['Close'], df_w['Volume'], length=14)
        psar = ta.psar(df_w['High'], df_w['Low'], df_w['Close'])
        df_w['PSAR'] = psar['PSARl_0.02_0.2'] # Uzun (long) sinyali
        
        # 3. Kriter Kontrolleri (6/6)
        c = df_w.iloc[-1]
        c_prev = df_w.iloc[-2]
        
        k1 = c['Close'] > c['EMA20'] and c['stoch_k'] > c['stoch_d']
        k2 = c['ADX'] >= 28 and c['DI_plus'] > c['DI_minus']
        k3 = c['Volume'] >= df_w['Volume'].rolling(20).mean().iloc[-1] * 1.2
        k4 = c['Close'] > c['PSAR']
        mesafe = ((c['Close'] - c['EMA20']) / c['EMA20']) * 100
        k5 = -2 <= mesafe <= 30
        k6 = c['MFI'] > 50
        
        skor = sum([k1, k2, k3, k4, k5, k6])
        
        # 4. RKP Puanı (Normalizasyon)
        rkp = (0.5 * min(c['ADX']/50, 1)) + (0.3 * (c['MFI']/100)) - (0.2 * (1 - min(abs(mesafe)/20, 1)))
        
        return {
            "Hisse": symbol.replace(".IS", ""),
            "Skor": f"{skor}/6",
            "RKP": round(rkp, 2),
            "ADX": round(c['ADX'], 1),
            "Mesafe": round(mesafe, 1),
            "Son Fiyat": round(c['Close'], 2)
        }
    except:
        return None

# --- STREAMLIT ARAYÜZ ---
st.title("🏆 RAMKAR v31 Professional Scanner")
st.write("217 Katılım Endeksi Hissesi Canlı Olarak Taranıyor...")

if st.button("TARAMAYI BAŞLAT"):
    results = []
    progress_bar = st.progress(0)
    
    for i, hisse in enumerate(KATILIM_HİSSELERİ):
        res = ramkar_engine(hisse)
        if res:
            results.append(res)
        progress_bar.progress((i + 1) / len(KATILIM_HİSSELERİ))
    
    full_df = pd.DataFrame(results)
    
    # --- FILTRELEME: SADECE 6/6 OLANLAR ---
    radar_kilit = full_df[full_df['Skor'] == "6/6"].sort_values(by="RKP", ascending=False)
    
    st.divider()
    
    if not radar_kilit.empty:
        st.header(f"🎯 Radar Kilit: {len(radar_kilit)} Hisse Bulundu")
        
        # Şık Kartlar
        cols = st.columns(len(radar_kilit))
        for idx, row in radar_kilit.reset_index().iterrows():
            with cols[idx]:
                st.metric(label=row['Hisse'], value=row['Son Fiyat'], delta=f"RKP: {row['RKP']}")
                st.write(f"ADX: {row['ADX']} | Mesafe: %{row['Mesafe']}")
                st.button("Analize Git", key=row['Hisse'])
    else:
        st.error("Şu an hiçbir hisse 6/6 kriterini karşılamıyor. Sabırla bekle.")

    st.subheader("📋 Tüm Tarama Listesi")
    st.dataframe(full_df)
