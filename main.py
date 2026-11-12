import os
import sqlite3
import streamlit as st
import pandas as pd
from datetime import datetime

# Configuração da página Web do Streamlit
st.set_page_config(page_title="Dominus PDV - Gestão Integrada", page_icon="🛒", layout="wide")

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
        cursor.execute(
            "INSERT INTO funcionarios (nome, usuario, senha, cargo) VALUES (?, ?, ?, ?)",
            ("Administrador", "admin", "admin123", "Gerente")
        )
        
    # Produtos iniciais de teste para o Almoxarifado
    cursor.execute("SELECT COUNT(*) FROM produtos")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO produtos (codigo_barras, nome, preco_venda, estoque_atual) VALUES (?, ?, ?, ?)",
            ("78910001", "Brigadeiro Tradicional", 4.00, 100)
        )
        cursor.execute(
            "INSERT INTO produtos (codigo_barras, nome, preco_venda, estoque_atual) VALUES (?, ?, ?, ?)",
            ("78910002", "Bolo de Cenoura com Chocolate", 8.50, 25)
        )
        
    conn.commit()
    conn.close()

# Inicializa as tabelas locais
inicializar_banco_isolado()

# Gerenciamento de estado da sessão
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "user_nome" not in st.session_state:
    st.session_state.user_nome = ""
if "user_cargo" not in st.session_state:
    st.session_state.user_cargo = ""
if "carrinho_novo" not in st.session_state:
    st.session_state.carrinho_novo = []

# ==============================================================================
# TELA DE LOGIN
# ==============================================================================
if not st.session_state.autenticado:
    st.markdown("<h2 style='text-align: center;'>🛒 Dominus PDV - Acesso ao Sistema</h2>", unsafe_allow_html=True)
    col_l1, col_l2, col_l3 = st.columns([1, 1.5, 1])
    
    with col_l2:
        with st.form("login_sistema"):
            user = st.text_input("Usuário de Acesso")
            password = st.text_input("Senha", type="password")
            btn_login = st.form_submit_button("Entrar no Sistema", use_container_width=True)
            
            if btn_login:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT nome, cargo FROM funcionarios WHERE usuario = ? AND senha = ?", 
                    (user, password)
                )
                user_data = cursor.fetchone()
                conn.close()
                
                if user_data:
                    st.session_state.autenticado = True
                    st.session_state.user_nome = user_data[0]
                    st.session_state.user_cargo = user_data[1]
                    st.rerun()
                else:
                    st.error("Usuário ou senha inválidos.")
    st.stop()

# ==============================================================================
# MENU LATERAL DE NAVEGAÇÃO
# ==============================================================================
st.sidebar.title("🧭 Menu Principal")
st.sidebar.write(f"👤 **{st.session_state.user_nome}** ({st.session_state.user_cargo})")
st.sidebar.markdown("---")

menu = st.sidebar.radio("Selecione o Módulo:", [
    "🛒 Frente de Caixa (PDV)", 
    "📦 Almoxarifado / Estoque", 
    "👥 Cadastros (Clientes/Equipe)",
    "📊 Relatórios de Vendas"
])

st.sidebar.markdown("---")
if st.sidebar.button("🚪 Sair do Sistema", use_container_width=True):
    st.session_state.autenticado = False
    st.session_state.carrinho_novo = []
    st.rerun()

# ==============================================================================
# MÓDULO 1: PDV DEDICADO (SEM CATÁLOGO LATERAL)
# ==============================================================================
if menu == "🛒 Frente de Caixa (PDV)":
    st.markdown("<h1 style='text-align: center; color: #1e3d59;'>Dominus - Frente de Caixa (PDV)</h1>", unsafe_allow_html=True)
    
    col_principal, col_botoes = st.columns([3.5, 1.0])
    
    with col_principal:
        # Formulário de busca e inserção rápida
        with st.form("form_busca_pdv", clear_on_submit=True):
            col_b1, col_b2, col_b3, col_b4 = st.columns([2.5, 1.0, 1.0, 1.0])
            with col_b1:
                input_produto = st.text_input("🔍 Código de Barras ou Nome do Produto:")
            with col_b2:
                qtd_item = st.number_input("Qtd:", min_value=1, value=1, step=1)
            with col_b3:
                desconto_item = st.number_input("Desc. Item (R$):", min_value=0.0, value=0.0, step=0.50, format="%.2f")
            with col_b4:
                st.write("")
                st.write("")
                btn_adicionar = st.form_submit_button("➕ Lançar", use_container_width=True)

        if btn_adicionar and input_produto.strip():
            termo = input_produto.strip()
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT codigo_barras, nome, preco_venda, estoque_atual 
                FROM produtos 
                WHERE codigo_barras = ? OR nome LIKE ?
            """, (termo, f"%{termo}%"))
            prod_achado = cursor.fetchone()
            conn.close()
            
            if prod_achado:
                cod_barras, nome_prod, v_unit, estoque_disp = prod_achado
                
                # Verifica quanto deste item já está no carrinho atual
                qtd_no_carrinho = sum(
                    item["Quantidade"] for item in st.session_state.carrinho_novo if item["Código"] == cod_barras
                )
                
                if estoque_disp >= (qtd_item + qtd_no_carrinho):
                    v_tot = max(0.0, (v_unit * qtd_item) - desconto_item)
                    
                    st.session_state.carrinho_novo.append({
                        "Seq": len(st.session_state.carrinho_novo) + 1,
                        "Código": cod_barras,
                        "Descrição do Produto": nome_prod,
                        "Quantidade": qtd_item,
                        "Valor Unitário": float(v_unit),
                        "Desconto Item": float(desconto_item),
                        "Valor Total": float(v_tot)
                    })
                    st.toast(f"✅ {nome_prod} adicionado ao cupom!")
                else:
                    st.warning(f"⚠️ Estoque insuficiente para '{nome_prod}'. Disponível: {estoque_disp} un.")
            else:
                st.error(f"❌ Produto '{termo}' não encontrado no estoque.")

        # Tabela do Cupom Atual
        st.subheader("🧾 Itens da Venda")
        if st.session_state.carrinho_novo:
            df_cart = pd.DataFrame(st.session_state.carrinho_novo)
            st.dataframe(
                df_cart,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Valor Unitário": st.column_config.NumberColumn(format="R$ %.2f"),
                    "Desconto Item": st.column_config.NumberColumn(format="R$ %.2f"),
                    "Valor Total": st.column_config.NumberColumn(format="R$ %.2f"),
                }
            )
        else:
            st.info("Caixa Livre. Bipe um código de barras ou digite o nome do produto acima.")

        st.markdown("---")

        # Totais e Desconto Geral
        subtotal = sum(item["Quantidade"] * item["Valor Unitário"] for item in st.session_state.carrinho_novo)
        descontos_itens = sum(item["Desconto Item"] for item in st.session_state.carrinho_novo)
        
        col_tot1, col_tot2, col_tot3 = st.columns(3)
        with col_tot1:
            st.metric("SUBTOTAL", f"R$ {subtotal:.2f}")
        with col_tot2:
            desc_total_venda = st.number_input("Desconto no Total da Venda (R$):", min_value=0.0, value=0.0, step=1.0, format="%.2f")
        with col_tot3:
            total_compra = max(0.0, subtotal - descontos_itens - desc_total_venda)
            st.metric("VALOR TOTAL DA COMPRA", f"R$ {total_compra:.2f}")

        st.markdown("---")

        # Formas de Pagamento (Aceita pagamento dividido)
        st.subheader("💳 Formas de Pagamento")
        col_p1, col_p2, col_p3, col_p4 = st.columns(4)
        with col_p1:
            val_dinheiro = st.number_input("💵 Dinheiro (R$)", min_value=0.0, value=0.0, step=1.0, format="%.2f")
        with col_p2:
            val_pix = st.number_input("💠 Pix (R$)", min_value=0.0, value=0.0, step=1.0, format="%.2f")
        with col_p3:
            val_debito = st.number_input("💳 Débito (R$)", min_value=0.0, value=0.0, step=1.0, format="%.2f")
        with col_p4:
            val_credito = st.number_input("💳 Crédito (R$)", min_value=0.0, value=0.0, step=1.0, format="%.2f")

        # Cálculos Financeiros Automáticos e Trava de Troco
        total_recebido = val_dinheiro + val_pix + val_debito + val_credito
        pagamentos_eletronicos = val_pix + val_debito + val_credito
        valor_restante = max(0.0, total_compra - total_recebido)
        
        # Trava: Pagamentos eletrônicos não podem exceder o valor total da compra
        excesso_eletronico = pagamentos_eletronicos > (total_compra + 0.009)
        troco = max(0.0, total_recebido - total_compra) if (total_compra > 0 and not excesso_eletronico) else 0.0

        st.write("")
        col_res1, col_res2, col_res3 = st.columns(3)
        with col_res1:
            st.info(f"**Valor Recebido:** R$ {total_recebido:.2f}")
        with col_res2:
            if excesso_eletronico:
                st.error("⚠️ Pix/Cartão excede o total!")
            elif valor_restante > 0.009:
                st.error(f"**Valor Restante:** R$ {valor_restante:.2f}")
            else:
                st.success("**Status:** Pagamento Completo")
        with col_res3:
            st.warning(f"**Troco:** R$ {troco:.2f}")

    # Painel Lateral Direito de Comandos
    with col_botoes:
        st.markdown("<div style='background-color:#1e3d59; color:white; padding:10px; border-radius:5px; text-align:center; font-weight:bold;'>COMANDOS DO CAIXA</div>", unsafe_allow_html=True)
        st.write("")
        
        tem_itens = len(st.session_state.carrinho_novo) > 0
        pagamento_ok = (total_compra > 0) and (valor_restante <= 0.009) and (not excesso_eletronico)

        # Botão Finalizar Venda
        btn_finalizar = st.button(
            "✅ FINALIZAR VENDA", 
            type="primary", 
            use_container_width=True, 
            disabled=not (tem_itens and pagamento_ok)
        )
        
        st.markdown("---")
        
        # Cancelar Item Específico
        max_seq = max(len(st.session_state.carrinho_novo), 1)
        idx_cancelar = st.number_input("Nº Seq. do Item:", min_value=1, max_value=max_seq, step=1, disabled=not tem_itens)
        btn_cancelar_item = st.button(
            "⚠️ CANCELAR ITEM", 
            use_container_width=True, 
            disabled=not tem_itens
        )
        
        st.markdown("---")
        
        # Cancelar Venda Inteira
        btn_cancelar_venda = st.button(
            "❌ CANCELAR VENDA", 
            use_container_width=True, 
            disabled=not tem_itens
        )

        # Ação: Finalizar Venda e Salvar no Banco
        if btn_finalizar:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            
            # 1. Atualiza o estoque
            for item in st.session_state.carrinho_novo:
                cursor.execute(
                    "UPDATE produtos SET estoque_atual = estoque_atual - ? WHERE codigo_barras = ?", 
                    (item["Quantidade"], item["Código"])
                )
            
            # 2. Monta descrição detalhada das formas de pagamento
            formas_usadas = []
            if val_dinheiro > 0: formas_usadas.append(f"Dinheiro: R$ {val_dinheiro:.2f}")
            if val_pix > 0: formas_usadas.append(f"Pix: R$ {val_pix:.2f}")
            if val_debito > 0: formas_usadas.append(f"Débito: R$ {val_debito:.2f}")
            if val_credito > 0: formas_usadas.append(f"Crédito: R$ {val_credito:.2f}")
            str_pagamento = " | ".join(formas_usadas)
            
            # 3. Grava a venda na tabela 'vendas'
            desconto_geral_aplicado = descontos_itens + desc_total_venda
            cursor.execute("""
                INSERT INTO vendas (data_hora, subtotal, desconto_total, total, forma_pagamento) 
                VALUES (?, ?, ?, ?, ?)
            """, (
                datetime.now().strftime("%d/%m/%Y %H:%M"), 
                subtotal, 
                desconto_geral_aplicado, 
                total_compra, 
                str_pagamento
            ))
            
            conn.commit()
            conn.close()
            
            st.session_state.carrinho_novo = []
            st.success("🎉 Venda finalizada e salva com sucesso!")
            st.rerun()

        # Ação: Cancelar Item
        if btn_cancelar_item:
            st.session_state.carrinho_novo = [
                item for item in st.session_state.carrinho_novo if item["Seq"] != idx_cancelar
            ]
            for i, item in enumerate(st.session_state.carrinho_novo):
                item["Seq"] = i + 1
            st.toast(f"Item {idx_cancelar} removido do cupom.")
            st.rerun()

        # Ação: Cancelar Venda
        if btn_cancelar_venda:
            st.session_state.carrinho_novo = []
            st.toast("Venda cancelada.")
            st.rerun()
# ==============================================================================
# MÓDULO 2: ALMOXARIFADO / ESTOQUE
# ==============================================================================
elif menu == "📦 Almoxarifado / Estoque":
    st.header("Gestão Central de Almoxarifado (Entradas e Saídas)")
    
    conn = sqlite3.connect(DB_NAME)
    df_almoxarifado = pd.read_sql_query("""
        SELECT id, 
               codigo_barras AS [Cód. Barras], 
               nome AS [Nome do Produto], 
               preco_venda AS [Preço de Venda (R$)], 
               estoque_atual AS [Estoque Atual], 
               estoque_minimo AS [Estoque Mínimo] 
        FROM produtos
    """, conn)
    conn.close()
    
    st.subheader("Inventário Físico da Loja")
    st.dataframe(df_almoxarifado, use_container_width=True, hide_index=True)
    
    col_alm1, col_alm2 = st.columns(2)
    
    with col_alm1:
        with st.expander("➕ Dar Entrada de Mercadoria (Abastecimento)", expanded=True):
            with st.form("entrada_produtos"):
                c_barras = st.text_input("Código de Barras do Lote")
                c_nome = st.text_input("Nome Comercial do Produto")
                c_preco = st.number_input("Preço de Venda Praticado (R$)", min_value=0.0, format="%.2f")
                c_qtd = st.number_input("Quantidade Recebida (Entrada)", min_value=1, step=1)
                btn_salvar_estoque = st.form_submit_button("Confirmar Entrada")
                
                if btn_salvar_estoque:
                    if c_barras.strip() and c_nome.strip() and c_preco > 0:
                        conn = sqlite3.connect(DB_NAME)
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO produtos (codigo_barras, nome, preco_venda, estoque_atual)
                            VALUES (?, ?, ?, ?)
                            ON CONFLICT(codigo_barras) DO UPDATE SET
                            estoque_atual = estoque_atual + excluded.estoque_atual,
                            preco_venda = excluded.preco_venda,
                            nome = excluded.nome
                        """, (c_barras.strip(), c_nome.strip(), c_preco, c_qtd))
                        conn.commit()
                        conn.close()
                        st.success(f"📦 Lote de '{c_nome}' integrado ao Almoxarifado!")
                        st.rerun()
                    else:
                        st.error("⚠️ Preencha todos os campos corretamente antes de salvar.")

    with col_alm2:
        with st.expander("🚨 Alertas de Estoque Crítico (Mínimo)", expanded=True):
            conn = sqlite3.connect(DB_NAME)
            df_critico = pd.read_sql_query("""
                SELECT codigo_barras AS [Código], 
                       nome AS [Produto], 
                       estoque_atual AS [Qtd Atual], 
                       estoque_minimo AS [Qtd Mínima] 
                FROM produtos 
                WHERE estoque_atual <= estoque_minimo
            """, conn)
            conn.close()
            
            if not df_critico.empty:
                st.warning("Os seguintes produtos precisam de reposição urgente:")
                st.dataframe(df_critico, use_container_width=True, hide_index=True)
            else:
                st.success("✅ Todos os produtos estão com níveis de estoque seguros!")

# ==============================================================================
# MÓDULO 3: CADASTROS (CLIENTES E EQUIPE)
# ==============================================================================
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
                if cl_nome.strip() and cl_cpf.strip():
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    try:
                        cursor.execute(
                            "INSERT INTO clientes (nome, cpf, telefone) VALUES (?, ?, ?)", 
                            (cl_nome.strip(), cl_cpf.strip(), cl_tel.strip())
                        )
                        conn.commit()
                        st.success(f"🎉 Cliente '{cl_nome}' cadastrado com sucesso!")
                    except sqlite3.IntegrityError:
                        st.error("❌ Erro: Este CPF já está cadastrado no sistema.")
                    finally:
                        conn.close()
                else:
                    st.error("⚠️ Nome e CPF são obrigatórios.")
                    
    with tab_funcionarios:
        st.subheader("Controle de Credenciais de Acesso")
        with st.form("form_func"):
            f_nome = st.text_input("Nome do Colaborador")
            f_user = st.text_input("Usuário para Login")
            f_senha = st.text_input("Senha de Acesso", type="password")
            f_cargo = st.selectbox("Cargo Operacional", ["Operador de Caixa", "Gerente", "Almoxarife"])
            btn_func = st.form_submit_button("Salvar Novo Funcionário")
            
            if btn_func:
                if f_nome.strip() and f_user.strip() and f_senha.strip():
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    try:
                        cursor.execute(
                            "INSERT INTO funcionarios (nome, usuario, senha, cargo) VALUES (?, ?, ?, ?)", 
                            (f_nome.strip(), f_user.strip(), f_senha.strip(), f_cargo)
                        )
                        conn.commit()
                        st.success(f"🔐 Credenciais criadas para {f_nome} ({f_cargo})!")
                    except sqlite3.IntegrityError:
                        st.error("❌ Erro: Este nome de usuário já está em uso.")
                    finally:
                        conn.close()
                else:
                    st.error("⚠️ Todos os campos de credenciais são obrigatórios.")

# ==============================================================================
# MÓDULO 4: RELATÓRIOS DE VENDAS COM GRÁFICO
# ==============================================================================
elif menu == "📊 Relatórios de Vendas":
    st.header("Painel Gerencial - Visualização de Desempenho")
    
    conn = sqlite3.connect(DB_NAME)
    df_faturamento = pd.read_sql_query("""
        SELECT SUBSTR(data_hora, 1, 10) AS [Data], 
               SUM(total) AS [Total Faturado (R$)] 
        FROM vendas 
        GROUP BY [Data] 
        ORDER BY [Data] ASC
    """, conn)
    conn.close()
    
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        total_acumulado = df_faturamento["Total Faturado (R$)"].sum() if not df_faturamento.empty else 0.0
        st.metric(label="Faturamento Total Acumulado", value=f"R$ {total_acumulado:.2f}")
    with col_m2:
        total_dias = len(df_faturamento)
        st.metric(label="Dias Operacionais Registrados", value=total_dias)
        
    st.markdown("---")
    
    st.subheader("📈 Evolução do Faturamento Diário")
    if not df_faturamento.empty:
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
               total AS [Total Pago (R$)], 
               forma_pagamento AS [Formas de Pagto] 
        FROM vendas 
        ORDER BY id DESC
    """, conn)
    conn.close()
    
    if not df_vendas_todas.empty:
        st.dataframe(df_vendas_todas, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma venda realizada até o momento.")
