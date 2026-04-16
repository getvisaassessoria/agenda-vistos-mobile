import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# Configuração da API
API_BASE = "https://app-vistos.onrender.com/api"
API_KEY = "G3tV1s4@2025!Ag3nd4"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

st.set_page_config(page_title="Agenda Vistos", page_icon="📱", layout="centered")
st.title("📱 Agenda na Mão")
st.write("Seus compromissos pendentes:")

@st.cache_data(ttl=30)
def buscar_pendentes():
    try:
        response = requests.get(f"{API_BASE}/compromissos", headers=headers)
        if response.status_code == 200:
            dados = response.json()
            # Filtra apenas pendentes (concluido == 0)
            pendentes = [c for c in dados if c.get('concluido') == 0]
            return pendentes
        else:
            st.error(f"Erro na API: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"Falha na conexão: {e}")
        return []

def dar_baixa(id_comp):
    try:
        response = requests.put(f"{API_BASE}/compromissos/{id_comp}", json={"concluido": 1}, headers=headers)
        if response.status_code == 200:
            return True
        else:
            st.error(f"Erro ao concluir: {response.status_code}")
            return False
    except Exception as e:
        st.error(f"Erro: {e}")
        return False

compromissos = buscar_pendentes()

if not compromissos:
    st.success("🎉 Tudo limpo! Nenhum compromisso pendente.")
else:
    # Agrupa por cliente
    clientes_dict = {}
    for comp in compromissos:
        cliente = comp['cliente']
        if cliente not in clientes_dict:
            clientes_dict[cliente] = []
        clientes_dict[cliente].append(comp)

    for cliente, lista in clientes_dict.items():
        with st.container(border=True):
            st.markdown(f"### 👤 {cliente}")
            for comp in lista:
                data_br = pd.to_datetime(comp['data']).strftime('%d/%m/%Y')
                st.markdown(f"**{comp['atividade']}** em {comp['local']}")
                st.markdown(f"📅 {data_br} às ⏰ {comp['hora']}")

                if st.button(f"✅ Dar Baixa", key=f"btn_{comp['id']}"):
                    if dar_baixa(comp['id']):
                        st.success("Baixa registrada!")
                        st.cache_data.clear()
                        st.rerun()
                st.write("")

    if st.button("🔄 Recarregar"):
        st.cache_data.clear()
        st.rerun()