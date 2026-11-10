import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os

# =========================================================================
# 1. FUNÇÃO DA TELA FLUTUANTE (Deve ficar aqui em cima, colada na borda esquerda)
# =========================================================================
@st.dialog("🧾 Venda Concluída - Cupom Fiscal")
def abrir_popup_cupom(venda_id, subtotal, desconto, total, formas_texto):
    st.markdown("<h3 style='text-align: center; color: #ff69b4;'>🍭 DOCE VIDA 🍭</h3>", unsafe_allow_html=True)
    st.markdown(f"**Cupom Nº:** `{venda_id}` | **Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    st.markdown("---")
    
    st.write("**Itens Processados:**")
    for item in st.session_state.carrinho_novo:
        st.write(f"▪️ {item['Quantidade']}x {item['Descrição do Produto']} ➔ R$ {item['Valor Total']:.2f}")
        
    st.markdown("---")
    st.write(f"**Subtotal Bruto:** R$ {subtotal:.2f}")
    st.write(f"**Descontos Totais:** R$ {desconto:.2f}")
    st.markdown(f"### **Valor Pago: R$ {total:.2f}**")
    st.caption(f"**Tipo de Recebimento:** {formas_texto}")
    st.markdown("---")
    
    if st.button("Fechar e Iniciar Nova Venda", use_container_width=True):
        st.session_state.carrinho_novo = []
        st.rerun()

# =========================================================================
# O resto do seu código (Menus, Login, etc.) continua aqui para baixo...
# =========================================================================


# ==============================================================================
# CONFIGURAÇÃO UNIFICADA DO BANCO DE DADOS
# ==============================================================================
import os
import sqlite3

# --- AJUSTE DE PASTAS UNIFICADO: DOCE VIDA ---
if not os.path.exists("banco_doce_vida"):
    os.makedirs("banco_doce_vida")

# O banco de dados agora fica salvo de forma personalizada dentro da pasta da loja
DB_NAME = os.path.join("banco_doce_vida", "doce_vida_sistema.db")


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

# --- TELA DE LOGIN CORRIGIDA ---
if not st.session_state.autenticado:
    # Nome oficial da loja centralizado no topo do painel de login
    st.markdown("<h2 style='text-align: center; color: #ff69b4; font-family: \"Comic Sans MS\", cursive;'>🍭 Doce Vida - SweetManager Pro</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray; margin-top: -15px;'>Painel Restrito de Acesso</p>", unsafe_allow_html=True)
    
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
                    st.success(f"Bem-vindo à Doce Vida, {user_data[0]}!")
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

# ==================== MÓDULO 1: PDV (ESTILO DOCE VIDA PRO) ====================
if menu == "🛒 Frente de Caixa (PDV)":
    # -------------------------------------------------------------------------
    # 1. BLINDAGEM DO BANCO DE DADOS DA DOCE VIDA
    # -------------------------------------------------------------------------
    PASTA_BANCO = "banco_doce_vida"
    if not os.path.exists(PASTA_BANCO):
        os.makedirs(PASTA_BANCO, exist_ok=True)
    DB_NAME = os.path.abspath(os.path.join(PASTA_BANCO, "doce_vida_sistema.db"))
    
    # Inicializa as tabelas físicas para garantir que o arquivo .db exista e não cause erro
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_barras TEXT UNIQUE,
        nome TEXT NOT NULL,
        preco_venda REAL NOT NULL,
        estoque_atual INTEGER DEFAULT 0
    )""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vendas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_hora TEXT NOT NULL,
        subtotal REAL NOT NULL,
        desconto_total REAL NOT NULL,
        total REAL NOT NULL,
        forma_pagamento TEXT
    )""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS itens_venda (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venda_id INTEGER,
        produto_id INTEGER,
        quantidade REAL,
        valor_unitario REAL,
        desconto_item REAL,
        subtotal REAL
    )""")
    conn.commit()
    conn.close()

    # Inicializa o carrinho temporário caso esteja vazio
    if "carrinho_novo" not in st.session_state:
        st.session_state.carrinho_novo = []

    st.markdown("<h1 style='text-align: center; color: #ff69b4; font-family: \"Comic Sans MS\", cursive;'>🍭 Doce Vida - Frente de Caixa</h1>", unsafe_allow_html=True)
    
    # Layout em colunas do Caixa Eletrônico
    col_principal, col_botoes = st.columns([3.2, 1.0])
    
    with col_principal:
        # Monitor PDV: Mostra o status do caixa ou o último doce registrado
        if st.session_state.carrinho_novo:
            ultimo_doce = st.session_state.carrinho_novo[-1]["Descrição do Produto"]
            st.markdown(f"<div style='background-color:#ebf5fb; padding:15px; border-radius:8px; text-align:center; font-weight:bold; font-size:26px; border:2px solid #3498db; margin-bottom:15px; color:#2980b9;'>🛒 INSERIDO: {ultimo_doce.upper()}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='background-color:#f5f5f5; padding:15px; border-radius:8px; text-align:center; font-weight:bold; font-size:24px; border:1px solid #ccc; margin-bottom:15px; color:#7f8c8d;'>🚫 CAIXA LIVRE - AGUARDANDO PRODUTOS</div>", unsafe_allow_html=True)
        
        # Puxa os produtos cadastrados para evitar que a tela fique em branco
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT codigo_barras, nome, preco_venda FROM produtos")
        lista_produtos = cursor.fetchall()
        conn.close()

        # 🛑 SOLUÇÃO SE O ALMOXARIFADO ESTIVER ZERADO
        if not lista_produtos:
            st.warning("⚠️ O Almoxarifado está completamente vazio! Cadastre produtos ou clique abaixo para injetar doces de teste no caixa.")
            if st.button("✨ Injetar Doces de Teste (Brigadeiro e Bolo)"):
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.executemany(
                    "INSERT OR IGNORE INTO produtos (codigo_barras, nome, preco_venda, estoque_atual) VALUES (?, ?, ?, ?)",
                    [("78910001", "Brigadeiro Tradicional Doce Vida", 4.50, 50),
                     ("78910002", "Bolo Pote Cenoura e Chocolate", 9.00, 20)]
                )
                conn.commit()
                conn.close()
                st.success("Doces injetados! Sistema recarregando...")
                st.rerun()
            opcoes_produtos = ["Nenhum produto cadastrado"]
        else:
            opcoes_produtos = ["Selecione ou digite o código/nome..."] + [
                f"{p[0]} - {p[1]} (R$ {p[2]:.2f})" for p in lista_produtos
            ]

        # Campo de Inserção por Código de Barras / Nome
        with st.form("entrada_produto_pdv", clear_on_submit=True):
            st.markdown("**🔍 Leitura de Itens**")
            col_busca1, col_busca2, col_busca3 = st.columns([2, 1, 1])
            with col_busca1:
                input_produto = st.selectbox("Buscar Produto:", options=opcoes_produtos)
            with col_busca2:
                qtd_item = st.number_input("QUANTIDADE", min_value=1, value=1, step=1)
            with col_busca3:
                desconto_item = st.number_input("DESC. ITEM (R$)", min_value=0.0, value=0.0, step=0.5)
            
            btn_lancar = st.form_submit_button("➕ LANÇAR NO CUPOM (ENTER)", use_container_width=True)

        # Validação e processamento do lançamento no carrinho
        if btn_lancar and input_produto != "Selecione ou digite o código/nome..." and input_produto != "Nenhum produto cadastrado":
            cod_barras_extraido = input_produto.split(" - ")[0]
            
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT id, codigo_barras, nome, preco_venda, estoque_atual FROM produtos WHERE codigo_barras = ?", (cod_barras_extraido,))
            prod_achado = cursor.fetchone()
            conn.close()
            
            if prod_achado:
                if prod_achado[4] >= qtd_item:
                    p_id = prod_achado[0]
                    v_unit = prod_achado[3]
                    v_tot = max(0.0, (v_unit * qtd_item) - desconto_item)
                    
                    st.session_state.carrinho_novo.append({
                        "Seq": len(st.session_state.carrinho_novo) + 1,
                        "id": p_id,
                        "Cód. Produto": prod_achado[1],
                        "Descrição do Produto": prod_achado[2],
                        "Quantidade": qtd_item,
                        "Valor Unitário": v_unit,
                        "Valor Desconto": desconto_item,
                        "Valor Total": v_tot
                    })
                    st.toast(f"🍭 {prod_achado[2]} adicionado!", icon="✅")
                    st.rerun()
                else:
                    st.warning(f"Estoque insuficiente! Disponível: {prod_achado[4]}")
            else:
                st.error("Produto não localizado.")

        # Grid central com o cupom atual de mercadorias
        st.write("### Itens Lançados")
        if st.session_state.carrinho_novo:
            df_cart = pd.DataFrame(st.session_state.carrinho_novo)
            if "id" in df_cart.columns:
                df_cart = df_cart.drop(columns=["id"])
            st.dataframe(df_cart, use_container_width=True, hide_index=True)
        else:
            st.info("Aguardando leitura de código de barras ou seleção de mercadorias...")

        # Área de Cálculos do Rodapé
        subtotal = sum(item["Quantidade"] * item["Valor Unitário"] for item in st.session_state.carrinho_novo)
        descontos_itens = sum(item["Valor Desconto"] for item in st.session_state.carrinho_novo)
        
        st.markdown("<hr style='border:1px dashed #ccc;'>", unsafe_allow_html=True)
        col_calc1, col_calc2, col_calc3 = st.columns(3)
        with col_calc1:
            st.metric("SUBTOTAL BRUTO", f"R$ {subtotal:.2f}")
        with col_calc2:
            desc_total_venda = st.number_input("DESCONTO COMPRA (R$)", min_value=0.0, value=0.0, step=1.0)
        with col_calc3:
            total_compra = max(0.0, subtotal - descontos_itens - desc_total_venda)
            st.metric("VALOR TOTAL DA COMPRA", f"R$ {total_compra:.2f}")

        # Pagamentos Múltiplos
        st.markdown("### 💳 1.2 Formas de Pagamento")
        col_p1, col_p2, col_p3, col_p4 = st.columns(4)
        with col_p1:
            val_dinheiro = st.number_input("Dinheiro R$", min_value=0.0, value=0.0)
        with col_p2:
            val_pix = st.number_input("Pix R$", min_value=0.0, value=0.0)
        with col_p3:
            val_debito = st.number_input("Cartão Débito R$", min_value=0.0, value=0.0)
        with col_p4:
            val_credito = st.number_input("Cartão Crédito R$", min_value=0.0, value=0.0)

        total_recebido = val_dinheiro + val_pix + val_debito + val_credito
        valor_restante = max(0.0, total_compra - total_recebido)
        troco = max(0.0, total_recebido - total_compra)

        # Indicadores Dinâmicos de Caixa
        st.markdown("#### 📊 Resumo Financeiro")
        col_res1, col_res2, col_res3 = st.columns(3)
        with col_res1:
            st.markdown(f"<div style='background-color:#f4f6f7; padding:10px; border-radius:5px; font-weight:bold;'>Recebido: R$ {total_recebido:.2f}</div>", unsafe_allow_html=True)
        with col_res2:
            if valor_restante > 0:
                st.markdown(f"<div style='background-color:#fadbd8; padding:10px; border-radius:5px; color:#922b21; font-weight:bold; text-align:center;'>Falta: R$ {valor_restante:.2f}</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div style='background-color:#d4efdf; padding:10px; border-radius:5px; color:#196f3d; font-weight:bold; text-align:center;'>✓ PAGO INTEGRAL</div>", unsafe_allow_html=True)
        with col_res3:
            st.markdown(f"<div style='background-color:#d4e6f1; padding:10px; border-radius:5px; color:#1a5276; font-weight:bold; text-align:center;'>Troco: R$ {troco:.2f}</div>", unsafe_allow_html=True)

    with col_botoes:
        st.markdown("<div style='background-color:#2c3e50; padding:12px; border-radius:6px; text-align:center; font-weight:bold; color:white;'>PAINEL DE COMANDOS</div>", unsafe_allow_html=True)
        st.write("")

        btn_finalizar = st.button("🛟 F6 - FINALIZAR VENDA", type="primary", use_container_width=True, disabled=(total_compra == 0 or valor_restante > 0))
        st.write("")

        st.markdown("", unsafe_allow_html=True)
        idx_cancelar = st.number_input("Nº Item", min_value=1, max_value=max(len(st.session_state.carrinho_novo), 1), step=1)
        btn_cancelar_item = st.button("⚠️ F4 - CANCELAR ITEM", type="secondary", use_container_width=True, disabled=(len(st.session_state.carrinho_novo) == 0))
        st.markdown("", unsafe_allow_html=True)
        st.write("")

        btn_cancelar_venda = st.button("❌ F7 - CANCELAR VENDA", type="secondary", use_container_width=True, disabled=(len(st.session_state.carrinho_novo) == 0))

        # Ação: Remover item específico do cupom
        if btn_cancelar_item:
            st.session_state.carrinho_novo = [item for item in st.session_state.carrinho_novo if item["Seq"] != idx_cancelar]
            for idx, item in enumerate(st.session_state.carrinho_novo):
                item["Seq"] = idx + 1
            st.toast("Item cancelado com sucesso!", icon="⚠️")
            st.rerun()

        # Ação: Abortar e limpar a operação completa
        if btn_cancelar_venda:
            st.session_state.carrinho_novo = []
            st.toast("Venda cancelada com sucesso!", icon="❌")
            st.rerun()

        # Lógica de gravação completa e persistência garantida no arquivo .db
        if btn_finalizar:
            try:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                
                # 1. Abate automático da saída física dos doces do estoque
                for item in st.session_state.carrinho_novo:
                    cursor.execute("UPDATE produtos SET estoque_atual = estoque_atual - ? WHERE codigo_barras = ?", (item["Quantidade"], item["Cód. Produto"]))
                
                # 2. Transforma os recebimentos múltiplos em string informativa
                formas_usadas = []
                if val_dinheiro > 0: formas_usadas.append(f"Dinheiro (R$ {val_dinheiro:.2f})")
                if val_pix > 0: formas_usadas.append(f"Pix (R$ {val_pix:.2f})")
                if val_debito > 0: formas_usadas.append(f"Débito (R$ {val_debito:.2f})")
                if val_credito > 0: formas_usadas.append(f"Crédito (R$ {val_credito:.2f})")
                str_pagamento = " + ".join(formas_usadas)
                
                # 3. Insere o resumo master no cabeçalho de vendas
                desc_total_aplicado = descontos_itens + desc_total_venda
                cursor.execute("INSERT INTO vendas (data_hora, subtotal, desconto_total, total, forma_pagamento) VALUES (?, ?, ?, ?, ?)",
                               (datetime.now().strftime("%d/%m/%Y %H:%M"), subtotal, desc_total_aplicado, total_compra, str_pagamento))
                
                venda_id = cursor.lastrowid
                
                # 4. Grava cada item da venda individualmente associado à chave primária master
                for item in st.session_state.carrinho_novo:
                    cursor.execute("""
                        INSERT INTO itens_venda (venda_id, produto_id, quantidade, valor_unitario, desconto_item, subtotal)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (venda_id, item["id"], item["Quantidade"], item["Valor Unitário"], item["Valor Desconto"], item["Valor Total"]))
                
                # SALVAMENTO PERMANENTE NO BANCO DE DADOS
                conn.commit()
                conn.close()
                
                # Dispara a tela flutuante para emissão do cupom
                abrir_popup_cupom(venda_id, subtotal, desc_total_aplicado, total_compra, str_pagamento)
                
            except sqlite3.Error as e:
                st.error(f"Erro ao salvar dados no SQLite: {e}")

    # -------------------------------------------------------------------------
    # 3. RENDERIZAÇÃO DOS LOGOS DA DOCE VIDA E DO DESENVOLVEDOR NO SIDEBAR
    # -------------------------------------------------------------------------
    with st.sidebar:
        # Posição do Logo da Loja (Topo da Barra)
        st.markdown("---")
        CADASTRADO_LOGO_LOJA = os.path.join("logo da empresa", "logo_empresa.png")
        if os.path.exists(CADASTRADO_LOGO_LOJA):
            st.image(CADASTRADO_LOGO_LOJA, use_container_width=True)
        else:
            st.markdown("<h3 style='text-align: center; color: #ff69b4;'>🍭 DOCE VIDA</h3>", unsafe_allow_html=True)
            
        # Posição do Logo do Desenvolvedor (Fundo da Barra)
        st.markdown("<br><br><br><br><br>", unsafe_allow_html=True)
        st.markdown("---")
        CADASTRADO_LOGO_DEV = os.path.join("desenvolvedor", "logo_desenvolvedor.png")
        if os.path.exists(CADASTRADO_LOGO_DEV):
            st.image(CADASTRADO_LOGO_DEV, width=140)
        else:
            st.caption("💻 TechFlow Systems - Desenvolvedor")
    # -------------------------------------------------------------------------
    # PAINEL LATERAL DIREITO: Painel de Ações e Comandos Operacionais
    # -------------------------------------------------------------------------
    with col_botoes:
        st.markdown("<div style='background-color:#2c3e50; padding:12px; border-radius:6px; text-align:center; font-weight:bold; color:white;'>PAINEL OPERACIONAL</div>", unsafe_allow_html=True)
        st.write("")
        
        # Botão Master - Concluir Transação (Desabilitado se faltar dinheiro)
        btn_finalizar = st.button("🛟 F6 - FINALIZAR VENDA", type="primary", use_container_width=True, disabled=(total_compra == 0 or valor_restante > 0), key="pdv_btn_finalizar_novo")
        st.write("")
        
        # Caixa de Cancelamento Individual
        st.markdown("<div style='background-color:#f8f9f9; padding:10px; border:1px solid #d5dbdb; border-radius:6px;'>", unsafe_allow_html=True)
        st.markdown("", unsafe_allow_html=True)
        idx_cancelar = st.number_input("Nº Item", min_value=1, max_value=max(len(st.session_state.carrinho_novo), 1), step=1)
        
        # CORREÇÃO DA LINHA 462: Adicionada a chave única 'key'
        btn_cancelar_item = st.button("⚠️ F4 - CANCELAR ITEM", type="secondary", use_container_width=True, disabled=(len(st.session_state.carrinho_novo) == 0), key="btn_cancelar_item_unico")
        st.markdown("", unsafe_allow_html=True)
        st.write("")

        # PREVENÇÃO PARA O PRÓXIMO BOTÃO: Adicionada a chave única 'key' para evitar o erro no F7
        btn_cancelar_venda = st.button("❌ F7 - CANCELAR VENDA", type="secondary", use_container_width=True, disabled=(len(st.session_state.carrinho_novo) == 0), key="btn_cancelar_venda_unico")


        # Ação: Remover item específico
        if btn_cancelar_item:
            st.session_state.carrinho_novo = [item for item in st.session_state.carrinho_novo if item["Seq"] != idx_cancelar]
            for idx, item in enumerate(st.session_state.carrinho_novo):
                item["Seq"] = idx + 1
            st.toast("Item removido da lista!", icon="⚠️")
            st.rerun()

        # Ação: Abortar cupom inteiro
        if btn_cancelar_venda:
            st.session_state.carrinho_novo = []
            st.toast("Venda abortada com sucesso!", icon="❌")
            st.rerun()

    # -------------------------------------------------------------------------
    # PERSISTÊNCIA COMPLETA E DISPARO DA JANELA FLUTUANTE
    # -------------------------------------------------------------------------
    if btn_finalizar:
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()

            # Garante de forma blindada que as tabelas existem na gravação
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS vendas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_hora TEXT NOT NULL,
                subtotal REAL NOT NULL,
                desconto_total REAL NOT NULL,
                total REAL NOT NULL,
                forma_pagamento TEXT
            )""")

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS itens_venda (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                venda_id INTEGER,
                produto_id INTEGER,
                quantidade REAL,
                valor_unitario REAL,
                desconto_item REAL,
                subtotal REAL
            )""")

            # 1. Abate as saídas do estoque no almoxarifado
            for item in st.session_state.carrinho_novo:
                cursor.execute("UPDATE produtos SET estoque_atual = estoque_atual - ? WHERE codigo_barras = ?", (item["Quantidade"], item["Cód. Produto"]))

            # 2. Consolida strings informativas dos recebimentos múltiplos
            formas_usadas = []
            if val_dinheiro > 0: formas_usadas.append(f"Dinheiro (R$ {val_dinheiro:.2f})")
            if val_pix > 0: formas_usadas.append(f"Pix (R$ {val_pix:.2f})")
            if val_debito > 0: formas_usadas.append(f"Débito (R$ {val_debito:.2f})")
            if val_credito > 0: formas_usadas.append(f"Crédito (R$ {val_credito:.2f})")
            str_pagamento = " + ".join(formas_usadas)

            # 3. Registra cabeçalho da venda
            desc_total_aplicado = descontos_itens + desc_total_venda
            cursor.execute("INSERT INTO vendas (data_hora, subtotal, desconto_total, total, forma_pagamento) VALUES (?, ?, ?, ?, ?)",
                           (datetime.now().strftime("%d/%m/%Y %H:%M"), subtotal, desc_total_aplicado, total_compra, str_pagamento))

            venda_id = cursor.lastrowid

            # 4. Registra cada item vinculado ao ID master gerado
            for item in st.session_state.carrinho_novo:
                cursor.execute("""
                INSERT INTO itens_venda (venda_id, produto_id, quantidade, valor_unitario, desconto_item, subtotal)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (venda_id, item["id"], item["Quantidade"], item["Valor Unitário"], item["Valor Desconto"], item["Valor Total"]))

            # GRAVAÇÃO FÍSICA IMEDIATA NO ARQUIVO .DB
            conn.commit()
            conn.close()

            # Dispara a janela flutuante nativa passando as informações processadas
            abrir_popup_cupom(venda_id, subtotal, desc_total_aplicado, total_compra, str_pagamento)

        except sqlite3.Error as e:
            st.error(f"Erro Crítico de persistência no Banco SQLite: {e}")

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

