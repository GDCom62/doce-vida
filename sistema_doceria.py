import streamlit as st
import sqlite3
import time
from datetime import datetime, timedelta

# Configuração visual profissional da página da Doceria
st.set_page_config(page_title="CandySystem Web Pro", page_icon="🧁", layout="wide")

# =====================================================================
# 1. BANCO DE DADOS (Com suporte à Validade e Cadastro de Equipe)
# =====================================================================
def inicializar_banco():
    conn = sqlite3.connect('doceria.db')
    cursor = conn.cursor()
    
    # 1. Cria a tabela básica se ela não existir
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_barras TEXT UNIQUE,
            nome TEXT NOT NULL,
            preco REAL NOT NULL,
            estoque INTEGER NOT NULL DEFAULT 0
        )
    ''')
    
    # 2. CORREÇÃO AUTOMÁTICA: Adiciona a coluna validade caso seu banco antigo não tenha ela
    try:
        cursor.execute("ALTER TABLE produtos ADD COLUMN validade TEXT")
    except sqlite3.OperationalError:
        # Se entrar aqui, significa que a coluna validade já existia, então ignora o erro
        pass
        
    # 3. Cria as demais tabelas do sistema
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cpf TEXT UNIQUE,
            telefone TEXT
        )
    ''')
    
    # Corrige tabela de clientes antiga se necessário (caso tenha erro de digitação anterior)
    try:
        cursor.execute("ALTER TABLE clientes ADD COLUMN telefone TEXT")
    except sqlite3.OperationalError:
        pass

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
    
    # Insere os dados padrão apenas se a tabela estiver completamente vazia
    cursor.execute("SELECT COUNT(*) FROM produtos")
    if cursor.fetchone()[0] == 0:
        from datetime import datetime, timedelta
        hoje = datetime.now()
        val_vencendo = (hoje + timedelta(days=3)).strftime('%Y-%m-%d')
        val_longa = (hoje + timedelta(days=60)).strftime('%Y-%m-%d')
        
        cursor.executemany("INSERT INTO produtos (codigo_barras, nome, preco, estoque, validade) VALUES (?, ?, ?, ?, ?)", [
            ('7891000101', 'Brigadeiro Gourmet', 4.50, 100, val_vencendo),
            ('7891000102', 'Bolo de Pote Ninho', 12.00, 30, val_vencendo),
            ('7891000103', 'Palha Italiana', 6.00, 50, val_longa)
        ])
        cursor.executemany("INSERT INTO funcionarios (usuario, senha, cargo) VALUES (?, ?, ?)", [
            ('admin', 'admin123', 'Gerente'),
            ('caixa1', '1234', 'Operador')
        ])
    conn.commit()
    conn.close()

inicializar_banco()

# Inicialização de Estados da Sessão
if 'usuario_logado' not in st.session_state:
    st.session_state.usuario_logado = None
if 'cargo_logado' not in st.session_state:
    st.session_state.cargo_logado = None
if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []

# =====================================================================
# LOGO ESTILIZADO EM HTML/CSS (Para não depender de imagem local)
# =====================================================================
def exibir_logo():
    st.markdown("""
        <div style='text-align: center; margin-bottom: 20px;'>
            <h1 style='font-family: "Pacifico", cursive, sans-serif; color: #D32F2F; font-size: 50px; margin-bottom: 0px;'>🍒 Doce Vida</h1>
            <p style='font-family: "Helvetica", sans-serif; color: #7D5A50; font-size: 14px; letter-spacing: 2px;'>CONFEITARIA & DOCERIA ARTESANAL</p>
        </div>
    """, unsafe_allow_html=True)

# =====================================================================
# 2. TELA DE LOGIN
# =====================================================================
if st.session_state.usuario_logado is None:
    exibir_logo()
    st.markdown("<h3 style='text-align: center; color: #5D4037;'>🧁 Acesso ao Sistema</h3>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("Formulário de Login"):
            usuario = st.text_input("Usuário:", value="admin")
            senha = st.text_input("Senha:", value="admin123", type="password")
            btn_login = st.form_submit_button("Entrar no Sistema")
            
            if btn_login:
                conn = sqlite3.connect('doceria.db')
                cursor = conn.cursor()
                cursor.execute("SELECT cargo FROM funcionarios WHERE usuario = ? AND senha = ?", (usuario, senha))
                resultado = cursor.fetchone()
                conn.close()
                
                if resultado:
                    st.session_state.usuario_logado = usuario
                    st.session_state.cargo_logado = resultado[0]
                    st.success("Bem-vindo!")
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
    st.stop()

# =====================================================================
# 3. INTERFACE PRINCIPAL (Abas do Sistema)
# =====================================================================
exibir_logo()
st.markdown(f"<p style='float: right; font-weight: bold; color: #7D5A50; margin-top: -40px;'>👤 {st.session_state.usuario_logado.upper()} ({st.session_state.cargo_logado})</p>", unsafe_allow_html=True)

# Definição das Abas baseado nas permissões do usuário logado
Abas_Principais = ["🛒 Frente de Caixa (PDV)", "📦 Almoxarifado / Estoque", "👥 Cadastro de Clientes"]
if st.session_state.cargo_logado == "Gerente":
    Abas_Principais.append("👥 Gerenciamento de Equipe")

abas = st.tabs(Abas_Principais)

# -----------------------------------------------------------------
# FRENTE DE CAIXA (PDV)
# -----------------------------------------------------------------
with abas[0]:
    col_esq, col_dir = st.columns([1, 1])
    
    with col_esq:
        st.subheader("Entrada de Itens")
        codigo_digitado = st.text_input("Bipar Código de Barras, QR ou Manual:", key="pdv_codigo")
        
        if codigo_digitado:
            conn = sqlite3.connect('doceria.db')
            cursor = conn.cursor()
            cursor.execute("SELECT codigo_barras, nome, preco, estoque FROM produtos WHERE codigo_barras = ?", (codigo_digitado,))
            produto = cursor.fetchone()
            conn.close()
            
            if produto:
                if produto[3] > 0:
                    st.session_state.carrinho.append({'codigo': produto[0], 'nome': produto[1], 'preco': produto[2], 'qtd': 1})
                    st.toast(f"Adicionado: {produto[1]}", icon="✅")
                else:
                    st.error(f"Estoque esgotado para: {produto[1]}")
            else:
                st.error("Produto não localizado no almoxarifado.")
        
        total_venda = sum(item['preco'] * item['qtd'] for item in st.session_state.carrinho)
        st.markdown(f"## Total: <span style='color: #D32F2F;'>R$ {total_venda:.2f}</span>", unsafe_allow_html=True)
        
        if st.button("💸 Concluir Venda Balcão", type="primary"):
            if st.session_state.carrinho:
                conn = sqlite3.connect('doceria.db')
                cursor = conn.cursor()
                for item in st.session_state.carrinho:
                    cursor.execute("UPDATE produtos SET estoque = estoque - ? WHERE codigo_barras = ?", (item['qtd'], item['codigo']))
                
                data_atual = time.strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute("INSERT INTO vendas (data_hora, total, funcionario_usuario) VALUES (?, ?, ?)", 
                               (data_atual, total_venda, st.session_state.usuario_logado))
                conn.commit()
                conn.close()
                st.session_state.carrinho = []
                st.success("Venda registrada!")
                st.rerun()
            else:
                st.warning("O carrinho está vazio.")
                
    with col_dir:
        st.subheader("Itens da Venda")
        if st.session_state.carrinho:
            st.table(st.session_state.carrinho)
            if st.button("🗑️ Cancelar Tudo"):
                st.session_state.carrinho = []
                st.rerun()
        else:
            st.info("Aguardando inserção de produtos...")

# -----------------------------------------------------------------
# ALMOXARIFADO / ESTOQUE COM VERIFICAÇÃO DE VALIDADE E CRUDS
# -----------------------------------------------------------------
with abas[1]:
    if st.session_state.cargo_logado != "Gerente":
        st.error("🔒 Área Restrita: Apenas administradores/gerentes possuem acesso ao Almoxarifado.")
    else:
        st.subheader("Controle Geral de Produtos")
        
        # Conexão e carregamento de produtos
        conn = sqlite3.connect('doceria.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, codigo_barras, nome, preco, estoque, validade FROM produtos")
        produtos_lista = cursor.fetchall()
        conn.close()
        
        # Análise automática de alertas de vencimento antes de desenhar a tabela
        hoje = datetime.now().date()
        st.markdown("#### 🚨 Alertas Urgentes de Validade")
        alertas_exibidos = 0
        
        for p in produtos_lista:
            if p[5]: # Se tiver validade cadastrada
                try:
                    data_val = datetime.strptime(p[5], '%Y-%m-%d').date()
                    dias_restantes = (data_val - hoje).days
                    
                    if dias_restantes <= 0:
                        st.error(f"❌ O produto **{p[2]}** (Cód: {p[1]}) **VENCEU** em {data_val.strftime('%d/%m/%Y')}!")
                        alertas_exibidos += 1
                    elif dias_restantes <= 7:
                        st.warning(f"⚠️ Atenção! O produto **{p[2]}** (Cód: {p[1]}) vai vencer em **{dias_restantes} dias** ({data_val.strftime('%d/%m/%Y')}).")
                        alertas_exibidos += 1
                except ValueError:
                    pass
        if alertas_exibidos == 0:
            st.success("Tudo perfeito! Nenhum produto próximo do vencimento nos próximos 7 dias.")
            
        st.markdown("---")
        st.markdown("#### Inventário Físico")
        st.dataframe(produtos_lista, column_config={
            "0": "ID", "1": "Código de Barras", "2": "Nome do Doce", "3": "Preço de Venda", "4": "Estoque", "5": "Data de Validade"
        }, use_container_width=True)
        
        # Divisão de colunas para gerenciamento de dados (Novo, Editar e Excluir)
        col_adm1, col_adm2, col_adm3 = st.columns(3)
        
        with col_adm1:
            st.markdown("#### 📥 Cadastrar / Abastecer Doce")
            with st.form("Novo Produto"):
                cod_in = st.text_input("Código de Barras ou QR:")
                nome_in = st.text_input("Nome do Doce:")
                preco_in = st.number_input("Preço de Venda (R$):", min_value=0.0, step=0.50)
                est_in = st.number_input("Quantidade Inicial:", min_value=0, step=1)
                val_in = st.date_input("Data de Validade:")
                
                sub_prod = st.form_submit_button("Salvar no Almoxarifado")
                if sub_prod and cod_in and nome_in:
                    conn = sqlite3.connect('doceria.db')
                    cursor = conn.cursor()
                    try:
                        cursor.execute("INSERT INTO produtos (codigo_barras, nome, preco, estoque, validade) VALUES (?, ?, ?, ?, ?)",
                                       (cod_in, nome_in, preco_in, est_in, val_in.strftime('%Y-%m-%d')))
                        conn.commit()
                        st.success("Produto adicionado!")
                        time.sleep(1)
                        st.rerun()
                    except sqlite3.IntegrityError:
                        # Se já existe o código de barras, atualiza a quantidade em estoque
                        cursor.execute("UPDATE produtos SET estoque = estoque + ? WHERE codigo_barras = ?", (est_in, cod_in))
                        conn.commit()
                        st.success("Estoque atualizado!")
                        time.sleep(1)
                        st.rerun()
                    finally:
                        conn.close()
        with col_adm2:
            st.markdown("#### ✏️ Editar Dados do Doce")
            id_editar = st.number_input("Digite o ID do doce para alterar:", min_value=1, step=1)
            with st.form("Editar Produto"):
                novo_nome = st.text_input("Novo Nome:")
                novo_preco = st.number_input("Novo Preço (R$):", min_value=0.0, step=0.50)
                nova_val = st.date_input("Nova Validade:")
                sub_edit = st.form_submit_button("Aplicar Alterações")
                
                if sub_edit:
                    conn = sqlite3.connect('doceria.db')
                    cursor = conn.cursor()
                    cursor.execute("UPDATE produtos SET nome=?, preco=?, validade=? WHERE id=?", 
                                   (novo_nome, novo_preco, nova_val.strftime('%Y-%m-%d'), id_editar))
                    if cursor.rowcount > 0:
                        conn.commit()
                        st.success("Dados salvos!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("ID não localizado.")
                    conn.close()

        with col_adm3:
            st.markdown("#### ❌ Remover do Sistema")
            id_deletar = st.number_input("Digite o ID do doce para deletar:", min_value=1, step=1)
            if st.button("Excluir Produto Definitivamente", type="primary"):
                conn = sqlite3.connect('doceria.db')
                cursor = conn.cursor()
                cursor.execute("DELETE FROM produtos WHERE id = ?", (id_deletar,))
                if cursor.rowcount > 0:
                    conn.commit()
                    st.success("Produto excluído do almoxarifado.")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Produto não localizado para exclusão.")
                conn.close()

# -----------------------------------------------------------------
# CADASTRO DE CLIENTES
# -----------------------------------------------------------------
with abas[2]:
    st.subheader("Gerenciamento de Clientes")
    with st.form("Novo Cliente"):
        nome_cli = st.text_input("Nome Completo:")
        cpf_cli = st.text_input("CPF:")
        tel_cli = st.text_input("Telefone:")
        if st.form_submit_button("Cadastrar"):
            if nome_cli:
                conn = sqlite3.connect('doceria.db')
                cursor = conn.cursor()
                try:
                    cursor.execute("INSERT INTO clientes (nome, cpf, telefone) VALUES (?, ?, ?)", (nome_cli, cpf_cli, tel_cli))
                    conn.commit()
                    st.success("Cliente Cadastrado!")
                except:
                    st.error("Erro no cadastro ou CPF duplicado.")
                finally:
                    conn.close()
                    st.rerun()

    conn = sqlite3.connect('doceria.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, cpf, telefone FROM clientes")
    st.dataframe(cursor.fetchall(), use_container_width=True)
    conn.close()
# -----------------------------------------------------------------
# NOVA ABA: GERENCIAMENTO DE EQUIPE (Apenas visível para Gerente)
# -----------------------------------------------------------------
if st.session_state.cargo_logado == "Gerente":
    with abas[3]:
        st.subheader("👥 Cadastro de Funcionários e Controle de Acessos")
        
        col_func1, col_func2 = st.columns(2)
        
        with col_func1:
            st.markdown("#### 🔐 Registrar Novo Usuário")
            with st.form("Novo Funcionario"):
                novo_user = st.text_input("Nome de Usuário (Login):").strip()
                nova_senha = st.text_input("Senha de Acesso:", type="password").strip()
                novo_cargo = st.selectbox("Nível de Acesso (Cargo):", ["Operador", "Gerente"])
                
                sub_func = st.form_submit_button("Criar Conta de Acesso")
                if sub_func and novo_user and nova_senha:
                    conn = sqlite3.connect('doceria.db')
                    cursor = conn.cursor()
                    try:
                        cursor.execute("INSERT INTO funcionarios (usuario, senha, cargo) VALUES (?, ?, ?)", 
                                       (novo_user, nova_senha, novo_cargo))
                        conn.commit()
                        st.success(f"Funcionário {novo_user.upper()} criado com sucesso!")
                        time.sleep(1)
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Esse nome de usuário já está em uso.")
                    finally:
                        conn.close()
        
        with col_func2:
            st.markdown("#### 📋 Equipe Cadastrada")
            conn = sqlite3.connect('doceria.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id, usuario, cargo FROM funcionarios")
            equipe = cursor.fetchall()
            conn.close()
            st.dataframe(equipe, column_config={"0": "ID", "1": "Nome de Usuário", "2": "Nível"}, use_container_width=True)

# =====================================================================
# MENU LATERAL (Sidebar - Comandos Rápidos e Voz)
# =====================================================================
with st.sidebar:
    st.markdown("### 🎙 shrink Comandos Rápidos de Voz")
    teste_voz = st.text_input("Fale ou digite o comando de voz aqui:")
    
    if st.button("🎙️ Processar Áudio"):
        if teste_voz:
            texto_p = teste_voz.lower()
            cod_v = None
            if "brigadeiro" in texto_p: cod_v = "7891000101"
            elif "bolo" in texto_p: cod_v = "7891000102"
            elif "palha" in texto_p: cod_v = "7891000103"
            
            if cod_v:
                conn = sqlite3.connect('doceria.db')
                cursor = conn.cursor()
                cursor.execute("SELECT codigo_barras, nome, preco, estoque FROM produtos WHERE codigo_barras = ?", (cod_v,))
                p = cursor.fetchone()
                conn.close()
                if p and p[3] > 0:
                    st.session_state.carrinho.append({'codigo': p[0], 'nome': p[1], 'preco': p[2], 'qtd': 1})
                    st.success(f"Adicionado via voz: {p[1]}")
                    time.sleep(0.5)
                    st.rerun()
        else:
            st.info("Simulando comando: 'Quero Brigadeiro'")
            time.sleep(1)
            st.session_state.carrinho.append({'codigo': '7891000101', 'nome': 'Brigadeiro Gourmet', 'preco': 4.5, 'qtd': 1})
            st.rerun()
            
    st.markdown("---")
    if st.button("Exit / Fazer Log Out", type="secondary"):
        st.session_state.usuario_logado = None
        st.session_state.cargo_logado = None
        st.session_state.carrinho = []
        st.rerun()
