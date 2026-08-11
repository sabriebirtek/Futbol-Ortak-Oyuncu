import pandas as pd
import streamlit as st
import time
import os

# Sayfa ayarları
st.set_page_config(page_title="Futbol Ortak Oyuncu Bulucu & Oyun", page_icon="⚽", layout="centered")

# --- 1. VERİLERİ YÜKLEME VE BİÇİMLENDİRME ---
@st.cache_data
def verileri_yukle():
    clubs = pd.read_csv('clubs.csv')
    players = pd.read_csv('players.csv')
    
    if os.path.exists('transfers.csv'):
        transfers = pd.read_csv('transfers.csv')
    else:
        transfers = pd.DataFrame(columns=['player_id', 'from_club_id', 'to_club_id'])
        
    if os.path.exists('appearances.csv'):
        appearances = pd.read_csv('appearances.csv', usecols=['player_id', 'player_club_id'])
    else:
        appearances = pd.DataFrame(columns=['player_id', 'player_club_id'])
    
    lig_kisaltmalari = {
        'GB1': 'PL', 'ES1': 'LL', 'TR1': 'SL',
        'IT1': 'SA', 'L1': 'BL', 'FR1': 'L1'
    }
    
    clubs['lig_kod'] = clubs['domestic_competition_id'].map(lig_kisaltmalari).fillna(clubs['domestic_competition_id'])
    clubs['gosterim_adi'] = clubs.apply(lambda row: f"⚽ {row['name']} [{row['lig_kod']}]", axis=1)
    
    milli_takimlar = players['country_of_citizenship'].dropna().unique()
    milli_df = pd.DataFrame({
        'name': milli_takimlar,
        'gosterim_adi': [f"🌐 {ulke} (Milli Takım)" for ulke in milli_takimlar]
    })
    
    return clubs, players, transfers, appearances, milli_df

clubs, players, transfers, appearances, milli_df = verileri_yukle()
tum_secenekler = sorted(list(clubs['gosterim_adi'].dropna()) + list(milli_df['gosterim_adi'].dropna()))
tum_oyuncular = sorted(players['name'].dropna().unique().tolist())

# --- YARDIMCI GELİŞMİŞ SORGULAR ---
def temiz_isim_al(gosterim):
    if not gosterim:
        return ""
    if gosterim.startswith("⚽ "):
        return gosterim.replace("⚽ ", "").split(" [")[0]
    elif gosterim.startswith("🌐 "):
        return gosterim.replace("🌐 ", "").replace(" (Milli Takım)", "")
    return gosterim

def bir_takimin_tum_oyuncularini_getir(takim_veya_ulke_adi):
    p_ids = set()
    eslesen_kulup = clubs[clubs['name'] == takim_veya_ulke_adi]
    if not eslesen_kulup.empty:
        c_id = eslesen_kulup['club_id'].values[0]
        p_ids.update(players[players['current_club_id'] == c_id]['player_id'].dropna().tolist())
        if not transfers.empty:
            t_from = transfers[transfers['from_club_id'] == c_id]['player_id'].dropna().tolist()
            t_to = transfers[transfers['to_club_id'] == c_id]['player_id'].dropna().tolist()
            p_ids.update(t_from + t_to)
        if not appearances.empty:
            app_p = appearances[appearances['player_club_id'] == c_id]['player_id'].dropna().tolist()
            p_ids.update(app_p)
        return p_ids

    eslesen_milli = players[players['country_of_citizenship'] == takim_veya_ulke_adi]
    if not eslesen_milli.empty:
        return set(eslesen_milli['player_id'].dropna().tolist())
        
    return set()

def oyuncunun_takimlarini_getir(oyuncu_adi):
    p_row = players[players['name'].str.lower() == oyuncu_adi.lower()]
    if p_row.empty:
        return None, []
    
    p_id = p_row['player_id'].values[0]
    milli = p_row['country_of_citizenship'].values[0]
    kulup_idleri = set()
    
    curr_c = p_row['current_club_id'].values[0]
    if pd.notna(curr_c) and curr_c != -1:
        kulup_idleri.add(int(curr_c))
        
    if not transfers.empty:
        p_transfers = transfers[transfers['player_id'] == p_id]
        from_ids = p_transfers['from_club_id'].dropna().tolist()
        to_ids = p_transfers['to_club_id'].dropna().tolist()
        for cid in from_ids + to_ids:
            if pd.notna(cid) and cid != -1:
                kulup_idleri.add(int(cid))
                
    if not appearances.empty:
        app_ids = appearances[appearances['player_id'] == p_id]['player_club_id'].dropna().tolist()
        for cid in app_ids:
            if pd.notna(cid) and cid != -1:
                kulup_idleri.add(int(cid))
                
    oynadigi_kulupler = clubs[clubs['club_id'].isin(kulup_idleri)]['name'].unique().tolist()
    return milli, oynadigi_kulupler

def ortak_oyunculari_getir(takim1, takim2):
    o1 = bir_takimin_tum_oyuncularini_getir(takim1)
    o2 = bir_takimin_tum_oyuncularini_getir(takim2)
    ortak_ids = o1.intersection(o2)
    return sorted(players[players['player_id'].isin(ortak_ids)]['name'].unique().tolist())

# --- OYUNU TEMİZ SIFIRLAMA FONKSİYONU ---
def oyunu_sifirla():
    st.session_state.game_step = "p1_select"
    st.session_state.p1_team = ""
    st.session_state.p2_team = ""
    st.session_state.buzzer_winner = None
    st.session_state.user_tahmin = None
    for key in ["p1_input", "p2_input", "game_predict_selectbox"]:
        if key in st.session_state:
            del st.session_state[key]


# --- ANA MOD SEÇİMİ ---
ana_mod = st.radio("Lütfen Mod Seçin:", ["🔍 Sorgulama Modu", "🎮 1v1 Oyun Modu"], horizontal=True)
st.divider()

# ==========================================
# 1. SORGULAMA MODU
# ==========================================
if ana_mod == "🔍 Sorgulama Modu":
    sorgu_tab1, sorgu_tab2 = st.tabs(["⚽ Kulüp Sorgulama", "👤 Oyuncu Sorgulama"])
    
    with sorgu_tab1:
        st.subheader("İki Takım / Ülke Arasındaki Ortak Oyuncular")
        col1, col2 = st.columns(2)
        with col1:
            secim1 = st.selectbox("1. Takım / Ülke", options=tum_secenekler, index=None, placeholder="1. Takım seçin...", key="sorgu_t1")
        with col2:
            secim2 = st.selectbox("2. Takım / Ülke", options=tum_secenekler, index=None, placeholder="2. Takım seçin...", key="sorgu_t2")
            
        if st.button("Ortak Oyuncuları Getir", type="primary", use_container_width=True, key="btn_sorgu_kulup"):
            if not secim1 or not secim2:
                st.info("Lütfen her iki kutudan da seçim yapın.")
            else:
                t1, t2 = temiz_isim_al(secim1), temiz_isim_al(secim2)
                sonuclar = ortak_oyunculari_getir(t1, t2)
                st.divider()
                if sonuclar:
                    st.success(f"**{t1}** ve **{t2}** takımlarında oynamış **{len(sonuclar)}** oyuncu bulundu:")
                    for oy in sonuclar:
                        st.write(f"• {oy}")
                else:
                    st.warning(f"**{t1}** ve **{t2}** arasında ortak oyuncu bulunamadı.")

    with sorgu_tab2:
        st.subheader("Oyuncunun Oynadığı Tüm Takımlar")
        secilen_oyuncu = st.selectbox("Oyuncu İsmi Girin / Seçin", options=tum_oyuncular, index=None, placeholder="Örn: Mesut Özil...", key="sorgu_p_select")
        
        if st.button("Takımları Getir", type="primary", use_container_width=True, key="btn_sorgu_oyuncu"):
            if secilen_oyuncu:
                milli, kulupler = oyuncunun_takimlarini_getir(secilen_oyuncu)
                st.divider()
                st.write(f"### 👤 {secilen_oyuncu}")
                if milli:
                    st.markdown(f"**🌐 {milli} (Milli Takım)**")
                st.write("**Oynadığı Kulüpler:**")
                if kulupler:
                    for k in sorted(kulupler):
                        st.write(f"• ⚽ {k}")
                else:
                    st.write("*Kulüp kariyer bilgisi bulunamadı.*")
            else:
                st.info("Lütfen bir oyuncu seçin.")

# ==========================================
# 2. OYUN MODU (1v1 SPLIT SCREEN)
# ==========================================
else:
    st.subheader("🎮 2 Kişilik Hızlı Cevap Oyunu")
    
    if "game_step" not in st.session_state:
        st.session_state.game_step = "p1_select"
    if "p1_team" not in st.session_state:
        st.session_state.p1_team = ""
    if "p2_team" not in st.session_state:
        st.session_state.p2_team = ""
    if "buzzer_winner" not in st.session_state:
        st.session_state.buzzer_winner = None
    if "user_tahmin" not in st.session_state:
        st.session_state.user_tahmin = None

    # --- ADIM 1: 1. OYUNCU TAKIM SEÇİMİ ---
    if st.session_state.game_step == "p1_select":
        st.info("👤 **1. Oyuncu:** Lütfen takımınızı seçin (İkinci oyuncu bakmasın!)")
        p1_sel = st.selectbox("1. Oyuncunun Takımı", options=tum_secenekler, index=None, placeholder="Takım seç...", key="p1_input")
        
        if st.button("1. Takımı Onayla ve Gizle 🔒", type="primary"):
            if p1_sel:
                st.session_state.p1_team = temiz_isim_al(p1_sel)
                st.session_state.game_step = "p2_select"
                st.rerun()
            else:
                st.warning("Lütfen bir takım seçin.")

    # --- ADIM 2: 2. OYUNCU TAKIM SEÇİMİ ---
    elif st.session_state.game_step == "p2_select":
        st.info("👤 **2. Oyuncu:** Lütfen takımınızı seçin!")
        p2_sel = st.selectbox("2. Oyuncunun Takımı", options=tum_secenekler, index=None, placeholder="Takım seç...", key="p2_input")
        
        if st.button("2. Takımı Onayla ve Oyunu Başlat 🚀", type="primary"):
            if p2_sel:
                st.session_state.p2_team = temiz_isim_al(p2_sel)
                st.session_state.game_step = "countdown"
                st.rerun()
            else:
                st.warning("Lütfen bir takım seçin.")

    # --- ADIM 3: GERİ SAYIM ---
    elif st.session_state.game_step == "countdown":
        countdown_box = st.empty()
        for i in range(5, 0, -1):
            countdown_box.write(f"# ⏳ Takımlar Açıklanıyor... {i}")
            time.sleep(1)
        st.session_state.game_step = "play"
        st.rerun()

    # --- ADIM 4: TIKLAMA EKRANI ---
    elif st.session_state.game_step == "play":
        t1 = st.session_state.p1_team
        t2 = st.session_state.p2_team
        
        st.write("---")
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown(f"### 🔵 1. Oyuncu\n# **{t1}**")
            if st.button(f"👈 Ben Biliyorum! ({t1})", type="primary", use_container_width=True, key="btn_p1_buzz"):
                st.session_state.buzzer_winner = "1. Oyuncu"
                st.session_state.game_step = "answer"
                st.rerun()

        with col_right:
            st.markdown(f"### 🔴 2. Oyuncu\n# **{t2}**")
            if st.button(f"Ben Biliyorum! ({t2}) 👉", type="primary", use_container_width=True, key="btn_p2_buzz"):
                st.session_state.buzzer_winner = "2. Oyuncu"
                st.session_state.game_step = "answer"
                st.rerun()

        st.write("---")
        if st.button("⚪ Pas / İki Takımda Ortak Oyuncu Yok", use_container_width=True):
            st.session_state.game_step = "result_pas"
            st.rerun()

    # --- ADIM 5: OYUNCU İSMİ SEÇİM EKRANI ---
    elif st.session_state.game_step == "answer":
        winner = st.session_state.buzzer_winner
        t1 = st.session_state.p1_team
        t2 = st.session_state.p2_team
        
        st.success(f"🔔 **İlk tıklayan: {winner}!**")
        st.write(f"**{t1}** ve **{t2}** takımlarında oynamış bir futbolcu seçin/yazın:")
        
        tahmin_oyuncu = st.selectbox(
            "Oyuncu İsmi Girin / Seçin:",
            options=tum_oyuncular,
            index=None,
            placeholder="Örn: Mesut Özil...",
            key="game_predict_selectbox"
        )
        
        if st.button("Cevabı Gönder 🎯", type="primary"):
            if tahmin_oyuncu:
                st.session_state.user_tahmin = tahmin_oyuncu
                st.session_state.game_step = "result_answer"
                st.rerun()
            else:
                st.warning("Lütfen bir oyuncu ismi seçin veya yazın.")

    # --- ADIM 6A: CEVAP SONUÇ EKRANI ---
    elif st.session_state.game_step == "result_answer":
        winner = st.session_state.buzzer_winner
        t1 = st.session_state.p1_team
        t2 = st.session_state.p2_team
        tahmin = st.session_state.user_tahmin
        dogru_cevaplar = ortak_oyunculari_getir(t1, t2)
        
        dogru_mu = tahmin in dogru_cevaplar
        if dogru_mu:
            st.balloons()
            st.success(f"🎉 **DOĞRU CEVAP!** ({tahmin}) - {winner} puanı kazandı!")
        else:
            diğer_oyuncu = "2. Oyuncu" if winner == "1. Oyuncu" else "1. Oyuncu"
            st.error(f"❌ **YANLIŞ CEVAP!** {tahmin}, bu iki takımda da ortak oynamamış. Sıra **{diğer_oyuncu}** tarafına geçti.")
        
        st.divider()
        st.write(f"**{t1}** ve **{t2}** Ortak Oyuncuları ({len(dogru_cevaplar)} kişi):")
        for oy in dogru_cevaplar:
            st.write(f"• {oy}")
            
        st.write("---")
        if st.button("Yeni Oyun Başlat 🔄", type="primary", use_container_width=True):
            oyunu_sifirla()
            st.rerun()

    # --- ADIM 6B: PAS SONUÇ EKRANI ---
    elif st.session_state.game_step == "result_pas":
        t1 = st.session_state.p1_team
        t2 = st.session_state.p2_team
        dogru_cevaplar = ortak_oyunculari_getir(t1, t2)
        
        if len(dogru_cevaplar) == 0:
            st.balloons()
            st.success(f"Tebrikler! Doğru bildiniz, **{t1}** ve **{t2}** arasında gerçekten HİÇ ortak oyuncu yoktu!")
        else:
            st.error(f"Yanlış Pas! Aslında **{t1}** ve **{t2}** arasında **{len(dogru_cevaplar)}** ortak oyuncu vardı:")
            for oy in dogru_cevaplar:
                st.write(f"• {oy}")
                
        st.write("---")
        if st.button("Yeni Oyun Başlat 🔄", type="primary", use_container_width=True):
            oyunu_sifirla()
            st.rerun()