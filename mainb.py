import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os

# =========================================================================
# 1. CONFIGURAÇÃO UNIFICADA DO BANCO DE DADOS (DOCE VIDA)
# =========================================================================
PASTA_BANCO = "banco_doce_vida"
if not os.path.exists(PASTA_BANCO):
    os.makedirs(PASTA_BANCO, exist_ok=True)

DB_NAME = os.path.abspath(os.path.join(PASTA_BANCO, "doce_vida_sistema.db"))

def inicializar_banco_doce_vida():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Tabela de Funcionários / Acesso
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS funcionarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        usuario TEXT UNIQUE NOT NULL,
        senha TEXT NOT NULL,
        cargo TEXT NOT NULL
    )""")
    
    # Tabela de Clientes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        cpf TEXT UNIQUE,
        telefone TEXT
    )""")
    
    # Tabela do Almoxarifado (Produtos)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_barras TEXT UNIQUE,
        nome TEXT NOT NULL,
        preco_venda REAL NOT NULL,
        estoque_atual INTEGER DEFAULT 0
    )""")
    
    # Tabela de Histórico de Vendas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vendas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_hora TEXT NOT NULL,
        subtotal REAL NOT NULL,
        desconto_total REAL NOT NULL,
        total REAL NOT NULL,
        forma_pagamento TEXT
    )""")

    # Tabela de Itens Detalhados da Venda
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS itens_venda (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venda_id INTEGER,
        produto_id INTEGER,
        quantidade REAL,
        valor_unitario REAL,
        desconto_item REAL,
        subtotal REAL,
        FOREIGN KEY(venda_id) REFERENCES vendas(id)
    )""")

    # Criação do usuário administrador padrão se a tabela estiver vazia
    cursor.execute("SELECT COUNT(*) FROM funcionarios")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO funcionarios (nome, usuario, senha, cargo) VALUES (?, ?, ?, ?)",
                       ("Gerente Doces", "admin", "admin123", "Gerente"))
        
    conn.commit()
    conn.close()

# Inicializa as tabelas físicas do sistema
inicializar_banco_doce_vida()

# =========================================================================
# 2. DEFINIÇÃO DA TELA FLUTUANTE (POPUP MODAL DO CUPOM)
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
# 3. GERENCIAMENTO DE ESTADO E AUTENTICAÇÃO DO USUÁRIO
# =========================================================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if "carrinho_novo" not in st.session_state:
    st.session_state.carrinho_novo = []

# --- TELA DE LOGIN PROTEGIDA E FORMATADA ---
if not st.session_state.autenticado:
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

# =========================================================================
# 4. MENU LATERAL E RENDERIZAÇÃO DE LOGOS LOCAIS
# =========================================================================
with st.sidebar:
    # Logo da Empresa (Topo)
    CADASTRADO_LOGO_LOJA = os.path.join("logo da empresa", "logo_empresa.png")
    if os.path.exists(CADASTRADO_LOGO_LOJA):
        st.image(CADASTRADO_LOGO_LOJA, use_container_width=True)
    else:
        st.markdown("<h2 style='text-align: center; color: #ff69b4;'>🍭 DOCE VIDA</h2>", unsafe_allow_html=True)
        
    st.write(f"👤 **{st.session_state.user_nome}** ({st.session_state.user_cargo})")
    st.markdown("---")
    
    # Navegação do Menu
    menu = st.radio("Navegação do Sistema:", ["🛒 Frente de Caixa (PDV)", "📦 Almoxarifado"])
    
    # Logo do Desenvolvedor (Rodapé)
    st.markdown("<br><br><br><br><br><br><br><br>", unsafe_allow_html=True)
    st.markdown("---")
    CADASTRADO_LOGO_DEV = os.path.join("desenvolvedor", "logo_desenvolvedor.png")
    if os.path.exists(CADASTRADO_LOGO_DEV):
        st.image(CADASTRADO_LOGO_DEV, width=140)
    else:
        st.caption("💻 TechFlow Systems - Desenvolvedor")

# =========================================================================
# 5. EXECUÇÃO DOS MÓDULOS SELECIONADOS
# =========================================================================

# -------------------------------------------------------------------------
# MÓDULO: FRENTE DE CAIXA (PDV)
# -------------------------------------------------------------------------
if menu == "🛒 Frente de Caixa (PDV)":
    st.markdown("<h1 style='text-align: center; color: #ff69b4; font-family: \"Comic Sans MS\", cursive;'>🍭 Doce Vida - Frente de Caixa</h1>", unsafe_allow_html=True)
    
    col_principal, col_botoes = st.columns([3.2, 1.0])
    
    with col_principal:
        # Monitor Virtual do Operador
        if st.session_state.carrinho_novo:
            ultimo_doce = st.session_state.carrinho_novo[-1]["Descrição do Produto"]
            st.markdown(f"<div style='background-color:#ebf5fb; padding:15px; border-radius:8px; text-align:center; font-weight:bold; font-size:26px; border:2px solid #3498db; margin-bottom:15px; color:#2980b9;'>🛒 INSERIDO: {ultimo_doce.upper()}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='background-color:#f5f5f5; padding:15px; border-radius:8px; text-align:center; font-weight:bold; font-size:24px; border:1px solid #ccc; margin-bottom:15px; color:#7f8c8d;'>🚫 CAIXA LIVRE - AGUARDANDO PRODUTOS</div>", unsafe_allow_html=True)
        
        # Puxa itens para a listagem
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT codigo_barras, nome, preco_venda FROM produtos")
        lista_produtos = cursor.fetchall()
        conn.close()

        if not lista_produtos:
            st.warning("⚠️ O Almoxarifado está vazio! Use o botão abaixo para injetar produtos de teste rapidamente.")
            if st.button("✨ Injetar Doces de Teste (Brigadeiro e Bolo)"):
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.executemany(
                    "INSERT OR IGNORE INTO produtos (codigo_barras, nome, preco_venda, estoque_atual) VALUES (?, ?, ?, ?)",
                    [("78910001", "Brigadeiro Tradicional", 4.50, 60),
                     ("78910002", "Bolo Pote Cenoura", 9.00, 30)]
                )
                conn.commit()
                conn.close()
                st.success("Doces adicionados com sucesso!")
                st.rerun()
            opcoes_produtos = ["Nenhum produto cadastrado"]
        else:
            opcoes_produtos = ["Selecione ou digite o código/nome..."] + [
                f"{p[0]} - {p[1]} (R$ {p[2]:.2f})" for p in lista_produtos
            ]

        # Formulário de entrada de mercadoria
        with st.form("entrada_produto_pdv", clear_on_submit=True):
            st.markdown("**🔍 Leitura de Itens (Código de Barras ou Nome)**")
            col_busca1, col_busca2, col_busca3 = st.columns([2, 1, 1])
            with col_busca1:
                input_produto = st.selectbox("Buscar Produto:", options=opcoes_produtos)
                qtd_item = st.number_input("QUANTIDADE", min_value=1, value=1, step=1, key="pdv_qtd_input")
            with col_busca3:
                desconto_item = st.number_input("DESC. ITEM (R$)", min_value=0.0, value=0.0, step=0.5, key="pdv_desc_item_input")
            
            btn_lancar = st.form_submit_button("➕ LANÇAR NO CUPOM (ENTER)", use_container_width=True)

        if btn_lancar and input_produto not in ["Selecione ou digite o código/nome...", "Nenhum produto cadastrado"]:
            cod_barras_extraido = input_produto.split(" - ")[0]

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT id, codigo_barras, nome, preco_venda, estoque_atual FROM produtos WHERE codigo_barras = ?", (cod_barras_extraido,))
            prod_achado = cursor.fetchone()
            conn.close()

            if prod_achado:
                if prod_achado[4] >= qtd_item:
                    v_tot = max(0.0, (prod_achado[3] * qtd_item) - desconto_item)
                    st.session_state.carrinho_novo.append({
                        "Seq": len(st.session_state.carrinho_novo) + 1,
                        "id": prod_achado[0],
                        "Cód. Produto": prod_achado[1],
                        "Descrição do Produto": prod_achado[2],
                        "Quantidade": qtd_item,
                        "Valor Unitário": prod_achado[3],
                        "Valor Desconto": desconto_item,
                        "Valor Total": v_tot
                    })
                    st.toast(f"🍭 {prod_achado[2]} adicionado!", icon="✅")
                    st.rerun()
                else:
                    st.warning(f"Estoque insuficiente! Disponível: {prod_achado[4]}")

        # Visualização da Tabela de Itens Lançados
        st.write("### 🧾 Itens no Cupom Atual")
        if st.session_state.carrinho_novo:
            df_cart = pd.DataFrame(st.session_state.carrinho_novo)
            st.dataframe(df_cart.drop(columns=["id"]), use_container_width=True, hide_index=True)
        else:
            st.info("Aguardando leitura de código de barras ou seleção de mercadorias...")
        # Cálculos de Fechamento do Caixa
        subtotal = sum(item["Quantidade"] * item["Valor Unitário"] for item in st.session_state.carrinho_novo)
        descontos_itens = sum(item["Valor Desconto"] for item in st.session_state.carrinho_novo)

        st.markdown("", unsafe_allow_html=True)
        col_calc1, col_calc2, col_calc3 = st.columns(3)
        with col_calc1:
            st.metric("SUBTOTAL BRUTO", f"R$ {subtotal:.2f}")
        with col_calc2:
            desc_total_venda = st.number_input("DESCONTO COMPRA (R$)", min_value=0.0, value=0.0, step=1.0, key="pdv_desc_total_venda")
        with col_calc3:
            total_compra = max(0.0, subtotal - descontos_itens - desc_total_venda)
            st.metric("VALOR TOTAL DA COMPRA", f"R$ {total_compra:.2f}")

        # Formas de Pagamento Multi-Modal
        st.markdown("### 💳 1.2 Formas de Pagamento Dividido")
        col_p1, col_p2, col_p3, col_p4 = st.columns(4)
        with col_p1:
            val_dinheiro = st.number_input("Dinheiro R$", min_value=0.0, value=0.0, key="din_key")
        with col_p2:
            val_pix = st.number_input("Pix R$", min_value=0.0, value=0.0, key="pix_key")
        with col_p3:
            val_debito = st.number_input("Cartão Débito R$", min_value=0.0, value=0.0, key="deb_key")
        with col_p4:
            val_credito = st.number_input("Cartão Crédito R$", min_value=0.0, value=0.0, key="cred_key")

        total_recebido = val_dinheiro + val_pix + val_debito + val_credito
        valor_restante = max(0.0, total_compra - total_recebido)
        troco = max(0.0, total_recebido - total_compra)

        st.markdown("#### 📊 Resumo Financeiro")
        col_res1, col_res2, col_res3 = st.columns(3)
        with col_res1:
            st.markdown(f"**Recebido:** R$ {total_recebido:.2f}")
        with col_res2:
            if valor_restante > 0:
                st.markdown(f"<span style='color:red; font-weight:bold;'>Falta: R$ {valor_restante:.2f}</span>", unsafe_allow_html=True)
            else:
                st.markdown("<span style='color:green; font-weight:bold;'>✓ PAGO INTEGRAL</span>", unsafe_allow_html=True)
        with col_res3:
            st.markdown(f"**Troco:** R$ {troco:.2f}")
    with col_botoes:
        st.markdown("<div style='background-color:#2c3e50; padding:12px; border-radius:6px; text-align:center; font-weight:bold; color:white;'>PAINEL DE COMANDOS</div>", unsafe_allow_html=True)
        st.write("")

        btn_finalizar = st.button("🛟 F6 - FINALIZAR VENDA", type="primary", use_container_width=True, disabled=(total_compra == 0 or valor_restante > 0), key="btn_fin_pdv")
        st.write("")

        idx_cancelar = st.number_input("Nº Item", min_value=1, max_value=max(len(st.session_state.carrinho_novo), 1), step=1, key="num_canc_pdv")
        btn_cancelar_item = st.button("⚠️ F4 - CANCELAR ITEM", type="secondary", use_container_width=True, disabled=(len(st.session_state.carrinho_novo) == 0), key="btn_item_pdv")
        st.write("")

        btn_cancelar_venda = st.button("❌ F7 - CANCELAR VENDA", type="secondary", use_container_width=True, disabled=(len(st.session_state.carrinho_novo) == 0), key="btn_venda_pdv")

        if btn_cancelar_item:
            st.session_state.carrinho_novo = [item for item in st.session_state.carrinho_novo if item["Seq"] != idx_cancelar]
            for idx, item in enumerate(st.session_state.carrinho_novo):
                item["Seq"] = idx + 1
            st.toast("Item cancelado!", icon="⚠️")
            st.rerun()

        if btn_cancelar_venda:
            st.session_state.carrinho_novo = []
            st.toast("Venda cancelada!", icon="❌")
            st.rerun()

        if btn_finalizar:
            try:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()

                for item in st.session_state.carrinho_novo:
                    cursor.execute("UPDATE produtos SET estoque_atual = estoque_atual - ? WHERE codigo_barras = ?", (item["Quantidade"], item["Cód. Produto"]))

                formas_usadas = []
                if val_dinheiro > 0: formas_usadas.append(f"Dinheiro (R$ {val_dinheiro:.2f})")
                if val_pix > 0: formas_usadas.append(f"Pix (R$ {val_pix:.2f})")
                if val_debito > 0: formas_usadas.append(f"Débito (R$ {val_debito:.2f})")
                if val_credito > 0: formas_usadas.append(f"Crédito (R$ {val_credito:.2f})")
                str_pagamento = " + ".join(formas_usadas)

                desc_total_aplicado = descontos_itens + desc_total_venda
                cursor.execute("INSERT INTO vendas (data_hora, subtotal, desconto_total, total, forma_pagamento) VALUES (?, ?, ?, ?, ?)",
                               (datetime.now().strftime("%d/%m/%Y %H:%M"), subtotal, desc_total_aplicado, total_compra, str_pagamento))
                venda_id = cursor.lastrowid

                for item in st.session_state.carrinho_novo:
                    cursor.execute("""
                        INSERT INTO itens_venda (venda_id, produto_id, quantidade, valor_unitario, desconto_item, subtotal)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (venda_id, item["id"], item["Quantidade"], item["Valor Unitário"], item["Valor Desconto"], item["Valor Total"]))

                conn.commit()
                conn.close()

                abrir_popup_cupom(venda_id, subtotal, desc_total_aplicado, total_compra, str_pagamento)

            except sqlite3.Error as e:
                st.error(f"Erro ao salvar dados no SQLite: {e}")

# ==================== MÓDULO 2: ALMOXARIFADO (ESTOQUE) ====================
elif menu == "📦 Almoxarifado":
    st.markdown("<h1 style='text-align: center; color: #ff69b4; font-family: \"Comic Sans MS\", cursive;'>📦 Almoxarifado - Controle de Estoque</h1>", unsafe_allow_html=True)

    with st.expander("✨ Cadastrar Novo Doce / Produto", expanded=False):
        with st.form("cadastro_produto_almoxarifado", clear_on_submit=True):
            col_cad1, col_cad2 = st.columns(2)
            with col_cad1:
                cad_codigo = st.text_input("Código de Barras / Identificador:")
                cad_nome = st.text_input("Descrição / Nome do Doce:")
            with col_cad2:
                cad_preco = st.number_input("Preço de Venda (R$):", min_value=0.0, value=0.0, step=0.50)
                cad_estoque = st.number_input("Estoque Inicial:", min_value=0, value=10, step=1)

            btn_cadastrar_prod = st.form_submit_button("💾 Salvar no Almoxarifado", use_container_width=True)

            if btn_cadastrar_prod:
                if not cad_codigo or not cad_nome or cad_preco <= 0:
                    st.error("Preencha todos os campos regulamentares corretamente.")
                else:
                    try:
                        conn = sqlite3.connect(DB_NAME)
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO produtos (codigo_barras, nome, preco_venda, estoque_atual) VALUES (?, ?, ?, ?)",
                                       (cad_codigo.strip(), cad_nome.strip(), cad_preco, cad_estoque))
                        conn.commit()
                        conn.close()
                        st.success(f"🎉 '{cad_nome}' adicionado com sucesso!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Este Código de Barras já está cadastrado.")

    st.markdown("### 📋 Posição Atual do Estoque")
    conn = sqlite3.connect(DB_NAME)
    df_estoque = pd.read_sql_query("SELECT id, codigo_barras AS 'Código de Barras', nome AS 'Descrição', preco_venda AS 'Preço (R$)', estoque_atual AS 'Estoque Atual' FROM produtos", conn)
    conn.close()

    if df_estoque.empty:
        st.info("Almoxarifado sem mercadorias registradas.")
    else:
        itens_criticos = df_estoque[df_estoque['Estoque Atual'] <= 5]
        if not itens_criticos.empty:
            st.markdown(f"<div style='background-color:#fadbd8; padding:10px; border-radius:5px; color:#922b21; font-weight:bold;'>⚠️ ALERTA: Há {len(itens_criticos)} itens com estoque crítico (5 unidades ou menos)!</div>", unsafe_allow_html=True)

        st.dataframe(df_estoque.drop(columns=["id"]), use_container_width=True, hide_index=True)

        st.markdown("### 🔄 Entrada Rápida de Mercadoria")
        with st.form("ajuste_estoque_rapido", clear_on_submit=True):
            col_aj1, col_aj2 = st.columns(2)
            with col_aj1:
                opcoes_ajuste = [f"{row['Código de Barras']} - {row['Descrição']}" for _, row in df_estoque.iterrows()]
                prod_selecionado = st.selectbox("Escolha o Doce:", options=opcoes_ajuste)
            with col_aj2:
                qtd_adicionar = st.number_input("Quantidade a Injetar:", min_value=-100, max_value=1000, value=10, step=1)

            btn_atualizar_estoque = st.form_submit_button("⚡ Atualizar Quantidade", use_container_width=True)

            if btn_atualizar_estoque:
                cod_para_ajuste = prod_selecionado.split(" - ")[0]
                try:
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute("UPDATE produtos SET estoque_atual = estoque_atual + ? WHERE codigo_barras = ?", (qtd_adicionar, cod_para_ajuste))
                    conn.commit()
                    conn.close()
                    st.toast("Estoque ajustado com sucesso!", icon="🔄")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro: {e}")

            with col_busca2:
