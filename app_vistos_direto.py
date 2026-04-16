import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime

# MESMA CONEXÃO DO SEU SCRIPT PYTHON (funciona)
DATABASE_URL = "postgresql://postgres.hlxobwdezofdpitsugxp:Getvisa061066@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"

def conectar():
    return psycopg2.connect(DATABASE_URL)

st.set_page_config(page_title="Agenda Vistos", page_icon="📱", layout="centered")
st.title("📱 Agenda Interna - Vistos")
st.write("Compromissos pendentes (CASV, Entrevista, Treinamento)")

# Buscar compromissos pendentes
try:
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, data, hora, cliente, atividade, local 
        FROM compromissos 
        WHERE concluido = 0 
        ORDER BY data, hora
    """)
    registros = cursor.fetchall()
    conn.close()
except Exception as e:
    st.error(f"Erro ao conectar: {e}")
    registros = []

if not registros:
    st.success("🎉 Nenhum compromisso pendente!")
else:
    # Agrupar por cliente (igual ao seu código original)
    clientes_dict = {}
    for r in registros:
        id_comp, data, hora, cliente, atividade, local = r
        if cliente not in clientes_dict:
            clientes_dict[cliente] = []
        clientes_dict[cliente].append({
            'id': id_comp,
            'data': data,
            'hora': hora,
            'atividade': atividade,
            'local': local
        })

    # Exibir cartões
    for cliente, lista in clientes_dict.items():
        with st.container(border=True):
            st.markdown(f"### 👤 {cliente}")
            for comp in lista:
                data_br = pd.to_datetime(comp['data']).strftime('%d/%m/%Y')
                st.markdown(f"**{comp['atividade']}** em {comp['local']}")
                st.markdown(f"📅 {data_br} às ⏰ {comp['hora']}")

                # Botão de dar baixa
                if st.button(f"✅ Dar Baixa", key=f"btn_{comp['id']}"):
                    try:
                        conn2 = conectar()
                        cursor2 = conn2.cursor()
                        cursor2.execute("UPDATE compromissos SET concluido = 1 WHERE id = %s", (comp['id'],))
                        conn2.commit()
                        conn2.close()
                        st.success("Baixa registrada!")
                        st.rerun()
                    except Exception as e2:
                        st.error(f"Erro: {e2}")
                st.write("")  # espaço

    if st.button("🔄 Recarregar"):
        st.rerun()