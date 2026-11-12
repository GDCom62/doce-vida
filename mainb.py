import os
import sqlite3
import streamlit as st
import pandas as pd
from datetime import datetime

# Configuração da página Web do Streamlit
st.set_page_config(page_title="Dominus PDV - Gestão Integrada", page_icon="🛒", layout="wide")

# ==============================================================================
# CONFIGURAÇÃO UNIFICADA DO BANCO DE DADOS E GERADOR DE RECIBO
# ==============================================================================
if not os.path.exists("banco_dados"):
    os.makedirs("banco_dados")

DB_NAME = os.path.join("banco_dados", "estoque_loja_independente.db")

def exibir_logo_centralizado(largura=180):
    if os.path.exists("logo_empresa.png"):
        col_e, col_c, col_d = st.columns([1, 2, 1])
        with col_c:
            st.image("logo_empresa.png", width=largura)

def gerar_texto_recibo(num_cupom, data_hora, itens, subtotal, descontos, total, formas_pgto, recebido, troco):
    linhas = [
        "==========================================",
        "           DOCE VIDA PDV - RECIBO           ",
        "      COMPROVANTE NÃO FISCAL DE VENDA     ",
        "==========================================",
        f"Cupom Nº: {num_cupom:06d}   Data: {data_hora}",
        "------------------------------------------",
        "ITEM  DESCRIÇÃO                 QTD  TOTAL",
        "------------------------------------------"
    ]
    for item in itens:
        desc_curta = item["Descrição do Produto"][:24].ljust(24)
        qtd_str = str(item["Quantidade"]).rjust(3)
        tot_str = f"{item['Valor Total']:.2f}".rjust(7)
        linhas.append(f"{item['Seq']:02d}    {desc_curta} {qtd_str} {tot_str}")
        if item["Desconto Item"] > 0:
            linhas.append(f"      (Desconto no item: -R$ {item['Desconto Item']:.2f})")
            
    linhas.extend([
        "------------------------------------------",
        f"SUBTOTAL:                     R$ {subtotal:8.2f}",
        f"DESCONTOS APLICADOS:         -R$ {descontos:8.2f}",
        f"TOTAL A PAGAR:                R$ {total:8.2f}",
        "------------------------------------------",
        "FORMAS DE PAGAMENTO:",
        f"  {formas_pgto}",
        f"VALOR RECEBIDO:               R$ {recebido:8.2f}",
        f"TROCO:                        R$ {troco:8.2f}",
        "==========================================",
        "       OBRIGADO PELA PREFERÊNCIA!         ",
        "=========================================="
    ])
    return "\n".join(linhas)

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
    
    # 3. Tabela do Almoxarifado (Produtos com Produto Base + Variação)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_barras TEXT UNIQUE,
        produto_base TEXT NOT NULL,
        variacao TEXT NOT NULL,
        nome TEXT NOT NULL,
        preco_venda REAL NOT NULL,
        estoque_atual INTEGER DEFAULT 0,
        estoque_minimo INTEGER DEFAULT 5
    )""")

    # Migração automática e correção de produtos antigos (DEVE FICAR AQUI)
    cursor.execute("PRAGMA table_info(produtos)")
    colunas_existentes = [col[1] for col in cursor.fetchall()]
    
    if "produto_base" not in colunas_existentes:
        cursor.execute("ALTER TABLE produtos ADD COLUMN produto_base TEXT DEFAULT 'Geral'")
    if "variacao" not in colunas_existentes:
        cursor.execute("ALTER TABLE produtos ADD COLUMN variacao TEXT DEFAULT 'Padrão'")
        
    cursor.execute("""
        UPDATE produtos 
        SET produto_base = nome 
        WHERE produto_base IS NULL OR produto_base = '' OR produto_base = 'Geral'
    """)
    cursor.execute("""
        UPDATE produtos 
        SET variacao = 'Padrão' 
        WHERE variacao IS NULL OR variacao = ''
    """)

    # 4. Tabela de Histórico de Vendas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vendas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_hora TEXT NOT NULL,
        subtotal REAL NOT NULL,
        desconto_total REAL NOT NULL,
        total REAL NOT NULL,
        forma_pagamento TEXT
    )""")

    # Usuário padrão
    cursor.execute("SELECT COUNT(*) FROM funcionarios")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO funcionarios (nome, usuario, senha, cargo) VALUES (?, ?, ?, ?)",
            ("Administrador", "admin", "admin123", "Gerente")
        )
        
    # Produtos iniciais de exemplo com Produto Base + Variações
    cursor.execute("SELECT COUNT(*) FROM produtos")
    if cursor.fetchone()[0] == 0:
        exemplos = [
            ("78910001", "Chocolate Joaozinho", "Chocolate Branco", "Chocolate Joaozinho - Chocolate Branco", 6.50, 50),
            ("78910002", "Chocolate Joaozinho", "Chocolate com Amêndoas", "Chocolate Joaozinho - Chocolate com Amêndoas", 7.50, 40),
            ("78910003", "Chocolate Joaozinho", "Ao Leite Tradicional", "Chocolate Joaozinho - Ao Leite Tradicional", 6.00, 60),
            ("78920001", "Brigadeiro Gourmet", "Tradicional", "Brigadeiro Gourmet - Tradicional", 4.00, 100)
        ]
        cursor.executemany(
            "INSERT INTO produtos (codigo_barras, produto_base, variacao, nome, preco_venda, estoque_atual) VALUES (?, ?, ?, ?, ?, ?)",
            exemplos
        )
        
    conn.commit()
    conn.close()

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
if "ultimo_recibo" not in st.session_state:
    st.session_state.ultimo_recibo = None

# ==============================================================================
# TELA DE LOGIN COM LOGO CENTRALIZADO
# ==============================================================================
if not st.session_state.autenticado:
    exibir_logo_centralizado(largura=200)
    st.markdown("<h2 style='text-align: center;'>🛒 Doce Vida PDV - Acesso </h2>", unsafe_allow_html=True)
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
# MENU LATERAL COM LOGO CENTRALIZADO
# ==============================================================================
with st.sidebar:
    if os.path.exists("logo_empresa.png"):
        col_s1, col_s2, col_s3 = st.columns([0.5, 2, 0.5])
        with col_s2:
            st.image("logo_empresa.png", use_container_width=True)
            
    st.markdown("<h3 style='text-align: center;'>🧭 Menu Principal</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center;'>👤 <b>{st.session_state.user_nome}</b> ({st.session_state.user_cargo})</p>", unsafe_allow_html=True)
    st.markdown("---")

    menu = st.radio("Selecione o Módulo:", [
        "🛒 Frente de Caixa (PDV)", 
        "📦 Almoxarifado / Estoque", 
        "👥 Cadastros (Clientes/Equipe)",
        "📊 Relatórios de Vendas"
    ])

    st.markdown("---")
    st.markdown("### 💾 Segurança dos Dados")
    
    # 1. Botão para Baixar o Backup do Banco Atual
    if os.path.exists(DB_NAME):
        with open(DB_NAME, "rb") as f_db:
            bytes_db = f_db.read()
        st.download_button(
            label="📥 Baixar Backup (.db)",
            data=bytes_db,
            file_name=f"backup_dominus_{datetime.now().strftime('%d_%m_%Y_%H%M')}.db",
            mime="application/octet-stream",
            use_container_width=True
        )
        
    # 2. Uploader para Restaurar Backup em caso de reinício do Streamlit Cloud
    arquivo_backup = st.file_uploader("📤 Restaurar Backup (.db)", type=["db"], key="up_backup")
    if arquivo_backup is not None:
        if st.button("Confirmar Restauração", type="primary", use_container_width=True):
            with open(DB_NAME, "wb") as f_out:
                f_out.write(arquivo_backup.getbuffer())
            st.success("✅ Dados restaurados com sucesso! Atualizando...")
            st.rerun()

    if st.button("🚪 Sair do Sistema", use_container_width=True):
        st.session_state.autenticado = False
        st.session_state.carrinho_novo = []
        st.session_state.ultimo_recibo = None
        st.rerun()
# ==============================================================================
# MÓDULO 1: PDV OTIMIZADO (INTERFACE LIMPA E ACESSÍVEL)
# ==============================================================================
if menu == "🛒 Frente de Caixa (PDV)":
    # Estilo visual para aumentar fontes, espaçamento e botões (Foco em Acessibilidade)
    st.markdown("""
        <style>
        .stSelectbox label, .stTextInput label, .stNumberInput label {
            font-size: 18px !important;
            font-weight: 600 !important;
            color: #1e3d59 !important;
        }
        .stButton button {
            min-height: 52px !important;
            font-size: 18px !important;
            font-weight: bold !important;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h1 style='text-align: center; color: #1e3d59; font-size: 32px;'>🛒 Caixa - Frente de Loja</h1>", unsafe_allow_html=True)
    
    # Busca produtos cadastrados
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT codigo_barras, 
               COALESCE(NULLIF(produto_base, ''), nome) as base, 
               COALESCE(NULLIF(variacao, ''), 'Padrão') as var, 
               nome, 
               preco_venda, 
               estoque_atual 
        FROM produtos 
        ORDER BY base ASC, var ASC
    """)
    lista_produtos_db = cursor.fetchall()
    conn.close()

    produtos_agrupados = {}
    for cod, base, var, nome_comp, preco, est in lista_produtos_db:
        if base not in produtos_agrupados:
            produtos_agrupados[base] = []
        produtos_agrupados[base].append({
            "codigo": cod,
            "variacao": var,
            "nome_completo": nome_comp,
            "preco": preco,
            "estoque": est
        })

    # -------------------- PASSO 1: SELEÇÃO DO PRODUTO --------------------
    st.markdown("### 1️⃣ Escolher Produto")
    with st.container(border=True):
        col_sel1, col_sel2, col_sel3 = st.columns([1.2, 1.5, 1.5])
        with col_sel1:
            input_codigo = st.text_input("🔫 Código de Barras:", key="pdv_cod_barras", placeholder="Bipe ou digite...")
        with col_sel2:
            lista_bases = ["-- Selecione o Produto --"] + list(produtos_agrupados.keys())
            base_escolhida = st.selectbox("Produto:", options=lista_bases, key="pdv_base")
        with col_sel3:
            if base_escolhida != "-- Selecione o Produto --":
                opcoes_var = {
                    f"{v['variacao']} — R$ {v['preco']:.2f}": v["codigo"]
                    for v in produtos_agrupados[base_escolhida]
                }
                var_label = st.selectbox("Tipo / Sabor:", options=list(opcoes_var.keys()), key="pdv_var")
                codigo_da_lista = opcoes_var[var_label]
            else:
                st.selectbox("Tipo / Sabor:", options=["-- Escolha o produto ao lado --"], disabled=True)
                codigo_da_lista = None

        with st.form("form_lancar_item", clear_on_submit=True):
            col_q1, col_q2 = st.columns([1.0, 2.5])
            with col_q1:
                qtd_item = st.number_input("Quantidade:", min_value=1, value=1, step=1)
            with col_q2:
                st.write("")
                st.write("")
                btn_adicionar = st.form_submit_button("➕ ADICIONAR NA COMPRA", type="primary", use_container_width=True)
            
            # Desconto por item guardado para não poluir a visão principal
            with st.expander("🏷️ Aplicar desconto apenas neste item (Opcional)"):
                desconto_item = st.number_input("Valor do Desconto no Item (R$):", min_value=0.0, value=0.0, step=0.50, format="%.2f")

        if btn_adicionar:
            termo_busca = input_codigo.strip() if input_codigo.strip() else codigo_da_lista
            if termo_busca:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT codigo_barras, nome, preco_venda, estoque_atual 
                    FROM produtos 
                    WHERE codigo_barras = ? OR nome LIKE ?
                """, (termo_busca, f"%{termo_busca}%"))
                prod_achado = cursor.fetchone()
                conn.close()
                
                if prod_achado:
                    cod_barras, nome_prod, v_unit, estoque_disp = prod_achado
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
                        st.toast(f"✅ {nome_prod} adicionado!")
                        st.rerun()
                    else:
                        st.warning(f"⚠️ Estoque insuficiente. Disponível: {estoque_disp} un.")
                else:
                    st.error("❌ Produto não encontrado.")
            else:
                st.warning("⚠️ Escolha um produto na lista ou use o leitor.")

    # -------------------- PASSO 2: ITENS DA COMPRA --------------------
    st.markdown("### 2️⃣ Itens da Compra")
    with st.container(border=True):
        if st.session_state.carrinho_novo:
            df_cart = pd.DataFrame(st.session_state.carrinho_novo)
            # Exibe apenas as colunas essenciais para facilitar a leitura
            colunas_visiveis = ["Seq", "Descrição do Produto", "Quantidade", "Valor Unitário", "Valor Total"]
            st.dataframe(
                df_cart[colunas_visiveis],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Seq": st.column_config.NumberColumn("Nº", width="small"),
                    "Valor Unitário": st.column_config.NumberColumn("Preço Un.", format="R$ %.2f"),
                    "Valor Total": st.column_config.NumberColumn("Total", format="R$ %.2f"),
                }
            )
            
            # Opções de cancelamento recolhidas para evitar cliques acidentais
            with st.expander("🗑️ Precisa cancelar algum item ou limpar a venda?"):
                col_c1, col_c2, col_c3 = st.columns([1.0, 1.5, 1.5])
                with col_c1:
                    max_seq = max(len(st.session_state.carrinho_novo), 1)
                    idx_cancelar = st.number_input("Nº do Item:", min_value=1, max_value=max_seq, step=1)
                with col_c2:
                    st.write("")
                    st.write("")
                    if st.button("⚠️ Remover Item", use_container_width=True):
                        st.session_state.carrinho_novo = [
                            item for item in st.session_state.carrinho_novo if item["Seq"] != idx_cancelar
                        ]
                        for i, item in enumerate(st.session_state.carrinho_novo):
                            item["Seq"] = i + 1
                        st.rerun()
                with col_c3:
                    st.write("")
                    st.write("")
                    if st.button("❌ Cancelar Toda Venda", use_container_width=True):
                        st.session_state.carrinho_novo = []
                        st.rerun()
        else:
            st.info("Nenhum item adicionado ainda.")

    # -------------------- PASSO 3: PAGAMENTO E FECHAMENTO --------------------
    st.markdown("### 3️⃣ Pagamento e Fechamento")
    with st.container(border=True):
        subtotal = sum(item["Quantidade"] * item["Valor Unitário"] for item in st.session_state.carrinho_novo)
        descontos_itens = sum(item["Desconto Item"] for item in st.session_state.carrinho_novo)
        
        with st.expander("🏷️ Dar desconto no valor total da compra (Opcional)"):
            desc_total_venda = st.number_input("Desconto Total (R$):", min_value=0.0, value=0.0, step=1.0, format="%.2f")
            
        total_compra = max(0.0, subtotal - descontos_itens - desc_total_venda)

        # Destaque visual grande para o Total a Pagar
        st.markdown(
            f"<div style='background-color:#e8f4f8; padding:18px; border-radius:10px; border: 2px solid #1e3d59; text-align:center; margin-bottom:20px;'>"
            f"<span style='font-size:20px; color:#1e3d59; font-weight:bold;'>TOTAL A PAGAR</span><br>"
            f"<span style='font-size:42px; color:#0b5394; font-weight:900;'>R$ {total_compra:.2f}</span>"
            f"</div>", 
            unsafe_allow_html=True
        )

        col_p1, col_p2, col_p3, col_p4 = st.columns(4)
        with col_p1:
            val_dinheiro = st.number_input("💵 Dinheiro (R$)", min_value=0.0, value=0.0, step=1.0, format="%.2f")
        with col_p2:
            val_pix = st.number_input("💠 Pix (R$)", min_value=0.0, value=0.0, step=1.0, format="%.2f")
        with col_p3:
            val_debito = st.number_input("💳 Débito (R$)", min_value=0.0, value=0.0, step=1.0, format="%.2f")
        with col_p4:
            val_credito = st.number_input("💳 Crédito (R$)", min_value=0.0, value=0.0, step=1.0, format="%.2f")

        total_recebido = val_dinheiro + val_pix + val_debito + val_credito
        pagamentos_eletronicos = val_pix + val_debito + val_credito
        valor_restante = max(0.0, total_compra - total_recebido)
        excesso_eletronico = pagamentos_eletronicos > (total_compra + 0.009)
        total_recebido = val_dinheiro + val_pix + val_debito + val_credito
        pagamentos_eletronicos = val_pix + val_debito + val_credito
        valor_restante = max(0.0, total_compra - total_recebido)
        excesso_eletronico = pagamentos_eletronicos > (total_compra + 0.009)
        troco = max(0.0, total_recebido - total_compra) if (total_compra > 0 and not excesso_eletronico) else 0.0

        st.write("")
        col_res1, col_res2 = st.columns(2)
        with col_res1:
            if excesso_eletronico:
                st.error("⚠️ Valor no Pix/Cartão maior que o total!")
            elif valor_restante > 0.009:
                st.warning(f"⏳ **Falta Receber:** R$ {valor_restante:.2f}")
            elif total_compra > 0:
                st.success("✅ **Valor Completo!**")
        with col_res2:
            if troco > 0:
                st.markdown(
                    f"<div style='background-color:#fff3cd; padding:12px; border-radius:8px; border: 2px solid #ffc107; text-align:center;'>"
                    f"<span style='font-size:18px; font-weight:bold; color:#856404;'>TROCO A DEVOLVER: R$ {troco:.2f}</span>"
                    f"</div>", 
                    unsafe_allow_html=True
                )

        st.write("")
        tem_itens = len(st.session_state.carrinho_novo) > 0
        pagamento_ok = (total_compra > 0) and (valor_restante <= 0.009) and (not excesso_eletronico)

        if st.button("✅ FINALIZAR VENDA E GERAR RECIBO", type="primary", use_container_width=True, disabled=not (tem_itens and pagamento_ok)):
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            for item in st.session_state.carrinho_novo:
                cursor.execute(
                    "UPDATE produtos SET estoque_atual = estoque_atual - ? WHERE codigo_barras = ?", 
                    (item["Quantidade"], item["Código"])
                )
            
            formas_usadas = []
            if val_dinheiro > 0: formas_usadas.append(f"Dinheiro: R$ {val_dinheiro:.2f}")
            if val_pix > 0: formas_usadas.append(f"Pix: R$ {val_pix:.2f}")
            if val_debito > 0: formas_usadas.append(f"Débito: R$ {val_debito:.2f}")
            if val_credito > 0: formas_usadas.append(f"Crédito: R$ {val_credito:.2f}")
            str_pagamento = " | ".join(formas_usadas)
            
            data_agora = datetime.now().strftime("%d/%m/%Y %H:%M")
            desconto_geral_aplicado = descontos_itens + desc_total_venda
            
            cursor.execute("""
                INSERT INTO vendas (data_hora, subtotal, desconto_total, total, forma_pagamento) 
                VALUES (?, ?, ?, ?, ?)
            """, (data_agora, subtotal, desconto_geral_aplicado, total_compra, str_pagamento))
            num_cupom_gerado = cursor.lastrowid
            
            conn.commit()
            conn.close()
            
            st.session_state.ultimo_recibo = {
                "numero": num_cupom_gerado,
                "texto": gerar_texto_recibo(
                    num_cupom_gerado, data_agora, st.session_state.carrinho_novo,
                    subtotal, desconto_geral_aplicado, total_compra,
                    str_pagamento, total_recebido, troco
                )
            }
            st.session_state.carrinho_novo = []
            st.rerun()

    # Exibição do Recibo em destaque após finalizar
    if st.session_state.ultimo_recibo:
        with st.container(border=True):
            st.success(f"🎉 Venda #{st.session_state.ultimo_recibo['numero']:06d} concluída com sucesso!")
            col_r1, col_r2 = st.columns([2, 1])
            with col_r1:
                st.code(st.session_state.ultimo_recibo["texto"], language="text")
            with col_r2:
                st.download_button(
                    label="🖨️ Baixar / Imprimir Recibo",
                    data=st.session_state.ultimo_recibo["texto"],
                    file_name=f"recibo_{st.session_state.ultimo_recibo['numero']:06d}.txt",
                    mime="text/plain",
                    type="primary",
                    use_container_width=True
                )
                st.write("")
                if st.button("🆕 Iniciar Nova Venda", use_container_width=True):
                    st.session_state.ultimo_recibo = None
                    st.rerun()


# ==============================================================================
# MÓDULO 2: ALMOXARIFADO / ESTOQUE (COM PRODUTO BASE E VARIAÇÕES)
# ==============================================================================
elif menu == "📦 Almoxarifado / Estoque":
    st.header("Gestão Central de Almoxarifado (Produtos e Variações)")
    
    conn = sqlite3.connect(DB_NAME)
    df_almoxarifado = pd.read_sql_query("""
        SELECT id, 
               codigo_barras AS [Cód. Barras], 
               produto_base AS [Produto Base],
               variacao AS [Variação / Sabor],
               preco_venda AS [Preço de Venda (R$)], 
               estoque_atual AS [Estoque Atual], 
               estoque_minimo AS [Estoque Mínimo] 
        FROM produtos
        ORDER BY produto_base ASC, variacao ASC
    """, conn)
    conn.close()
    
    st.subheader("Inventário Físico da Loja")
    st.dataframe(df_almoxarifado, use_container_width=True, hide_index=True)
    
    col_alm1, col_alm2 = st.columns(2)
    
    with col_alm1:
        with st.expander("➕ Cadastrar / Abastecer Produto e Variação", expanded=True):
            with st.form("entrada_produtos"):
                c_barras = st.text_input("Código de Barras Único")
                c_base = st.text_input("Produto Base / Linha (Ex: Chocolate Joaozinho)")
                c_var = st.text_input("Variação / Sabor (Ex: Chocolate Branco, Com Amêndoas)")
                c_preco = st.number_input("Preço de Venda Praticado (R$)", min_value=0.0, format="%.2f")
                c_qtd = st.number_input("Quantidade Recebida (Entrada)", min_value=1, step=1)
                btn_salvar_estoque = st.form_submit_button("Confirmar Entrada")
                
                if btn_salvar_estoque:
                    if c_barras.strip() and c_base.strip() and c_var.strip() and c_preco > 0:
                        nome_completo = f"{c_base.strip()} - {c_var.strip()}"
                        conn = sqlite3.connect(DB_NAME)
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO produtos (codigo_barras, produto_base, variacao, nome, preco_venda, estoque_atual)
                            VALUES (?, ?, ?, ?, ?, ?)
                            ON CONFLICT(codigo_barras) DO UPDATE SET
                            estoque_atual = estoque_atual + excluded.estoque_atual,
                            preco_venda = excluded.preco_venda,
                            produto_base = excluded.produto_base,
                            variacao = excluded.variacao,
                            nome = excluded.nome
                        """, (c_barras.strip(), c_base.strip(), c_var.strip(), nome_completo, c_preco, c_qtd))
                        conn.commit()
                        conn.close()
                        st.success(f"📦 '{nome_completo}' integrado ao Almoxarifado!")
                        st.rerun()
                    else:
                        st.error("⚠️ Preencha todos os campos (Código, Produto Base, Variação e Preço).")

    with col_alm2:
        with st.expander("🚨 Alertas de Estoque Crítico (Mínimo)", expanded=True):
            conn = sqlite3.connect(DB_NAME)
            df_critico = pd.read_sql_query("""
                SELECT codigo_barras AS [Código], 
                       nome AS [Produto / Variação], 
                       estoque_atual AS [Qtd Atual], 
                       estoque_minimo AS [Qtd Mínima] 
                FROM produtos 
                WHERE estoque_atual <= estoque_minimo
            """, conn)
            conn.close()
            
            if not df_critico.empty:
                st.warning("Os seguintes itens precisam de reposição urgente:")
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
