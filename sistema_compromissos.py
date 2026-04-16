import psycopg2
import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter import ttk
from datetime import datetime, timedelta
import PyPDF2
import re

# ==========================================
# ☁️ CONEXÃO COM A NUVEM (SUPABASE)
DATABASE_URL = "postgresql://postgres.hlxobwdezofdpitsugxp:Getvisa061066@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"
# ==========================================

alertas_disparados = set()
lista_vars_acompanhantes = []

def criar_banco():
    """Cria a tabela compromissos se não existir, garantindo as colunas cliente_id e concluido."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS compromissos (
            id SERIAL PRIMARY KEY,
            cliente TEXT NOT NULL,
            atividade TEXT NOT NULL,
            data TEXT NOT NULL,
            hora TEXT NOT NULL,
            local TEXT NOT NULL,
            concluido INTEGER DEFAULT 0,
            cliente_id UUID REFERENCES clientes(id)
        )
        """)
        conn.commit()
        conn.close()
        print("Banco de dados verificado/criado com sucesso.")
    except Exception as e:
        print(f"Erro ao conectar na nuvem: {e}")

def buscar_cliente_id(nome_cliente):
    """Busca o UUID de um cliente na tabela 'clientes' usando o nome (busca aproximada)."""
    if not nome_cliente:
        return None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        # Busca por nome completo (case-insensitive, e aceita partes do nome)
        cursor.execute("SELECT id FROM clientes WHERE nome_completo ILIKE %s LIMIT 1", (f"%{nome_cliente}%",))
        resultado = cursor.fetchone()
        conn.close()
        return resultado[0] if resultado else None
    except Exception as e:
        print(f"Erro ao buscar cliente_id para '{nome_cliente}': {e}")
        return None

# --- FUNÇÕES DE MÁSCARA E AUTOCOMPLETAR ---
def mascara_data(event, entry):
    if event.keysym in ['BackSpace', 'Delete']: return
    texto = entry.get().replace('/', '')
    if len(texto) > 8: texto = texto[:8]
    novo_texto = ""
    for i, char in enumerate(texto):
        if i in [2, 4]: novo_texto += '/'
        novo_texto += char
    entry.delete(0, tk.END)
    entry.insert(0, novo_texto)

def mascara_hora(event, entry):
    if event.keysym in ['BackSpace', 'Delete']: return
    texto = entry.get().replace(':', '')
    if len(texto) > 4: texto = texto[:4]
    novo_texto = ""
    for i, char in enumerate(texto):
        if i == 2: novo_texto += ':'
        novo_texto += char
    entry.delete(0, tk.END)
    entry.insert(0, novo_texto)

def autocompletar_local(event):
    digitado = var_local.get().upper()
    if digitado == "":
        entry_local['values'] = locais_permitidos
    else:
        filtrados = [l for l in locais_permitidos if l.startswith(digitado)]
        entry_local['values'] = filtrados
    entry_local.event_generate('<Down>')

def forcar_maiusculo_var(var):
    var.set(var.get().upper())

# --- FUNÇÕES DINÂMICAS PARA ACOMPANHANTES ---
def adicionar_campo_acompanhante(nome_inicial=""):
    num = len(lista_vars_acompanhantes) + 1
    var_acomp = tk.StringVar(value=nome_inicial)
    var_acomp.trace_add("write", lambda *args, v=var_acomp: forcar_maiusculo_var(v))
    lista_vars_acompanhantes.append(var_acomp)

    linha = tk.Frame(frame_acompanhantes)
    linha.pack(fill="x", pady=2)
    tk.Label(linha, text=f"Acompanhante {num}:", width=18, anchor="e").pack(side="left", padx=5)
    tk.Entry(linha, textvariable=var_acomp, width=32).pack(side="left")

def limpar_acompanhantes():
    for widget in frame_acompanhantes.winfo_children():
        widget.destroy()
    lista_vars_acompanhantes.clear()

# --- IMPORTAR PDF ---
def importar_pdf():
    caminho_arquivo = filedialog.askopenfilename(title="Selecione o PDF", filetypes=[("Arquivos PDF", "*.pdf")])
    if not caminho_arquivo: return

    try:
        with open(caminho_arquivo, "rb") as arquivo:
            leitor = PyPDF2.PdfReader(arquivo)
            texto_completo = ""
            for pagina in leitor.pages:
                texto_completo += pagina.extract_text() + "\n"

        matches_nomes = re.findall(r"Nome do Solicitante\s+([^\n\r]+)", texto_completo)
        if matches_nomes:
            nomes_limpos = [nome.strip() for nome in matches_nomes]
            nomes_unicos = list(dict.fromkeys(nomes_limpos))
            var_cliente.set(nomes_unicos[0])
            limpar_acompanhantes()
            if len(nomes_unicos) > 1:
                for nome in nomes_unicos[1:]:
                    adicionar_campo_acompanhante(nome)

        meses = {"Janeiro": "01", "Fevereiro": "02", "Março": "03", "Abril": "04", "Maio": "05", "Junho": "06",
                 "Julho": "07", "Agosto": "08", "Setembro": "09", "Outubro": "10", "Novembro": "11", "Dezembro": "12"}

        match_casv = re.search(r"Data do Agendamento no CASV:\s*(\d{1,2})\s+([A-Za-zç]+),\s+(\d{4}),\s+(\d{2}:\d{2})\s+([A-Za-z\s]+?)\s+Horário", texto_completo)
        if match_casv:
            dia, mes_nome, ano, hora, local_bruto = match_casv.groups()
            mes = meses.get(mes_nome, "01")
            entry_data_casv.delete(0, tk.END)
            entry_data_casv.insert(0, f"{int(dia):02d}/{mes}/{ano}")
            entry_hora_casv.delete(0, tk.END)
            entry_hora_casv.insert(0, hora)

            local_upper = local_bruto.upper()
            for loc in locais_permitidos:
                if loc in local_upper or local_upper in loc:
                    var_local.set(loc)
                    break

        match_entrevista = re.search(r"Data da entrevista no Consulado:\s*(\d{1,2})\s+([A-Za-zç]+),\s+(\d{4}),\s+(\d{2}:\d{2})", texto_completo)
        if match_entrevista:
            dia, mes_nome, ano, hora = match_entrevista.groups()
            mes = meses.get(mes_nome, "01")
            entry_data_entrevista.delete(0, tk.END)
            entry_data_entrevista.insert(0, f"{int(dia):02d}/{mes}/{ano}")
            entry_hora_entrevista.delete(0, tk.END)
            entry_hora_entrevista.insert(0, hora)

        messagebox.showinfo("Sucesso", "Dados extraídos do PDF com sucesso!")
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao ler PDF: {e}")

# --- SALVAR COMPROMISSOS (COM cliente_id) ---
def salvar():
    cliente_principal = var_cliente.get().strip()
    local = var_local.get().strip()

    if not cliente_principal or not local:
        messagebox.showwarning("Aviso", "Preencha o Cliente Principal e o Local Padrão!")
        return

    nomes_acomp = [var.get().strip() for var in lista_vars_acompanhantes if var.get().strip()]
    if nomes_acomp:
        cliente_final = f"{cliente_principal} (+ {', '.join(nomes_acomp)})"
    else:
        cliente_final = cliente_principal

    etapas = []
    if entry_data_casv.get() and entry_hora_casv.get():
        etapas.append(("CASV", entry_data_casv.get(), entry_hora_casv.get()))
    if entry_data_entrevista.get() and entry_hora_entrevista.get():
        etapas.append(("ENTREVISTA", entry_data_entrevista.get(), entry_hora_entrevista.get()))
    if entry_data_treinamento.get() and entry_hora_treinamento.get():
        modalidade = f"TREINAMENTO - {var_modalidade.get()}"
        etapas.append((modalidade, entry_data_treinamento.get(), entry_hora_treinamento.get()))
    if entry_data_retirada.get() and entry_hora_retirada.get():
        etapas.append(("RETIRADA DO PASSAPORTE", entry_data_retirada.get(), entry_hora_retirada.get()))

    if not etapas:
        messagebox.showwarning("Aviso", "Preencha pelo menos uma etapa (Data e Hora)!")
        return

    # Buscar o cliente_id do cliente principal (para associar a todos os compromissos do grupo)
    cliente_id = buscar_cliente_id(cliente_principal)

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        for atividade, data, hora in etapas:
            data_banco = datetime.strptime(data, "%d/%m/%Y").strftime("%Y-%m-%d")
            cursor.execute(
                "INSERT INTO compromissos (cliente, atividade, data, hora, local, concluido, cliente_id) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (cliente_final, atividade, data_banco, hora, local, 0, cliente_id)
            )
        conn.commit()
        conn.close()

        # Limpar campos
        var_cliente.set("")
        limpar_acompanhantes()
        var_local.set("")
        entry_data_casv.delete(0, tk.END)
        entry_hora_casv.delete(0, tk.END)
        entry_data_entrevista.delete(0, tk.END)
        entry_hora_entrevista.delete(0, tk.END)
        entry_data_treinamento.delete(0, tk.END)
        entry_hora_treinamento.delete(0, tk.END)
        entry_data_retirada.delete(0, tk.END)
        entry_hora_retirada.delete(0, tk.END)

        msg = "Compromissos salvos com sucesso!"
        if cliente_id is None:
            msg += "\n\n⚠️ Atenção: Não foi possível vincular este compromisso a um cliente existente.\nOs avisos por e-mail/WhatsApp não serão enviados até que o cliente seja cadastrado na tabela 'clientes'."
        else:
            msg += "\n\n✅ Cliente vinculado. Notificações automáticas serão enviadas."
        messagebox.showinfo("Sucesso", msg)
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao salvar na nuvem: {e}")

# --- RELATÓRIO GERAL (inalterado, mas funciona com a nova coluna) ---
def ver_agenda():
    janela_agenda = tk.Toplevel(janela)
    janela_agenda.title("Relatório Geral (Nuvem)")
    janela_agenda.geometry("900x400")

    colunas = ("ID", "Cliente", "Atividade", "Data", "Hora", "Local", "Status")
    tree = ttk.Treeview(janela_agenda, columns=colunas, show="headings")

    tree.heading("ID", text="ID")
    tree.heading("Cliente", text="Cliente")
    tree.heading("Atividade", text="Atividade")
    tree.heading("Data", text="Data")
    tree.heading("Hora", text="Hora")
    tree.heading("Local", text="Local")
    tree.heading("Status", text="Status")

    tree.column("ID", width=30, anchor="center")
    tree.column("Cliente", width=250)
    tree.column("Atividade", width=180)
    tree.column("Data", width=90, anchor="center")
    tree.column("Hora", width=60, anchor="center")
    tree.column("Local", width=120, anchor="center")
    tree.column("Status", width=100, anchor="center")

    tree.tag_configure('concluido', background='#d4edda')
    tree.tag_configure('grupo1', background='#ffffff')
    tree.tag_configure('grupo2', background='#e6f2ff')
    tree.tag_configure('separador', background='#f0f0f0', foreground='#a0a0a0')

    tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def carregar_dados():
        for item in tree.get_children():
            tree.delete(item)
        try:
            conn = psycopg2.connect(DATABASE_URL)
            cursor = conn.cursor()
            cursor.execute("SELECT id, cliente, atividade, data, hora, local, concluido FROM compromissos ORDER BY cliente ASC, data ASC, hora ASC")
            linhas = cursor.fetchall()
            conn.close()

            cliente_atual = ""
            cor_fundo = "grupo1"

            for row in linhas:
                if cliente_atual != "" and row[1] != cliente_atual:
                    tree.insert("", tk.END, values=("", "-"*20, "-"*15, "-"*10, "-"*10, "-"*15, ""), tags=('separador',))
                    cor_fundo = "grupo2" if cor_fundo == "grupo1" else "grupo1"

                cliente_atual = row[1]
                status = "✅ CONCLUÍDO" if row[6] == 1 else "⏳ PENDENTE"
                tag = 'concluido' if row[6] == 1 else cor_fundo

                data_banco = row[3]
                try:
                    if "-" in data_banco:
                        data_formatada = datetime.strptime(data_banco, "%Y-%m-%d").strftime("%d/%m/%Y")
                    else:
                        data_formatada = data_banco 
                except:
                    data_formatada = data_banco

                tree.insert("", tk.END, values=(row[0], row[1], row[2], data_formatada, row[4], row[5], status), tags=(tag,))
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar dados: {e}")

    carregar_dados()

    def concluir_selecionado():
        selecionado = tree.selection()
        if not selecionado: return
        valores = tree.item(selecionado[0], "values")
        if valores[0] == "": return 

        id_comp = valores[0]
        if messagebox.askyesno("Confirmar", "Marcar como CONCLUÍDO?"):
            try:
                conn = psycopg2.connect(DATABASE_URL)
                cursor = conn.cursor()
                cursor.execute("UPDATE compromissos SET concluido = 1 WHERE id = %s", (id_comp,))
                conn.commit()
                conn.close()
                carregar_dados()
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao atualizar: {e}")

    def deletar_selecionado():
        selecionado = tree.selection()
        if not selecionado: return
        valores = tree.item(selecionado[0], "values")
        if valores[0] == "": return 

        id_comp = valores[0]
        if messagebox.askyesno("Confirmar", "Tem certeza que deseja excluir este compromisso?"):
            try:
                conn = psycopg2.connect(DATABASE_URL)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM compromissos WHERE id = %s", (id_comp,))
                conn.commit()
                conn.close()
                carregar_dados()
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao excluir: {e}")

    def editar_selecionado():
        selecionado = tree.selection()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione um registro na lista para editar.")
            return

        valores = tree.item(selecionado[0], "values")
        if valores[0] == "": return

        id_comp = valores[0]
        cliente_atual = valores[1]
        atividade_atual = valores[2]
        data_atual = valores[3]
        hora_atual = valores[4]
        local_atual = valores[5]

        janela_edit = tk.Toplevel(janela_agenda)
        janela_edit.title("Editar Compromisso")
        janela_edit.geometry("350x250")
        janela_edit.grab_set()

        tk.Label(janela_edit, text=f"{cliente_atual}", font=("Arial", 10, "bold")).pack(pady=5)
        tk.Label(janela_edit, text=f"{atividade_atual}", fg="blue").pack()

        frame_form = tk.Frame(janela_edit)
        frame_form.pack(pady=15)

        tk.Label(frame_form, text="Data:").grid(row=0, column=0, sticky="e", pady=5)
        entry_data = tk.Entry(frame_form, width=15)
        entry_data.insert(0, data_atual)
        entry_data.grid(row=0, column=1, pady=5, padx=5)
        entry_data.bind('<KeyRelease>', lambda e: mascara_data(e, entry_data))

        tk.Label(frame_form, text="Hora:").grid(row=1, column=0, sticky="e", pady=5)
        entry_hora = tk.Entry(frame_form, width=15)
        entry_hora.insert(0, hora_atual)
        entry_hora.grid(row=1, column=1, pady=5, padx=5)
        entry_hora.bind('<KeyRelease>', lambda e: mascara_hora(e, entry_hora))

        tk.Label(frame_form, text="Local:").grid(row=2, column=0, sticky="e", pady=5)
        entry_local = ttk.Combobox(frame_form, values=["BRASILIA", "RIO DE JANEIRO", "SAO PAULO", "RECIFE", "PORTO ALEGRE"], width=13)
        entry_local.insert(0, local_atual)
        entry_local.grid(row=2, column=1, pady=5, padx=5)

        def salvar_edicao():
            nova_data = entry_data.get()
            nova_hora = entry_hora.get()
            novo_local = entry_local.get().upper()

            try:
                data_banco = datetime.strptime(nova_data, "%d/%m/%Y").strftime("%Y-%m-%d")
                conn = psycopg2.connect(DATABASE_URL)
                cursor = conn.cursor()
                cursor.execute("UPDATE compromissos SET data = %s, hora = %s, local = %s WHERE id = %s", 
                               (data_banco, nova_hora, novo_local, id_comp))
                conn.commit()
                conn.close()
                janela_edit.destroy()
                carregar_dados()
            except Exception as e:
                messagebox.showerror("Erro", "Verifique se a data está no formato correto (DD/MM/AAAA).")

        tk.Button(janela_edit, text="💾 Salvar Alterações", command=salvar_edicao, bg="#4CAF50", fg="black").pack(pady=10)

    frame_botoes = tk.Frame(janela_agenda)
    frame_botoes.pack(pady=10)

    tk.Button(frame_botoes, text="✅ Dar Baixa", command=concluir_selecionado, fg="green", font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=10)
    tk.Button(frame_botoes, text="✏️ Editar", command=editar_selecionado, fg="blue", font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=10)
    tk.Button(frame_botoes, text="❌ Excluir", command=deletar_selecionado, fg="red", font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=10)

# =========================
# INICIAR SISTEMA
# =========================
criar_banco()

janela = tk.Tk()
janela.title("Sistema de Vistos - Agência (Conectado na Nuvem ☁️)")
janela.minsize(550, 600)

tk.Button(janela, text="📄 Importar PDF do Consulado", command=importar_pdf, bg="#2196F3", fg="black", font=("Arial", 11, "bold")).pack(pady=10)

frame_topo = tk.Frame(janela)
frame_topo.pack(pady=5, fill="x", padx=20)

frame_cli = tk.Frame(frame_topo)
frame_cli.pack(fill="x", pady=2)
tk.Label(frame_cli, text="Cliente Principal:", width=18, anchor="e").pack(side="left", padx=5)
var_cliente = tk.StringVar()
var_cliente.trace_add("write", lambda *args: forcar_maiusculo_var(var_cliente))
tk.Entry(frame_cli, textvariable=var_cliente, width=32).pack(side="left")

frame_acompanhantes = tk.Frame(frame_topo)
frame_acompanhantes.pack(fill="x")

tk.Button(frame_topo, text="➕ Adicionar Acompanhante", command=adicionar_campo_acompanhante, fg="#2196F3", relief="flat", cursor="hand2").pack(anchor="w", padx=140, pady=2)

frame_loc = tk.Frame(frame_topo)
frame_loc.pack(fill="x", pady=10)
tk.Label(frame_loc, text="Local Padrão:", width=18, anchor="e").pack(side="left", padx=5)
var_local = tk.StringVar()
locais_permitidos = ["BRASILIA", "RIO DE JANEIRO", "SAO PAULO", "RECIFE", "PORTO ALEGRE"]
entry_local = ttk.Combobox(frame_loc, textvariable=var_local, values=locais_permitidos, width=30)
entry_local.pack(side="left")
entry_local.bind('<KeyRelease>', autocompletar_local)

frame_etapas = tk.LabelFrame(janela, text=" Datas das Etapas (Preencha as que tiver) ")
frame_etapas.pack(pady=10, padx=20, fill="both", expand=True)

tk.Label(frame_etapas, text="Data (Apenas Números)").grid(row=0, column=1, pady=5)
tk.Label(frame_etapas, text="Hora").grid(row=0, column=2, pady=5)

tk.Label(frame_etapas, text="CASV:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
entry_data_casv = tk.Entry(frame_etapas, width=12)
entry_data_casv.grid(row=1, column=1, padx=5, pady=5)
entry_data_casv.bind('<KeyRelease>', lambda e: mascara_data(e, entry_data_casv))
entry_hora_casv = tk.Entry(frame_etapas, width=8)
entry_hora_casv.grid(row=1, column=2, padx=5, pady=5)
entry_hora_casv.bind('<KeyRelease>', lambda e: mascara_hora(e, entry_hora_casv))

tk.Label(frame_etapas, text="ENTREVISTA:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
entry_data_entrevista = tk.Entry(frame_etapas, width=12)
entry_data_entrevista.grid(row=2, column=1, padx=5, pady=5)
entry_data_entrevista.bind('<KeyRelease>', lambda e: mascara_data(e, entry_data_entrevista))
entry_hora_entrevista = tk.Entry(frame_etapas, width=8)
entry_hora_entrevista.grid(row=2, column=2, padx=5, pady=5)
entry_hora_entrevista.bind('<KeyRelease>', lambda e: mascara_hora(e, entry_hora_entrevista))

tk.Label(frame_etapas, text="TREINAMENTO:").grid(row=3, column=0, sticky="e", padx=5, pady=5)
entry_data_treinamento = tk.Entry(frame_etapas, width=12)
entry_data_treinamento.grid(row=3, column=1, padx=5, pady=5)
entry_data_treinamento.bind('<KeyRelease>', lambda e: mascara_data(e, entry_data_treinamento))
entry_hora_treinamento = tk.Entry(frame_etapas, width=8)
entry_hora_treinamento.grid(row=3, column=2, padx=5, pady=5)
entry_hora_treinamento.bind('<KeyRelease>', lambda e: mascara_hora(e, entry_hora_treinamento))
var_modalidade = tk.StringVar(value="ONLINE")
ttk.Combobox(frame_etapas, textvariable=var_modalidade, values=["ONLINE", "PRESENCIAL"], width=12, state="readonly").grid(row=3, column=3, padx=5, pady=5)

tk.Label(frame_etapas, text="RETIRADA PASSAPORTE:").grid(row=4, column=0, sticky="e", padx=5, pady=5)
entry_data_retirada = tk.Entry(frame_etapas, width=12)
entry_data_retirada.grid(row=4, column=1, padx=5, pady=5)
entry_data_retirada.bind('<KeyRelease>', lambda e: mascara_data(e, entry_data_retirada))
entry_hora_retirada = tk.Entry(frame_etapas, width=8)
entry_hora_retirada.grid(row=4, column=2, padx=5, pady=5)
entry_hora_retirada.bind('<KeyRelease>', lambda e: mascara_hora(e, entry_hora_retirada))

tk.Button(janela, text="Salvar Compromissos", command=salvar, bg="#4CAF50", fg="black").pack(pady=10)
tk.Button(janela, text="Ver Relatório Geral", command=ver_agenda).pack()

janela.mainloop()
