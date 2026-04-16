import streamlit as st
import psycopg2
import pandas as pd

# Configuração para ficar bonito no celular
st.set_page_config(page_title="Agenda Vistos", page_icon="📱", layout="centered")

# A MESMA CHAVE DO MAC
DATABASE_URL = "postgresql://postgres.hlxobwdezofdpitsugxp:Getvisa061066@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"

def conectar():
    return psycopg2.connect(DATABASE_URL)

st.title("📱 Agenda na Mão")
st.write("Seus compromissos pendentes:")

try:
    conn = conectar()
    cursor = conn.cursor()
    # Busca apenas os pendentes, ordenados por data
    cursor.execute("SELECT id, data, hora, cliente, atividade, local FROM compromissos WHERE concluido = 0 ORDER BY data, hora")
    registros = cursor.fetchall()
    conn.close()

    if not registros:
        st.success("🎉 Tudo limpo! Nenhum compromisso pendente.")
    else:
        # 1. AGRUPAR OS COMPROMISSOS PELO NOME DO CLIENTE
        clientes_agrupados = {}
        for r in registros:
            id_comp, data, hora, cliente, atividade, local = r

            # Se o cliente ainda não está na lista, cria um espaço para ele
            if cliente not in clientes_agrupados:
                clientes_agrupados[cliente] = []

            # Adiciona o compromisso na lista desse cliente específico
            clientes_agrupados[cliente].append({
                'id': id_comp,
                'data': data,
                'hora': hora,
                'atividade': atividade,
                'local': local
            })

        # 2. MOSTRAR NA TELA EM FORMATO DE "CARTÕES"
        for cliente, lista_compromissos in clientes_agrupados.items():

            # Cria uma caixa visual com borda para cada cliente
            with st.container(border=True):
                st.markdown(f"### 👤 {cliente}")

                # Lista todas as etapas (Treinamento, CASV, etc) dentro do cartão do cliente
                for comp in lista_compromissos:
                    data_br = pd.to_datetime(comp['data']).strftime('%d/%m/%Y')

                    st.markdown(f"**{comp['atividade']}** em {comp['local']}")
                    st.markdown(f"📅 {data_br} às ⏰ {comp['hora']}")

                    # Botão de dar baixa individual para cada etapa
                    if st.button(f"✅ Dar Baixa", key=f"btn_{comp['id']}"):
                        conn = conectar()
                        cursor = conn.cursor()
                        cursor.execute("UPDATE compromissos SET concluido = 1 WHERE id = %s", (comp['id'],))
                        conn.commit()
                        conn.close()
                        st.rerun() # Atualiza a tela na hora

                    # Adiciona um pequeno espaço entre as etapas do mesmo cliente
                    st.write("") 

except Exception as e:
    st.error(f"Erro ao conectar no banco de dados: {e}")
