import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time

# =====================================================================
# 1. BANCO DE DADOS
# =====================================================================
def inicializar_banco():
    conn = sqlite3.connect('doceria.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_barras TEXT UNIQUE,
            nome TEXT NOT NULL,
            preco REAL NOT NULL,
            estoque INTEGER NOT NULL DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cpf TEXT UNIQUE,
            telefone TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS funcionarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            cargo TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora TEXT NOT NULL,
            total REAL NOT NULL,
            funcionario_usuario TEXT NOT NULL
        )
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM produtos")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO produtos (codigo_barras, nome, preco, estoque) VALUES (?, ?, ?, ?)", [
            ('7891000101', 'Brigadeiro Gourmet', 4.50, 100),
            ('7891000102', 'Bolo de Pote Ninho', 12.00, 30),
            ('7891000103', 'Palha Italiana', 6.00, 50)
        ])
        cursor.executemany("INSERT INTO funcionarios (usuario, senha, cargo) VALUES (?, ?, ?)", [
            ('admin', 'admin123', 'Gerente'),
            ('caixa1', '1234', 'Operador')
        ])
        
    conn.commit()
    conn.close()

# =====================================================================
# 2. TELA DE LOGIN
# =====================================================================
class TelaLogin(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Acesso ao Sistema")
        self.geometry("350x250")
        self.configure(bg="#FDF6F6")
        self.resizable(False, False)
        
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.ao_fechar)
        
        tk.Label(self, text="🧁 LOGIN DE ACESSO", font=("Helvetica", 14, "bold"), bg="#FDF6F6", fg="#5D4037").pack(pady=15)
        
        tk.Label(self, text="Usuário:", bg="#FDF6F6", font=("Helvetica", 10)).pack(anchor="w", padx=40)
        self.ent_user = tk.Entry(self, font=("Helvetica", 11), width=25)
        self.ent_user.pack(pady=2)
        self.ent_user.insert(0, "caixa1")
        
        tk.Label(self, text="Senha:", bg="#FDF6F6", font=("Helvetica", 10)).pack(anchor="w", padx=40)
        self.ent_senha = tk.Entry(self, font=("Helvetica", 11), width=25, show="*")
        self.ent_senha.pack(pady=2)
        self.ent_senha.insert(0, "1234")
        
        btn_entrar = tk.Button(self, text="Entrar no Sistema", bg="#C79292", fg="white", font=("Helvetica", 11, "bold"), relief="flat", width=20, command=self.autenticar)
        btn_entrar.pack(pady=15)
        
    def autenticar(self):
        usuario = self.ent_user.get().strip()
        senha = self.ent_senha.get().strip()
        
        conn = sqlite3.connect('doceria.db')
        cursor = conn.cursor()
        cursor.execute("SELECT cargo FROM funcionarios WHERE usuario = ? AND senha = ?", (usuario, senha))
        resultado = cursor.fetchone()
        conn.close()
        
        if resultado:
            cargo = resultado[0]
            self.parent.definir_usuario_ativo(usuario, cargo)
            self.destroy()
        else:
            messagebox.showerror("Acesso Negado", "Usuário ou senha incorretos!")

    def ao_fechar(self):
        self.parent.destroy()

# =====================================================================
# 3. INTERFACE PRINCIPAL
# =====================================================================
class SistemaDoceria(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CandySystem Pro v1.2 - Frente de Caixa e Gestão")
        self.geometry("1100x680")
        self.configure(bg="#FDF6F6")
        
        self.carrinho = []
        self.usuario_atual = None
        self.cargo_atual = None
        
        self.configurar_estilos()
        self.criar_widgets()
        
        self.withdraw()
        self.after(100, self.mostrar_login)

    def mostrar_login(self):
        TelaLogin(self)

    def definir_usuario_ativo(self, usuario, cargo):
        self.usuario_atual = usuario
        self.cargo_atual = cargo
        self.deiconify()
        self.lbl_usuario_logado.config(text=f"👤 Operador: {self.usuario_atual.upper()} ({self.cargo_atual})")
        self.atualizar_visualizacao_estoque()
        self.atualizar_visualizacao_clientes()

    def configurar_estilos(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background="#FDF6F6", tabposition="nw")
        style.configure("TNotebook.Tab", background="#E8D3D3", foreground="#5D4037", font=("Helvetica", 10, "bold"), padding=6)
        style.map("TNotebook.Tab", background=[("selected", "#C79292")], foreground=[("selected", "white")])
        style.configure("Treeview", font=("Helvetica", 11), rowheight=25, background="white")
        style.configure("Treeview.Heading", font=("Helvetica", 11, "bold"), background="#C79292", foreground="white")
        
    def criar_widgets(self):
        barra_status = tk.Frame(self, bg="#E8D3D3", height=30)
        barra_status.pack(fill="x", side="top")
        self.lbl_usuario_logado = tk.Label(barra_status, text="👤 Operador: Nenhum", font=("Helvetica", 10, "bold"), bg="#E8D3D3", fg="#5D4037")
        self.lbl_usuario_logado.pack(side="left", padx=15, pady=5)

        self.abas = ttk.Notebook(self)
        self.abas.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.aba_caixa = ttk.Frame(self.abas)
        self.aba_adm = ttk.Frame(self.abas)
        
        self.abas.add(self.aba_caixa, text=" 🛒 Frente de Caixa (PDV) ")
        self.abas.add(self.aba_adm, text=" 📊 Painel Administrativo / Almoxarifado ")
        
        self.montar_aba_caixa()
        self.montar_aba_adm()
        
        self.abas.bind("<<NotebookTabChanged>>", self.verificar_permissao_aba)

    def verificar_permissao_aba(self, event):
        aba_selecionada = self.abas.index(self.abas.select())
        if aba_selecionada == 1 and self.cargo_atual != "Gerente":
            self.abas.select(0)
            messagebox.showwarning("Acesso Restrito", "Apenas funcionários com cargo de 'Gerente' possuem acesso!")

    def montar_aba_caixa(self):
        painel_esquerdo = tk.Frame(self.aba_caixa, bg="#FDF6F6", width=400)
        painel_esquerdo.pack(side="left", fill="y", padx=10, pady=10)
        
        tk.Label(painel_esquerdo, text="ENTRADA DE PRODUTO", font=("Helvetica", 12, "bold"), bg="#FDF6F6", fg="#5D4037").pack(anchor="w", pady=5)
        
        tk.Label(painel_esquerdo, text="Código, QR Code ou Digitação Manual:", bg="#FDF6F6", fg="#7D5A50").pack(anchor="w")
        self.txt_codigo = tk.Entry(painel_esquerdo, font=("Helvetica", 14), width=25)
        self.txt_codigo.pack(fill="x", pady=5)
        self.txt_codigo.bind("<Return>", self.adicionar_por_codigo)
        
        self.btn_voz = tk.Button(painel_esquerdo, text="🎙️ Ativar Comando de Voz", font=("Helvetica", 11, "bold"), bg="#E1BEE7", fg="#4A148C", relief="flat", command=self.escutar_comando_voz)
        self.btn_voz.pack(fill="x", pady=15)
        
        tk.Label(painel_esquerdo, text="TOTAL DO PEDIDO:", font=("Helvetica", 12, "bold"), bg="#FDF6F6", fg="#5D4037").pack(anchor="w", pady=20)
        self.lbl_total = tk.Label(painel_esquerdo, text="R$ 0,00", font=("Helvetica", 28, "bold"), bg="#FDF6F6", fg="#D32F2F")
        self.lbl_total.pack(anchor="w")
        
        btn_finalizar = tk.Button(painel_esquerdo, text="💸 Finalizar Venda", font=("Helvetica", 14, "bold"), bg="#4CAF50", fg="white", relief="flat", command=self.finalizar_venda)
        btn_finalizar.pack(fill="x", side="bottom", pady=10)
        
        painel_direito = tk.Frame(self.aba_caixa)
        painel_direito.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        self.tab_carrinho = ttk.Treeview(painel_direito, columns=("Cod", "Prod", "Preco", "Qtd", "Total"), show="headings")
        self.tab_carrinho.heading("Cod", text="Código")
        self.tab_carrinho.heading("Prod", text="Produto")
        self.tab_carrinho.heading("Preco", text="Preço Unit.")
        self.tab_carrinho.heading("Qtd", text="Qtd")
        self.tab_carrinho.heading("Total", text="Total")
        self.tab_carrinho.column("Prod", width=250)
        self.tab_carrinho.pack(fill="both", expand=True)

    def montar_aba_adm(self):
        abas_adm = ttk.Notebook(self.aba_adm)
        abas_adm.pack(fill="both", expand=True)
        
        self.aba_estoque = ttk.Frame(abas_adm)
        self.aba_clientes = ttk.Frame(abas_adm)
        
        abas_adm.add(self.aba_estoque, text="📦 Almoxarifado / Estoque")
        abas_adm.add(self.aba_clientes, text="👥 Cadastro de Clientes")
        
        self.montar_aba_estoque()
        self.montar_aba_clientes()
        
    def montar_aba_estoque(self):
        self.tab_estoque = ttk.Treeview(self.aba_estoque, columns=("ID", "Cod", "Nome", "Preco", "Estoque"), show="headings")
        self.tab_estoque.heading("ID", text="ID")
        self.tab_estoque.heading("Cod", text="Cód. Barras / QR")
        self.tab_estoque.heading("Nome", text="Nome do Doce")
        self.tab_estoque.heading("Preco", text="Preço de Venda")
        self.tab_estoque.heading("Estoque", text="Qtd em Estoque")
        self.tab_estoque.column("ID", width=50, anchor="center")
        self.tab_estoque.pack(fill="both", expand=True, padx=10, pady=5)
        
        frame_botoes = tk.Frame(self.aba_estoque, bg="#FDF6F6")
        frame_botoes.pack(fill="x", padx=10, pady=5)
        
        btn_editar = tk.Button(frame_botoes, text="✏️ Editar Produto", bg="#FFB74D", fg="black", font=("Helvetica", 10, "bold"), relief="flat", command=self.abrir_janela_edicao, width=15)
        btn_editar.pack(side="left", padx=5, pady=5)
        
        btn_excluir = tk.Button(frame_botoes, text="❌ Excluir Doce", bg="#E57373", fg="white", font=("Helvetica", 10, "bold"), relief="flat", command=self.excluir_produto_estoque, width=15)
        btn_excluir.pack(side="left", padx=5, pady=5)
        
        frame_acoes = tk.LabelFrame(frame_botoes, text=" Entrada de Mercadoria ", font=("Helvetica", 9, "bold"), padx=5, pady=5, bg="#FDF6F6")
        frame_acoes.pack(side="right", padx=5, pady=5)
        
        tk.Label(frame_acoes, text="Cód. Barras:", bg="#FDF6F6").grid(row=0, column=0, padx=2)
        self.ent_est_cod = tk.Entry(frame_acoes, width=15)
        self.ent_est_cod.grid(row=0, column=1, padx=2)
        
        tk.Label(frame_acoes, text="Qtd:", bg="#FDF6F6").grid(row=0, column=2, padx=2)
        self.ent_est_qtd = tk.Entry(frame_acoes, width=5)
        self.ent_est_qtd.grid(row=0, column=3, padx=2)
        
        btn_atualizar = tk.Button(frame_acoes, text="📥 Adicionar", bg="#C79292", fg="white", font=("Helvetica", 9, "bold"), relief="flat", command=self.registrar_entrada_estoque)
        btn_atualizar.grid(row=0, column=4, padx=5)

    def montar_aba_clientes(self):
        frame_cad_cli = tk.LabelFrame(self.aba_clientes, text=" Novo Cliente ", font=("Helvetica", 10, "bold"), padx=10, pady=10, bg="#FDF6F6")
        frame_cad_cli.pack(fill="x", padx=10, pady=10)
        
        tk.Label(frame_cad_cli, text="Nome:", bg="#FDF6F6").grid(row=0, column=0, padx=5, sticky="w")
        self.ent_cli_nome = tk.Entry(frame_cad_cli, width=30)
        self.ent_cli_nome.grid(row=0, column=1, padx=5, pady=2)
        
        tk.Label(frame_cad_cli, text="CPF:", bg="#FDF6F6").grid(row=0, column=2, padx=5, sticky="w")
        self.ent_cli_cpf = tk.Entry(frame_cad_cli, width=20)
        self.ent_cli_cpf.grid(row=0, column=3, padx=5, pady=2)
        
        tk.Label(frame_cad_cli, text="Telefone:", bg="#FDF6F6").grid(row=0, column=4, padx=5, sticky="w")
        self.ent_cli_tel = tk.Entry(frame_cad_cli, width=20)
        self.ent_cli_tel.grid(row=0, column=5, padx=5, pady=2)
        
        btn_salvar_cli = tk.Button(frame_cad_cli, text="💾 Salvar Cliente", bg="#4CAF50", fg="white", font=("Helvetica", 9, "bold"), relief="flat", command=self.salvar_cliente)
        btn_salvar_cli.grid(row=0, column=6, padx=15)
        
        self.tab_clientes = ttk.Treeview(self.aba_clientes, columns=("ID", "Nome", "CPF", "Telefone"), show="headings")
        self.tab_clientes.heading("ID", text="ID")
        self.tab_clientes.heading("Nome", text="Nome Completo")
        self.tab_clientes.heading("CPF", text="CPF")
        self.tab_clientes.heading("Telefone", text="Telefone")
        self.tab_clientes.column("ID", width=60, anchor="center")
        self.tab_clientes.pack(fill="both", expand=True, padx=10, pady=5)
    def adicionar_por_codigo(self, event=None):
        codigo = self.txt_codigo.get().strip()
        if not codigo: return
        
        conn = sqlite3.connect('doceria.db')
        cursor = conn.cursor()
        cursor.execute("SELECT codigo_barras, nome, preco, estoque FROM produtos WHERE codigo_barras = ?", (codigo,))
        produto = cursor.fetchone()
        conn.close()
        
        if produto:
            cod, nome, preco, estoque = produto
            if estoque <= 0:
                messagebox.showwarning("Estoque Esgotado", f"O produto '{nome}' está sem estoque disponível!")
                return
                
            self.carrinho.append({'codigo': cod, 'nome': nome, 'preco': preco, 'qtd': 1})
            self.atualizar_grade_carrinho()
            self.txt_codigo.delete(0, tk.END)
        else:
            messagebox.showerror("Não Encontrado", "Código de barras ou QR Code não cadastrado.")
            
    def atualizar_grade_carrinho(self):
        for i in self.tab_carrinho.get_children():
            self.tab_carrinho.delete(i)
            
        total_geral = 0.0
        for item in self.carrinho:
            total_item = item['preco'] * item['qtd']
            total_geral += total_item
            self.tab_carrinho.insert("", "end", values=(item['codigo'], item['nome'], f"R$ {item['preco']:.2f}", item['qtd'], f"R$ {total_item:.2f}"))
            
        self.lbl_total.config(text=f"R$ {total_geral:.2f}")

    def finalizar_venda(self):
        if not self.carrinho:
            messagebox.showwarning("Carrinho Vazio", "Adicione produtos antes de finalizar.")
            return
            
        conn = sqlite3.connect('doceria.db')
        cursor = conn.cursor()
        
        try:
            total_venda = 0.0
            for item in self.carrinho:
                total_venda += item['preco'] * item['qtd']
                cursor.execute("UPDATE produtos SET estoque = estoque - ? WHERE codigo_barras = ?", (item['qtd'], item['codigo']))
            
            data_atual = time.strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("INSERT INTO vendas (data_hora, total, funcionario_usuario) VALUES (?, ?, ?)", 
                           (data_atual, total_venda, self.usuario_atual))
            
            conn.commit()
            messagebox.showinfo("Sucesso", f"Venda gravada por {self.usuario_atual.upper()}!\nEstoque updated.")
            self.carrinho = []
            self.atualizar_grade_carrinho()
            self.atualizar_visualizacao_estoque()
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Erro", f"Falha ao processar venda: {e}")
        finally:
            conn.close()

    def registrar_entrada_estoque(self):
        cod = self.ent_est_cod.get().strip()
        qtd_str = self.ent_est_qtd.get().strip()
        
        if not cod or not qtd_str.isdigit():
            messagebox.showwarning("Dados Inválidos", "Preencha o código e uma quantidade válida.")
            return
            
        conn = sqlite3.connect('doceria.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE produtos SET estoque = estoque + ? WHERE codigo_barras = ?", (int(qtd_str), cod))
        if cursor.rowcount > 0:
            conn.commit()
            messagebox.showinfo("Sucesso", "Entrada de mercadoria registrada no almoxarifado.")
            self.atualizar_visualizacao_estoque()
            self.ent_est_cod.delete(0, tk.END)
            self.ent_est_qtd.delete(0, tk.END)
        else:
            messagebox.showerror("Erro", "Produto não encontrado para dar entrada.")
        conn.close()

    def salvar_cliente(self):
        nome = self.ent_cli_nome.get().strip()
        cpf = self.ent_cli_cpf.get().strip()
        tel = self.ent_cli_tel.get().strip()
        
        if not nome:
            messagebox.showwarning("Erro", "O campo Nome é obrigatório.")
            return
            
        conn = sqlite3.connect('doceria.db')
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO clientes (nome, cpf, telefone) VALUES (?, ?, ?)", (nome, cpf, tel))
            conn.commit()
            messagebox.showinfo("Sucesso", "Cliente cadastrado com sucesso!")
            self.ent_cli_nome.delete(0, tk.END)
            self.ent_cli_cpf.delete(0, tk.END)
            self.ent_cli_tel.delete(0, tk.END)
            self.atualizar_visualizacao_clientes()
        except sqlite3.IntegrityError:
            messagebox.showerror("Erro", "Este CPF já está cadastrado para outro cliente.")
        finally:
            conn.close()
    def atualizar_visualizacao_estoque(self):
        for i in self.tab_estoque.get_children():
            self.tab_estoque.delete(i)
        conn = sqlite3.connect('doceria.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, codigo_barras, nome, preco, estoque FROM produtos")
        for linha in cursor.fetchall():
            self.tab_estoque.insert("", "end", values=(linha[0], linha[1], linha[2], f"R$ {linha[3]:.2f}", linha[4]))
        conn.close()

    def atualizar_visualizacao_clientes(self):
        for i in self.tab_clientes.get_children():
            self.tab_clientes.delete(i)
        conn = sqlite3.connect('doceria.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, cpf, telefone FROM clientes")
        for linha in cursor.fetchall():
            self.tab_clientes.insert("", "end", values=linha)
        conn.close()

    def abrir_janela_edicao(self):
        selecionado = self.tab_estoque.selection()
        if not selecionado:
            messagebox.showwarning("Seleção Necessária", "Selecione um doce na tabela acima para editar.")
            return
            
        valores = self.tab_estoque.item(selecionado, 'values')
        prod_id = valores[0]
        cod_atual = valores[1]
        nome_atual = valores[2]
        preco_atual = valores[3].replace("R$ ", "")
        
        janela_edit = tk.Toplevel(self)
        janela_edit.title("Editar Dados")
        janela_edit.geometry("350x250")
        janela_edit.configure(bg="#FDF6F6")
        janela_edit.transient(self)
        janela_edit.grab_set()
        
        tk.Label(janela_edit, text="Nome do Produto:", bg="#FDF6F6").pack(pady=5)
        ent_nome = tk.Entry(janela_edit, font=("Helvetica", 11), width=28)
        ent_nome.insert(0, nome_atual)
        ent_nome.pack()
        
        tk.Label(janela_edit, text="Preço de Venda (R$):", bg="#FDF6F6").pack(pady=5)
        ent_preco = tk.Entry(janela_edit, font=("Helvetica", 11), width=28)
        ent_preco.insert(0, preco_atual)
        ent_preco.pack()
        
        tk.Label(janela_edit, text="Código de Barras / QR:", bg="#FDF6F6").pack(pady=5)
        ent_cod = tk.Entry(janela_edit, font=("Helvetica", 11), width=28)
        ent_cod.insert(0, cod_atual)
        ent_cod.pack()
        
        def salvar_alteracoes():
            novo_nome = ent_nome.get().strip()
            novo_preco_str = ent_preco.get().strip()
            novo_cod = ent_cod.get().strip()
            
            try:
                novo_preco = float(novo_preco_str)
            except ValueError:
                messagebox.showerror("Erro", "Preço inválido.", parent=janela_edit)
                return
                
            conn = sqlite3.connect('doceria.db')
            cursor = conn.cursor()
            try:
                cursor.execute("UPDATE produtos SET nome = ?, preco = ?, codigo_barras = ? WHERE id = ?", 
                               (novo_nome, novo_preco, novo_cod, prod_id))
                conn.commit()
                janela_edit.destroy()
                self.atualizar_visualizacao_estoque()
            except sqlite3.IntegrityError:
                messagebox.showerror("Erro", "Código em uso.", parent=janela_edit)
            finally:
                conn.close()
                
        tk.Button(janela_edit, text="💾 Salvar", bg="#4CAF50", fg="white", command=salvar_alteracoes).pack(pady=15)

    def excluir_produto_estoque(self):
        selecionado = self.tab_estoque.selection()
        if not selecionado:
            messagebox.showwarning("Seleção Necessária", "Selecione para excluir.")
            return
            
        valores = self.tab_estoque.item(selecionado, 'values')
        prod_id = valores[0]
        
        if messagebox.askyesno("Confirmar", f"Excluir item ID {prod_id}?"):
            conn = sqlite3.connect('doceria.db')
            cursor = conn.cursor()
            cursor.execute("DELETE FROM produtos WHERE id = ?", (prod_id,))
            conn.commit()
            conn.close()
            self.atualizar_visualizacao_estoque()

    def escutar_comando_voz(self):
        def thread_voz():
            self.btn_voz.config(text="🎙️ Ouvindo Microfone...", bg="#FFCDD2")
            
            # --- CASO QUEIRA ATIVAR O MICROFONE REAL, RETIRE AS ASPAS TRIPLAS ABAIXO ---
            """
            import speech_recognition as sr
            r = sr.Recognizer()
            with sr.Microphone() as source:
                try:
                    r.adjust_for_ambient_noise(source, duration=1)
                    audio = r.listen(source, timeout=4)
                    texto_ouvido = r.recognize_google(audio, language='pt-BR').lower()
                    
                    if "brigadeiro" in texto_ouvido:
                        self.txt_codigo.delete(0, tk.END)
                        self.txt_codigo.insert(0, "7891000101")
                        self.adicionar_por_codigo()
                    elif "bolo" in texto_ouvido or "pote" in texto_ouvido:
                        self.txt_codigo.delete(0, tk.END)
                        self.txt_codigo.insert(0, "7891000102")
                        self.adicionar_por_codigo()
                    elif "palha" in texto_ouvido or "italiana" in texto_ouvido:
                        self.txt_codigo.delete(0, tk.END)
                        self.txt_codigo.insert(0, "7891000103")
                        self.adicionar_por_codigo()
                except Exception as e:
                    print("Erro no áudio:", e)
            """
            
            time.sleep(2) 
            self.txt_codigo.delete(0, tk.END)
            self.txt_codigo.insert(0, "7891000101")
            self.adicionar_por_codigo()
            
            self.btn_voz.config(text="🎙️ Ativar Comando de Voz", bg="#E1BEE7")
            
        threading.Thread(target=thread_voz).start()

# =====================================================================
# EXECUÇÃO DO SISTEMA
# =====================================================================
if __name__ == "__main__":
    inicializar_banco()
    app = SistemaDoceria()
    app.mainloop()
