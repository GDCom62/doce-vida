import os
import sqlite3
import streamlit as st
import pandas as pd
from datetime import datetime

# Configuração da página Web do Streamlit
st.set_page_config(page_title="SweetManager PDV Pro", page_icon="🍭", layout="wide")

# ==============================================================================
# CONFIGURAÇÃO UNIFICADA DO BANCO DE DADOS
# ==============================================================================
if not os.path.exists("banco_dados"):
    os.makedirs("banco_dados")

DB_NAME = os.path.join("banco_dados", "estoque_loja_independente.db")

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
        subtotal REAL NOT NULL,
        desconto_total REAL NOT NULL,
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

# Inicializa as tabelas locais no caminho correto
inicializar_banco_isolado()

# Gerenciamento de estado de login na sessão web
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "carrinho_novo" not in st.session_state:
    st.session_state.carrinho_novo = []

# --- TELA DE LOGIN ---
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

# CORREÇÃO: Inclusão do módulo de Relatórios de Vendas para seleção no Menu
menu = st.sidebar.radio("Navegar por Módulos:", [
    "🛒 Frente de Caixa (PDV)", 
    "📦 Almoxarifado / Estoque", 
    "👥 Cadastros (Clientes/Equipe)",
    "📊 Relatórios de Vendas"
])

if st.sidebar.button("🚪 Desconectar Sistema", type="secondary"):
    st.session_state.autenticado = False
    st.rerun()

# ==================== MÓDULO 1: PDV (ESTILO WAYBIT) ====================
if menu == "🛒 Frente de Caixa (PDV)":
    st.markdown("<h1 style='text-align: center; color: #1e3d59;'>Dominus - PDV</h1>", unsafe_allow_html=True)
    
    # Layout estruturado com base na imagem do monitor
    col_principal, col_botoes = st.columns([3.2, 1.0])
    
    with col_principal:
        st.markdown("<div style='background-color:#f5f5f5; padding:10px; border-radius:5px; text-align:center; font-weight:bold; font-size:24px; border:1px solid #ccc; margin-bottom:15px;'>NÃO IDENTIFICADO</div>", unsafe_allow_html=True)
        
        # Área superior de busca e especificações do item atual
        col_busca1, col_busca2 = st.columns([3, 1])
        with col_busca1:
            input_produto = st.text_input("Busca de produtos pelo nome ou código (Código de barras/QR Code):", key="search_pdv")
        with col_busca2:
            qtd_item = st.number_input("QUANTIDADE", min_value=1, value=1, step=1)
            desconto_item = st.number_input("Desconto por item (R$)", min_value=0.0, value=0.0, step=0.5)

        # Processamento da inserção de produto
        if input_produto:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT codigo_barras, nome, preco_venda, estoque_atual FROM produtos WHERE codigo_barras = ? OR nome LIKE ?", (input_produto, f"%{input_produto}%"))
            prod_achado = cursor.fetchone()
            conn.close()
            
            if prod_achado:
                if prod_achado[3] >= qtd_item:
                    v_unit = prod_achado[2]
                    v_tot = (v_unit * qtd_item) - desconto_item
                    
                    # Evita valores negativos por desconto abusivo
                    if v_tot < 0: 
                        v_tot = 0.0
                    
                    st.session_state.carrinho_novo.append({
                        "Seq": len(st.session_state.carrinho_novo) + 1,
                        "Cód. Produto": prod_achado[0],
                        "Descrição do Produto": prod_achado[1],
                        "Quantidade": qtd_item,
                        "Valor Unitário": v_unit,
                        "Valor Desconto": desconto_item,
                        "Valor Total": v_tot
                    })
                    st.toast(f"🍭 {prod_achado[1]} adicionado!", icon="✅")
                else:
                    st.warning(f"Atenção: Estoque insuficiente de '{prod_achado[1]}' (Disponível: {prod_achado[3]}).")
            else:
                st.error("Produto não localizado no Almoxarifado.")
        
        # Grid central de mercadorias lançadas
        st.write("### Itens no Cupom Atual")
        if st.session_state.carrinho_novo:
            df_cart = pd.DataFrame(st.session_state.carrinho_novo)
            st.dataframe(df_cart, use_container_width=True, hide_index=True)
        else:
            st.info("Aguardando inserção de mercadorias no leitor ou campo de busca...")

        # Cálculos de Subtotal e Descontos Totais
        subtotal = sum(item["Quantidade"] * item["Valor Unitário"] for item in st.session_state.carrinho_novo)
        descontos_itens = sum(item["Valor Desconto"] for item in st.session_state.carrinho_novo)
        
        st.markdown("---")
        col_calc1, col_calc2, col_calc3 = st.columns(3)
        with col_calc1:
            st.metric("SUBTOTAL (R$)", f"{subtotal:.2f}")
        with col_calc2:
            desc_total_venda = st.number_input("Desconto no total da venda (R$)", min_value=0.0, value=0.0, step=1.0)
        with col_calc3:
            total_compra = subtotal - descontos_itens - desc_total_venda
            if total_compra < 0: 
                total_compra = 0.0
            st.metric("VALOR TOTAL DA COMPRA (R$)", f"{total_compra:.2f}", delta="- Descontos Aplicados")

        # Seção 1.2: Formas de Pagamento Dinâmicas e Múltiplas
        st.markdown("### 💳 1.2 Formas de Pagamento")
        col_p1, col_p2, col_p3, col_p4 = st.columns(4)
        with col_p1:
            val_dinheiro = st.number_input("Valor em Dinheiro", min_value=0.0, value=0.0)
        with col_p2:
            val_pix = st.number_input("Valor no Pix", min_value=0.0, value=0.0)
        with col_p3:
            val_debito = st.number_input("Valor Cartão Débito", min_value=0.0, value=0.0)
        with col_p4:
            val_credito = st.number_input("Valor Cartão Crédito", min_value=0.0, value=0.0)

        total_recebido = val_dinheiro + val_pix + val_debito + val_credito
        valor_restante = total_compra - total_recebido
        troco = total_recebido - total_compra if total_recebido > total_compra else 0.0

        col_res1, col_res2, col_res3 = st.columns(3)
        with col_res1:
            st.write(f"**Valor Recebido:** R$ {total_recebido:.2f}")
        with col_res2:
            if valor_restante > 0:
                st.markdown(f"<span style='color:red; font-weight:bold;'>Valor Restante: R$ {valor_restante:.2f}</span>", unsafe_allow_html=True)
            else:
        st.markdown("<span style='color:green; font-weight:bold;'>Pagamento Completo</span>", unsafe_allow_html=True)
        with col_res3:
            st.write(f"**Troco Calculado:** R$ {troco:.2f}")

    with col_botoes:
        st.markdown("<div style='background-color:#e0e0e0; padding:10px; border-radius:5px; text-align:center; font-weight:bold;'>PAINEL DE COMANDOS</div>", unsafe_allow_html=True)
        st.write("")
        
        # Botão para finalizar venda (Habilitado apenas se houver itens e o pagamento cobrir o total)
        btn_finalizar = st.button("🛟 F6 - FECHAR VENDA", type="primary", use_container_width=True, disabled=(total_compra == 0 or valor_restante > 0))
        
        # Botão para cancelar item específico
        idx_cancelar = st.number_input("Nº Item p/ Cancelar", min_value=1, max_value=max(len(st.session_state.carrinho_novo), 1), step=1)
        btn_cancelar_item = st.button("⚠️ F4 - CANCELAR ITEM", type="secondary", use_container_width=True, disabled=(len(st.session_state.carrinho_novo) == 0))
        
        # Botão para cancelar venda inteira
        btn_cancelar_venda = st.button("❌ F7 - CANCELAR VENDA", type="secondary", use_container_width=True, disabled=(len(st.session_state.carrinho_novo) == 0))

        if btn_finalizar:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            
            # Executa a baixa no estoque do almoxarifado para cada item vendido
            for item in st.session_state.carrinho_novo:
                cursor.execute("UPDATE produtos SET estoque_atual = estoque_atual - ? WHERE codigo_barras = ?", (item["Quantidade"], item["Cód. Produto"]))
            
            # Mapeia dinamicamente as formas de pagamento informadas para histórico do banco
            formas_usadas = []
            if val_dinheiro > 0: formas_usadas.append(f"Dinheiro (R$ {val_dinheiro:.2f})")
            if val_pix > 0: formas_usadas.append(f"Pix (R$ {val_pix:.2f})")
            if val_debito > 0: formas_usadas.append(f"Débito (R$ {val_debito:.2f})")
            if val_credito > 0: formas_usadas.append(f"Crédito (R$ {val_credito:.2f})")
            str_pagamento = " + ".join(formas_usadas)
            
            # Salva o cabeçalho consolidado da venda no banco de dados
            cursor.execute("INSERT INTO vendas (data_hora, subtotal, desconto_total, total, forma_pagamento) VALUES (?, ?, ?, ?, ?)",
                           (datetime.now().strftime("%d/%m/%Y %H:%M"), subtotal, (descontos_itens + desc_total_venda), total_compra, str_pagamento))
            
            conn.commit()
            conn.close()
            st.success("Venda Concluída! Banco de dados atualizado com sucesso.")
            st.session_state.carrinho_novo = []
            st.rerun()

        if btn_cancelar_item:
            # Remove o item selecionado e reordena a numeração sequencial do cupom
            st.session_state.carrinho_novo = [item for item in st.session_state.carrinho_novo if item["Seq"] != idx_cancelar]
            for i, item in enumerate(st.session_state.carrinho_novo):
                item["Seq"] = i + 1
            st.toast("Item cancelado do cupom!", icon="🚨")
            st.rerun()

        if btn_cancelar_venda:
            st.session_state.carrinho_novo = []
            st.toast("Venda cancelada integralmente!", icon="❌")
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

# ==================== MÓDULO 4: RELATÓRIOS (CORRIGIDO) ====================
# ==================== MÓDULO 4: RELATÓRIOS COM GRÁFICO ====================
elif menu == "📊 Relatórios de Vendas":
    st.header("Painel Gerencial - Visualização de Desempenho")
    
    # Busca dados agrupados por dia para o gráfico
    conn = sqlite3.connect(DB_NAME)
    df_faturamento = pd.read_sql_query("""
        SELECT SUBSTR(data_hora, 1, 10) AS [Data], 
               SUM(total) AS [Total Faturado (R$)] 
        FROM vendas 
        GROUP BY [Data] 
        ORDER BY [Data] ASC
    """, conn)
    conn.close()
    
    # Exibição de Métricas no topo
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        total_acumulado = df_faturamento["Total Faturado (R$)"].sum() if not df_faturamento.empty else 0.0
        st.metric(label="Faturamento Total Acumulado", value=f"R$ {total_acumulado:.2f}")
    with col_m2:
        total_dias = len(df_faturamento)
        st.metric(label="Dias Operacionais Registrados", value=total_dias)
        
    st.markdown("---")
    
    # Seção do Gráfico de Desempenho
    st.subheader("📈 Evolução do Faturamento Diário")
    if not df_faturamento.empty:
        # Prepara o DataFrame colocando a Data como índice para o Streamlit gerar o gráfico corretamente
        df_grafico = df_faturamento.set_index("Data")
        st.line_chart(df_grafico, y="Total Faturado (R$)")
    else:
        st.info("Aguardando primeiras vendas para plotar o gráfico de desempenho.")
        
    st.markdown("---")
    st.subheader("📋 Histórico Completo de Cupons Finalizados")
    
    conn = sqlite3.connect(DB_NAME)
    df_vendas_todas = pd.read_sql_query("""
        SELECT id AS [Nº Cupom], 
               data_hora AS [Data/Hora], 
               subtotal AS [Subtotal (R$)], 
               desconto_total AS [Descontos (R$)], 
               total AS [Total Pago], 
               forma_pagamento AS [Formas de Pagto] 
        FROM vendas 
        ORDER BY id DESC
    """, conn)
    conn.close()
    
    if not df_vendas_todas.empty:
        st.dataframe(df_vendas_todas, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma venda realizada até o momento.")

