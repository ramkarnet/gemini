import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="RAMKAR DEBUG", layout="wide")
st.title("🛠️ RAMKAR v31 - HATA AYIKLAMA MODU")

# --- HİSSE LİSTESİ (Test için Azaltılmış Liste) ---
# Sorun çözülünce buraya 217 hisseni eklersin.
HISSEN_LISTESI = [
    "THYAO.IS", "ASELS.IS", "GARAN.IS", "AKBNK.IS", "EREGL.IS", 
    "KCHOL.IS", "SAHOL.IS", "SISE.IS", "TUPRS.IS", "BIMAS.IS"
]

def analyze_stock_safe(symbol):
    try:
        # 1. VERİ ÇEKME LOGU
        with st.status(f"{symbol} verisi çekiliyor...", expanded=False) as status:
            df = yf.download(symbol, period="1y", interval="1d", progress=False)
            
            if df.empty:
                st.write(f"❌ {symbol}: Veri Boş Geldi (Yahoo Vermedi)")
                status.update(label=f"{symbol} Başarısız", state="error")
                return None
            
            if len(df) < 50:
                st.write(f"⚠️ {symbol}: Yetersiz Veri ({len(df)} gün)")
                status.update(label=f"{symbol} Yetersiz", state="error")
                return None
                
            st.write(f"✅ {symbol}: {len(df)} günlük veri alındı.")
            
            # 2. RESAMPLE (Haftalık)
            logic = {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}
            df_w = df.resample('W-FRI').agg(logic)
            
            # 3. İNDİKATÖRLER
            df_w['EMA20'] = ta.ema(df_w['Close'], length=20)
            stoch = ta.stochrsi(df_w['Close'], length=14, rsi_length=14, k=3, d=3)
            
            if stoch is None:
                st.write(f"❌ {symbol}: İndikatör hesaplanamadı.")
                return None
                
            df_w['stoch_k'] = stoch.iloc[:, 0]
            df_w['stoch_d'] = stoch.iloc[:, 1]
            
            # ADX
            adx = ta.adx(df_w['High'], df_w['Low'], df_w['Close'], length=14)
            df_w['ADX'] = adx.iloc[:, 0]
            df_w['DI_plus'] = adx.iloc[:, 1]
            df_w['DI_minus'] = adx.iloc[:, 2]
            
            # MFI
            df_w['MFI'] = ta.mfi(df_w['High'], df_w['Low'], df_w['Close'], df_w['Volume'], length=14)
            
            # 4. SON DEĞERLER
            c = df_w.iloc[-1]
            
            # NaN Kontrolü
            if pd.isna(c['EMA20']) or pd.isna(c['ADX']):
                st.write(f"⚠️ {symbol}: Son verilerde eksiklik var.")
                return None

            # 5. PUANLAMA
            vol_avg = df_w['Volume'].rolling(20).mean().iloc[-1]
            
            k1 = (c['Close'] > c['EMA20']) and (c['stoch_k'] > c['stoch_d'])
            k2 = (c['ADX'] >= 20) # Test için düşürdüm
            
            score = 0
            if k1: score += 1
            if k2: score += 1
            # Diğer kriterleri test için kapattım, sadece sistem çalışıyor mu bakalım.
            
            status.update(label=f"{symbol} Tamamlandı! Skor: {score}", state="complete")
            
            return {
                "Hisse": symbol,
                "Fiyat": round(c['Close'], 2),
                "Skor": score,
                "Durum": "Başarılı"
            }

    except Exception as e:
        st.error(f"HATA {symbol}: {str(e)}")
        return None

# --- ANA EKRAN ---
st.info("Bu mod, sistemin neden veri alamadığını anlamak içindir. Hız yavaştır.")

if st.button("TEST TARAMASINI BAŞLAT"):
    results = []
    
    # İlerleme Çubuğu
    my_bar = st.progress(0)
    
    for i, hisse in enumerate(HISSEN_LISTESI):
        res = analyze_stock_safe(hisse)
        if res:
            results.append(res)
        my_bar.progress((i + 1) / len(HISSEN_LISTESI))
        
    st.divider()
    
    if len(results) > 0:
        st.success("✅ Bağlantı Başarılı! Veriler aşağıdadır:")
        df_res = pd.DataFrame(results)
        st.dataframe(df_res)
    else:
        st.error("⛔ Taramaya rağmen liste hala boş. Sorun %100 Yahoo Finance engellemesi.")
        st.warning("Çözüm: 'requirements.txt' dosyasına 'yfinance --upgrade' yazmayı dene veya 1 saat bekle.")
