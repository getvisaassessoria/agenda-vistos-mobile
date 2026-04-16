import psycopg2
from datetime import datetime, timedelta
import requests

# ==========================================
# CONEXÃO COM O SUPABASE
DATABASE_URL = "postgresql://postgres.hlxobwdezofdpitsugxp:Getvisa061066@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"
RESEND_API_KEY = "re_EDi3taB6_9UAiyMMCoHs7bdtWoxibFKWL"
# ==========================================

def enviar_email(destinatario, assunto, corpo_html):
    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "from": "GetVisa <contato@getvisa.com.br>",
        "to": [destinatario],
        "subject": assunto,
        "html": corpo_html
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            print(f"✅ E-mail enviado para {destinatario}")
        else:
            print(f"❌ Erro ao enviar e-mail para {destinatario}: {response.text}")
    except Exception as e:
        print(f"❌ Falha na requisição: {e}")

def enviar_whatsapp(telefone, mensagem):
    # Simulação - substitua pela API real quando tiver
    print(f"📱 WhatsApp para {telefone}: {mensagem}")

def main():
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    hoje = datetime.now().date()
    # Datas no formato ISO (YYYY-MM-DD) para comparar com a coluna DATE
    data_alvo_1 = (hoje + timedelta(days=1)).strftime("%Y-%m-%d")
    data_alvo_3 = (hoje + timedelta(days=3)).strftime("%Y-%m-%d")
    print(f"Buscando compromissos para {data_alvo_1} e {data_alvo_3}")

    cursor.execute("""
        SELECT c.id, c.cliente, c.atividade, c.data, c.hora, c.local, 
               cl.email, cl.telefone, cl.nome_completo
        FROM compromissos c
        LEFT JOIN clientes cl ON c.cliente_id = cl.id
        WHERE c.data IN (%s, %s) AND c.concluido = 0
    """, (data_alvo_1, data_alvo_3))
    compromissos = cursor.fetchall()
    conn.close()

    if not compromissos:
        print("Nenhum compromisso encontrado para as datas.")
        return

    for comp in compromissos:
        comp_id, cliente_nome, atividade, data_comp, hora_comp, local, email, telefone, nome_cliente = comp
        # data_comp já é um objeto date (porque a coluna é DATE)
        # Converte para string no formato brasileiro para exibição
        data_exibicao = data_comp.strftime("%d/%m/%Y") if hasattr(data_comp, 'strftime') else data_comp
        nome_destinatario = nome_cliente if nome_cliente else cliente_nome.split(' (+')[0]

        dias_restantes = (data_comp - hoje).days if hasattr(data_comp, 'strftime') else 0
        if dias_restantes == 1:
            titulo = "🔔 Lembrete: seu compromisso é amanhã!"
        elif dias_restantes == 3:
            titulo = "📅 Lembrete: você tem um compromisso em 3 dias"
        else:
            continue

        corpo_email = f"""
        <h2>Olá {nome_destinatario},</h2>
        <p>Você tem um compromisso agendado:</p>
        <ul>
            <li><strong>Atividade:</strong> {atividade}</li>
            <li><strong>Data:</strong> {data_exibicao}</li>
            <li><strong>Horário:</strong> {hora_comp}</li>
            <li><strong>Local:</strong> {local or 'A definir'}</li>
        </ul>
        <p>Não se esqueça dos documentos necessários.</p>
        <p>Atenciosamente,<br>Equipe GetVisa</p>
        """

        if email:
            enviar_email(email, titulo, corpo_email)
        else:
            print(f"⚠️ Compromisso ID {comp_id} não tem e-mail cadastrado (cliente_id provavelmente nulo).")

        if telefone:
            mensagem = f"🔔 Lembrete GetVisa: {atividade} no dia {data_exibicao} às {hora_comp} em {local}."
            enviar_whatsapp(telefone, mensagem)

if __name__ == "__main__":
    main()