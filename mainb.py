import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# Configuração da página Web do Streamlit
st.set_page_config(page_title="SweetManager Independente", page_icon="🍭", layout="wide")

# Banco de dados exclusivo e isolado para este diretório
DB_NAME = "estoque_loja_independente.db"

def inicializar_banco_isolado():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Tabela de Funcionários/Acesso
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS funcionarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        usuario TEXT UNIQUE NOT NULL,
        senha TEXT NOT NULL,
        cargo TEXT NOT NULL
    )""")
    
    # 2. Tabela de Clientes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        cpf TEXT UNIQUE,
        telefone TEXT
    )""")
    
    # 3. Tabela do Almoxarifado (Produtos)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_barras TEXT UNIQUE,
        nome TEXT NOT NULL,
        preco_venda REAL NOT NULL,
        estoque_atual INTEGER DEFAULT 0,
        estoque_minimo INTEGER DEFAULT 5
    )""")
    
    # 4. Tabela de Histórico de Vendas (Saídas)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vendas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_hora TEXT NOT NULL,
        total REAL NOT NULL,
        forma_pagamento TEXT
    )""")

    # Usuário padrão para o primeiro acesso administrativo
    cursor.execute("SELECT COUNT(*) FROM funcionarios")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO funcionarios (nome, usuario, senha, cargo) VALUES (?, ?, ?, ?)",
                       ("Gerente Doces", "admin", "admin123", "Gerente"))
        
    # Produtos iniciais de teste para o Almoxarifado
    cursor.execute("SELECT COUNT(*) FROM produtos")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO produtos (codigo_barras, nome, preco_venda, estoque_atual) VALUES (?, ?, ?, ?)",
                       ("78910001", "Brigadeiro Tradicional", 4.00, 100))
        cursor.execute("INSERT INTO produtos (codigo_barras, nome, preco_venda, estoque_atual) VALUES (?, ?, ?, ?)",
                       ("78910002", "Bolo de Cenoura com Chocolate", 8.50, 25))
        
    conn.commit()
    conn.close()

# Inicializa as tabelas locais
inicializar_banco_isolado()

# Gerenciamento de estado de login na sessão web
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "carrinho_novo" not in st.session_state:
    st.session_state.carrinho_novo = []

# --- TELA DE LOGIN PROFISSIONAL ---
if not st.session_state.autenticado:
    st.markdown("<h2 style='text-align: center;'>🍭 SweetManager Pro - Acesso Restrito</h2>", unsafe_allow_html=True)
    col_l1, col_l2, col_l3 = st.columns([1, 1.5, 1])
    
    with col_l2:
        with st.form("login_sistema"):
            user = st.text_input("Usuário de Acesso")
            password = st.text_input("Senha", type="password")
            btn_login = st.form_submit_button("Entrar no Sistema", use_container_width=True)
            
            if btn_login:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("SELECT nome, cargo FROM funcionarios WHERE usuario = ? AND senha = ?", (user, password))
                user_data = cursor.fetchone()
                conn.close()
                
                if user_data:
                    st.session_state.autenticado = True
                    st.session_state.user_nome = user_data[0]
                    st.session_state.user_cargo = user_data[1]
                    st.success(f"Bem-vindo, {user_data[0]}!")
                    st.rerun()
                else:
                    st.error("Usuário ou senha inválidos para a base desta loja.")
    st.stop()

# --- INTERFACE PRINCIPAL APÓS LOGIN ---
st.sidebar.title("🍭 Menu Administrativo")
st.sidebar.write(f"👤 **{st.session_state.user_nome}** ({st.session_state.user_cargo})")
st.sidebar.markdown("---")

# Abas de navegação profissional do Streamlit
menu = st.sidebar.radio("Navegar por Módulos:", ["🛒 Frente de Caixa (PDV)", "📦 Almoxarifado / Estoque", "👥 Cadastros (Clientes/Equipe)"])

if st.sidebar.button("🚪 Desconectar Sistema", type="secondary"):
    st.session_state.autenticado = False
    st.rerun()

# ==================== MÓDULO 1: PDV ====================
if menu == "🛒 Frente de Caixa (PDV)":
    st.header("Balcão de Atendimento - Vendas Automatizadas")
    
    col_pdv1, col_pdv2 = st.columns([2, 1.2])
    
    with col_pdv1:
        st.subheader("Entrada de Itens")
        
        # O campo de texto captura leitores de código de barras físicos que dão "Enter" automático
        input_produto = st.text_input("Bipe o código de barras/QR Code ou digite o código/nome manualmente:", key="input_autom")
        
        # Funcionalidade por Voz (Simulada via entrada de comando do atendente ou integração nativa de texto)
        voz_check = st.checkbox("💡 Ativar assistente de voz simulado (Inserir comando via texto de voz)")
        if voz_check:
            comando_voz = st.text_input("Ex: 'adicionar brigadeiro' ou 'remover bolo':").lower()
            if "adicionar" in comando_voz:
                input_produto = comando_voz.replace("adicionar", "").strip()
        
        if input_produto:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            # Busca flexível: por código de barras exato ou por nome parcial do doce
            cursor.execute("SELECT codigo_barras, nome, preco_venda, estoque_atual FROM produtos WHERE codigo_barras = ? OR nome LIKE ?", (input_produto, f"%{input_produto}%"))
            prod_achado = cursor.fetchone()
            conn.close()
            
            if prod_achado:
                if prod_achado[3] > 0:
                    st.session_state.carrinho_novo.append({
                        "Código": prod_achado[0],
                        "Produto": prod_achado[1],
                        "Preço (R$)": prod_achado[2],
                        "Qtd": 1
                    })
                    st.toast(f"🍭 {prod_achado[1]} adicionado ao carrinho!", icon="✅")
                else:
                    st.warning(f"Atenção: '{prod_achado[1]}' está zerado no Almoxarifado!")
            else:
                st.error("Produto não localizado no Almoxarifado.")
        
        st.write("### Itens Selecionados no Carrinho")
        if st.session_state.carrinho_novo:
            df_cart = pd.DataFrame(st.session_state.carrinho_novo)
            st.dataframe(df_cart, use_container_width=True, hide_index=True)
            if st.button("🗑️ Esvaziar Carrinho Atual"):
                st.session_state.carrinho_novo = []
                st.rerun()
        else:
            st.info("Aguardando leitura de mercadorias no balcão...")

    with col_pdv2:
        st.subheader("Fechamento do Cupom")
        total_pago = sum(item["Preço (R$)"] * item["Qtd"] for item in st.session_state.carrinho_novo)
        st.metric(label="VALOR TOTAL", value=f"R$ {total_pago:.2f}")
        
        meio_pagto = st.selectbox("Forma de Recebimento:", ["Pix (Exibe QR Code)", "Dinheiro no Caixa", "Cartão de Crédito/Débito"])
        
        if meio_pagto == "Pix (Exibe QR Code)" and total_pago > 0:
            st.write("**QR Code Dinâmico Gerado para o Cliente:**")
            # Gera dinamicamente um QR Code de pagamento para a tela
            st.image(f"https://qrserver.com{total_pago:.2f}")
            
        btn_fechar_venda = st.button("🏁 Concluir Venda e Baixar Estoque", type="primary", use_container_width=True, disabled=(total_pago == 0))
        
        if btn_fechar_venda:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            
            # Executa a baixa automática no almoxarifado para cada item vendido
            for item in st.session_state.carrinho_novo:
                cursor.execute("UPDATE produtos SET estoque_atual = estoque_atual - ? WHERE codigo_barras = ?", (item["Qtd"], item["Código"]))
            
            # Registra o cabeçalho da venda
            cursor.execute("INSERT INTO vendas (data_hora, total, forma_pagamento) VALUES (?, ?, ?)",
                           (datetime.now().strftime("%d/%m/%Y %H:%M"), total_pago, meio_pagto))
            
            conn.commit()
            conn.close()
            st.success("Venda finalizada com sucesso! Saídas registradas no Almoxarifado.")
            st.session_state.carrinho_novo = []
            st.canvas = None
            st.rerun()

# ==================== MÓDULO 2: ALMOXARIFADO ====================
elif menu == "📦 Almoxarifado / Estoque":
    st.header("Gestão Central de Almoxarifado (Entradas e Saídas)")
    
    conn = sqlite3.connect(DB_NAME)
    df_almoxarifado = pd.read_sql_query("SELECT id, codigo_barras AS [Cód. Barras], nome AS [Nome do Doce], preco_venda AS [Preço de Venda (R$)], estoque_atual AS [Estoque Atual], estoque_minimo AS [Estoque Mínimo] FROM produtos", conn)
    conn.close()
    
    st.subheader("Inventário Físico da Loja")
    st.dataframe(df_almoxarifado, use_container_width=True, hide_index=True)
    
    col_alm1, col_alm2 = st.columns(2)
    
    with col_alm1:
        with st.expander("➕ Dar Entrada de Mercadoria (Abastecimento)"):
            with st.form("entrada_doces"):
                c_barras = st.text_input("Código de Barras do Lote")
                c_nome = st.text_input("Nome Comercial do Doce")
                c_preco = st.number_input("Preço de Venda Praticado", min_value=0.0, format="%.2f")
                c_qtd = st.number_input("Quantidade Recebida (Entrada)", min_value=1, step=1)
                btn_salvar_estoque = st.form_submit_button("Confirmar Entrada")
                
                if btn_salvar_estoque:
                    if c_barras and c_nome and c_preco > 0:
                        conn = sqlite3.connect(DB_NAME)
                        cursor = conn.cursor()
                        # Atualiza se o código já existir ou insere um novo doce
                        cursor.execute("""
                            INSERT INTO produtos (codigo_barras, nome, preco_venda, estoque_atual)
                            VALUES (?, ?, ?, ?)
                            ON CONFLICT(codigo_barras) DO UPDATE SET
                            estoque_atual = estoque_atual + excluded.estoque_atual,
                            preco_venda = excluded.preco_venda,
                            nome = excluded.nome
                        """, (c_barras, c_nome, c_preco, c_qtd))
                        conn.commit()
                        conn.close()
                        st.success(f"📦 Lote de '{c_nome}' integrado ao Almoxarifado com sucesso!")
                        st.rerun()
                    else:
                        st.error("⚠️ Por favor, preencha todos os campos corretamente antes de salvar.")

    with col_alm2:
        with st.expander("🚨 Alertas de Estoque Crítico (Mínimo)"):
            conn = sqlite3.connect(DB_NAME)
            # Busca produtos que estão abaixo ou iguais ao limite mínimo estabelecido
            df_critico = pd.read_sql_query("""
                SELECT codigo_barras AS [Código], 
                       nome AS [Doce], 
                       estoque_atual AS [Qtd Atual], 
                       estoque_minimo AS [Qtd Mínima] 
                FROM produtos 
                WHERE estoque_atual <= estoque_minimo
            """, conn)
            conn.close()
            
            if not df_critico.empty:
                st.warning("Os seguintes doces precisam de reposição urgente:")
                st.dataframe(df_critico, use_container_width=True, hide_index=True)
            else:
                st.success("✅ Todos os produtos estão com níveis de estoque seguros!")

# ==================== MÓDULO 3: CADASTROS ====================
elif menu == "👥 Cadastros (Clientes/Equipe)":
    st.header("Controle de Clientes e Funcionários de Acesso")
    
    tab_clientes, tab_funcionarios = st.tabs(["👥 Clientes Fidelidade", "🔐 Funcionários & Cargos"])
    
    with tab_clientes:
        st.subheader("Cadastro de Novo Cliente")
        with st.form("form_cliente"):
            cl_nome = st.text_input("Nome Completo")
            cl_cpf = st.text_input("CPF")
            cl_tel = st.text_input("Telefone de Contato")
            btn_cliente = st.form_submit_button("Cadastrar Cliente")
            
            if btn_cliente:
                if cl_nome and cl_cpf:
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    try:
                        cursor.execute("INSERT INTO clientes (nome, cpf, telefone) VALUES (?, ?, ?)", (cl_nome, cl_cpf, cl_tel))
                        conn.commit()
                        st.success(f"🎉 Cliente '{cl_nome}' cadastrado com sucesso!")
                    except sqlite3.IntegrityError:
                        st.error("❌ Erro: Este CPF já está cadastrado no sistema.")
                    finally:
                        conn.close()
                else:
                    st.error("⚠️ Nome e CPF são obrigatórios para o cadastro.")
                    
    with tab_funcionarios:
        st.subheader("Controle de Credenciais de Acesso")
        with st.form("form_func"):
            f_nome = st.text_input("Nome do Colaborador")
            f_user = st.text_input("Usuário para Login")
            f_senha = st.text_input("Senha de Acesso", type="password")
            f_cargo = st.selectbox("Cargo Operacional", ["Operador de Caixa", "Gerente", "Almoxarife"])
            btn_func = st.form_submit_button("Salvar Novo Funcionário")
            
            if btn_func:
                if f_nome and f_user and f_senha:
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    try:
                        cursor.execute("INSERT INTO funcionarios (nome, usuario, senha, cargo) VALUES (?, ?, ?, ?)", (f_nome, f_user, f_senha, f_cargo))
                        conn.commit()
                        st.success(f"🔐 Credenciais criadas para {f_nome} com cargo de {f_cargo}!")
                    except sqlite3.IntegrityError:
                        st.error("❌ Erro: Este nome de usuário já está sendo utilizado por outro colaborador.")
                    finally:
                        conn.close()
                else:
                    st.error("⚠️ Todos os campos de credenciais precisam ser preenchidos.")
# ==================== MÓDULO 4: RELATÓRIOS GRÁFICOS ====================
elif menu == "📊 Relatórios de Vendas":
    st.header("Painel Gerencial - Visualização de Desempenho")
    
    conn = sqlite3.connect(DB_NAME)
    
    # 1. Carrega dados de faturamento diário
    df_faturamento = pd.read_sql_query("""
        SELECT SUBSTR(data_hora, 1, 10) AS [Data], 
               SUM(total) AS [Total Faturado (R$)] 
        FROM vendas 
        GROUP BY [Data] 
        ORDER BY [Data] DESC
    """, conn)
    
    # 2. Carrega histórico de itens mais vendidos (Simulação baseada nas vendas registradas)
    # Nota: Em um fluxo completo, uma tabela 'vendas_itens' popularia perfeitamente essa métrica.
    df_produtos_mais_vendidos = pd.read_sql_query("""
        SELECT nome AS [Doce], 
               preco_venda AS [Preço Unitário (R$)],
               estoque_atual AS [Estoque Restante]
        FROM produtos 
        ORDER BY estoque_atual ASC 
        LIMIT 5
    """, conn)
    
    conn.close()
    
    # Exibição de Métricas Gerais de Destaque
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        total_acumulado = df_faturamento["Total Faturado (R$)"].sum() if not df_faturamento.empty else 0.0
        st.metric(label="Faturamento Total Acumulado", value=f"R$ {total_acumulado:.2f}")
    with col_m2:
        total_vendas_count = len(df_faturamento)
        st.metric(label="Dias Operacionais Registrados", value=total_vendas_count)
        
    st.markdown("---")
    
    col_graf1, col_graf2 = st.columns(2)
    
    with col_graf1:
        st.subheader("📈 Faturamento por Dia")
        if not df_faturamento.empty:
            # Renderiza um gráfico de linhas nativo e limpo do Streamlit para controle diário
            st.line_chart(df_faturamento.set_index("Data")["Total Faturado (R$)"])
            st.dataframe(df_faturamento, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma venda realizada até o momento para gerar o gráfico de faturamento.")
            
    with col_graf2:
        st.subheader("🍩 Movimentação e Giro de Estoque")
        if not df_produtos_mais_vendidos.empty:
            st.write("Doces com maior saída (Menor estoque atual no almoxarifado):")
            # Apresenta gráficos de barras comparativos nativos do Streamlit
            st.bar_chart(df_produtos_mais_vendidos.set_index("Doce")["Estoque Restante"])
            st.dataframe(df_produtos_mais_vendidos, use_container_width=True, hide_index=True)
        else:
            st.info("Cadastre produtos no Almoxarifado para visualizar as métricas de giro.")
