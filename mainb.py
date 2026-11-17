import os
import sqlite3
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import streamlit.components.v1 as components

# Configuração da página Web do Streamlit
st.set_page_config(page_title="Dominus PDV - Gestão Integrada", page_icon="🛒", layout="wide")

# ==============================================================================
# CONFIGURAÇÃO UNIFICADA DO BANCO DE DADOS E GERADORES DE IMPRESSÃO
# ==============================================================================
if not os.path.exists("banco_dados"):
    os.makedirs("banco_dados")

DB_NAME = os.path.join("banco_dados", "estoque_loja_independente.db")

def exibir_logo_centralizado(largura=180):
    if os.path.exists("logo_empresa.png"):
        col_e, col_c, col_d = st.columns([1, 1, 1])
        with col_c:
            st.image("logo_empresa.png", width=largura)

def gerar_texto_recibo(num_cupom, data_hora, itens, subtotal, descontos, total, formas_pgto, recebido, troco):
    linhas = [
        "==========================================",
        "           DOMINUS PDV - RECIBO           ",
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

def gerar_relatorio_fechamento_dia(data_filtro, df_dia):
    qtd_vendas = len(df_dia)
    subtotal_dia = df_dia["Subtotal (R$)"].sum()
    descontos_dia = df_dia["Descontos (R$)"].sum()
    total_dia = df_dia["Total Pago (R$)"].sum()

    totais_pgto = {"Dinheiro": 0.0, "Pix": 0.0, "Débito": 0.0, "Crédito": 0.0}
    for registro in df_dia["Formas de Pagto"].dropna():
        partes = registro.split("|")
        for p in partes:
            p = p.strip()
            for forma in totais_pgto.keys():
                if p.startswith(f"{forma}: R$"):
                    try:
                        valor = float(p.split("R$")[1].strip())
                        totais_pgto[forma] += valor
                    except ValueError:
                        pass

    linhas = [
        "==========================================",
        "    DOMINUS PDV - FECHAMENTO DE CAIXA     ",
        "==========================================",
        f"Data do Fechamento: {data_filtro}",
        f"Emissão: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "------------------------------------------",
        f"QUANTIDADE DE VENDAS:        {qtd_vendas:04d} cupons",
        f"SUBTOTAL BRUTO:               R$ {subtotal_dia:8.2f}",
        f"TOTAL DE DESCONTOS:          -R$ {descontos_dia:8.2f}",
        f"FATURAMENTO LÍQUIDO DO DIA:   R$ {total_dia:8.2f}",
        "------------------------------------------",
        "RESUMO POR FORMA DE PAGAMENTO:",
        f"  Dinheiro:                   R$ {totais_pgto['Dinheiro']:8.2f}",
        f"  Pix:                        R$ {totais_pgto['Pix']:8.2f}",
        f"  Cartão de Débito:           R$ {totais_pgto['Débito']:8.2f}",
        f"  Cartão de Crédito:          R$ {totais_pgto['Crédito']:8.2f}",
        "------------------------------------------",
        "CUPONS REGISTRADOS NO DIA:"
    ]

    for _, row in df_dia.iterrows():
        hora = row["Data/Hora"].split(" ")[1] if " " in row["Data/Hora"] else ""
        linhas.append(f"  #{int(row['Nº Cupom']):04d} ({hora}) - R$ {row['Total Pago (R$)']:7.2f}")

    linhas.extend([
        "==========================================",
        "         CONFERÊNCIA DE CAIXA OK          ",
        "=========================================="
    ])
    return "\n".join(linhas)
def inicializar_banco_isolado():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Tabela de Funcionários
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
    
    # 3. Tabela de Produtos (Mesmo código de barras para sabores/gramaturas diferentes + Validade)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_barras TEXT NOT NULL,
        produto_base TEXT NOT NULL,
        variacao TEXT NOT NULL,
        gramatura TEXT DEFAULT 'Padrão',
        nome TEXT NOT NULL,
        preco_venda REAL NOT NULL,
        estoque_atual INTEGER DEFAULT 0,
        estoque_minimo INTEGER DEFAULT 5,
        data_fabricacao TEXT,
        data_validade TEXT,
        UNIQUE(codigo_barras, variacao, gramatura)
    )""")

    # Migração automática caso a tabela antiga tenha UNIQUE apenas em codigo_barras
    cursor.execute("PRAGMA table_info(produtos)")
    colunas_info = cursor.fetchall()
    colunas_existentes = [col for col in colunas_info]
    
    if "gramatura" not in colunas_existentes or "data_validade" not in colunas_existentes:
        cursor.execute("ALTER TABLE produtos RENAME TO produtos_antigos")
        cursor.execute("""
        CREATE TABLE produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_barras TEXT NOT NULL,
            produto_base TEXT NOT NULL,
            variacao TEXT NOT NULL,
            gramatura TEXT DEFAULT 'Padrão',
            nome TEXT NOT NULL,
            preco_venda REAL NOT NULL,
            estoque_atual INTEGER DEFAULT 0,
            estoque_minimo INTEGER DEFAULT 5,
            data_fabricacao TEXT,
            data_validade TEXT,
            UNIQUE(codigo_barras, variacao, gramatura)
        )""")
        
        base_col = "produto_base" if "produto_base" in colunas_existentes else "nome"
        var_col = "variacao" if "variacao" in colunas_existentes else "'Padrão'"
        
        cursor.execute(f"""
            INSERT OR IGNORE INTO produtos (id, codigo_barras, produto_base, variacao, gramatura, nome, preco_venda, estoque_atual, estoque_minimo)
            SELECT id, codigo_barras, COALESCE(NULLIF({base_col}, ''), nome), COALESCE(NULLIF({var_col}, ''), 'Padrão'), 'Padrão', nome, preco_venda, estoque_atual, estoque_minimo
            FROM produtos_antigos
        """)
        cursor.execute("DROP TABLE produtos_antigos")

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

    cursor.execute("SELECT COUNT(*) FROM funcionarios")
    if cursor.fetchone() == 0:
        cursor.execute(
            "INSERT INTO funcionarios (nome, usuario, senha, cargo) VALUES (?, ?, ?, ?)",
            ("Administrador", "admin", "admin123", "Gerente")
        )
        
    cursor.execute("SELECT COUNT(*) FROM produtos")
    if cursor.fetchone() == 0:
        exemplos = [
            ("78910001", "Chocolate Joaozinho", "Chocolate Branco", "100g", "Chocolate Joaozinho - Chocolate Branco (100g)", 6.50, 50, "2026-11-01", "2026-12-30"),
            ("78910001", "Chocolate Joaozinho", "Com Amêndoas", "100g", "Chocolate Joaozinho - Com Amêndoas (100g)", 7.50, 40, "2026-11-01", "2026-12-30"),
            ("78910001", "Chocolate Joaozinho", "Com Amêndoas", "250g", "Chocolate Joaozinho - Com Amêndoas (250g)", 15.90, 20, "2026-11-01", "2026-12-30")
        ]
        cursor.executemany(
            """INSERT INTO produtos 
               (codigo_barras, produto_base, variacao, gramatura, nome, preco_venda, estoque_atual, data_fabricacao, data_validade) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                    st.session_state.user_nome = user_data
                    st.session_state.user_cargo = user_data
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

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id,
               codigo_barras, 
               COALESCE(NULLIF(produto_base, ''), nome) as base, 
               COALESCE(NULLIF(variacao, ''), 'Padrão') as var,
               COALESCE(NULLIF(gramatura, ''), 'Padrão') as gram,
               nome, 
               preco_venda, 
               estoque_atual,
               data_validade
        FROM produtos 
        ORDER BY base ASC, var ASC, gram ASC
    """)
    lista_produtos_db = cursor.fetchall()
    conn.close()

    # Alarme discreto no topo do PDV se houver produto vencido ou vencendo em 7 dias
    hoje_pdv = datetime.now().date()
    vencendo_pdv = []
    for _, _, base, var, gram, _, _, est, val_str in lista_produtos_db:
        if est > 0 and val_str and str(val_str).strip() not in ["", "None", "NaT"]:
            try:
                dt_v = datetime.strptime(str(val_str)[:10], "%Y-%m-%d").date()
                dias_r = (dt_v - hoje_pdv).days
                if dias_r <= 7:
                    status_v = "VENCIDO" if dias_r < 0 else f"vence em {dias_r}d"
                    vencendo_pdv.append(f"{base} - {var} ({gram}) [{status_v}]")
            except ValueError:
                pass
    if vencendo_pdv:
        st.warning("⚠️ **Atenção Validade:** " + " | ".join(vencendo_pdv))

    produtos_agrupados = {}
    for pid, cod, base, var, gram, nome_comp, preco, est, val_str in lista_produtos_db:
        if base not in produtos_agrupados:
            produtos_agrupados[base] = []
        val_fmt = ""
        if val_str and str(val_str).strip() not in ["", "None", "NaT"]:
            try:
                val_fmt = f" | Val: {datetime.strptime(str(val_str)[:10], '%Y-%m-%d').strftime('%d/%m/%Y')}"
            except ValueError:
                pass
        produtos_agrupados[base].append({
            "id": pid,
            "codigo": cod,
            "variacao": var,
            "gramatura": gram,
            "nome_completo": nome_comp,
            "preco": preco,
            "estoque": est,
            "validade_fmt": val_fmt
        })

    # -------------------- PASSO 1: SELEÇÃO DO PRODUTO --------------------
    st.markdown("### 1️⃣ Escolher Produto")
    with st.container(border=True):
        col_sel1, col_sel2, col_sel3 = st.columns([1.1, 1.4, 1.7])
        with col_sel1:
            input_codigo = st.text_input("🔫 Código de Barras:", key="pdv_cod_barras", placeholder="Bipe ou digite...")
        with col_sel2:
            lista_bases = ["-- Selecione o Produto --"] + list(produtos_agrupados.keys())
            base_escolhida = st.selectbox("Produto:", options=lista_bases, key="pdv_base")
        with col_sel3:
            if base_escolhida != "-- Selecione o Produto --":
                opcoes_var = {
                    f"{v['variacao']} ({v['gramatura']}) — R$ {v['preco']:.2f}{v['validade_fmt']}": v["id"]
                    for v in produtos_agrupados[base_escolhida]
                }
                var_label = st.selectbox("Sabor e Gramatura:", options=list(opcoes_var.keys()), key="pdv_var")
                id_da_lista = opcoes_var[var_label]
            else:
                st.selectbox("Sabor e Gramatura:", options=["-- Escolha o produto ao lado --"], disabled=True)
                id_da_lista = None

        # Se o operador bipar um código de barras que tem mais de 1 sabor/gramatura, abre seletor imediato
        id_escolhido_codigo = None
        if input_codigo.strip():
            correspondentes = [p for p in lista_produtos_db if p[1] == input_codigo.strip()]
            if len(correspondentes) > 1:
                opcoes_cod = {
                    f"{p[3]} ({p[4]}) — R$ {p[6]:.2f} (Est: {p[7]})": p[0]
                    for p in correspondentes
                }
                escolha_cod_label = st.selectbox("🔎 Este código possui mais de uma opção. Escolha qual está vendendo:", options=list(opcoes_cod.keys()))
                id_escolhido_codigo = opcoes_cod[escolha_cod_label]
            elif len(correspondentes) == 1:
                id_escolhido_codigo = correspondentes[0][0]

        with st.form("form_lancar_item", clear_on_submit=True):
            col_q1, col_q2 = st.columns([1.0, 2.5])
            with col_q1:
                qtd_item = st.number_input("Quantidade:", min_value=1, value=1, step=1)
            with col_q2:
                st.write("")
                st.write("")
                btn_adicionar = st.form_submit_button("➕ ADICIONAR NA COMPRA", type="primary", use_container_width=True)
            
            with st.expander("🏷️ Aplicar desconto apenas neste item (Opcional)"):
                desconto_item = st.number_input("Valor do Desconto no Item (R$):", min_value=0.0, value=0.0, step=0.50, format="%.2f")

        if btn_adicionar:
            id_final = id_escolhido_codigo if input_codigo.strip() else id_da_lista
            
            if id_final:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("SELECT id, codigo_barras, nome, preco_venda, estoque_atual FROM produtos WHERE id = ?", (id_final,))
                prod_achado = cursor.fetchone()
                conn.close()
                
                if prod_achado:
                    pid, cod_barras, nome_prod, v_unit, estoque_disp = prod_achado
                    qtd_no_carrinho = sum(
                        item["Quantidade"] for item in st.session_state.carrinho_novo if item.get("ID_Prod") == pid
                    )
                    if estoque_disp >= (qtd_item + qtd_no_carrinho):
                        v_tot = max(0.0, (v_unit * qtd_item) - desconto_item)
                        st.session_state.carrinho_novo.append({
                            "Seq": len(st.session_state.carrinho_novo) + 1,
                            "ID_Prod": pid,
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
                st.warning("⚠️ Produto não encontrado ou não selecionado.")
    # -------------------- PASSO 2: ITENS DA COMPRA --------------------
    st.markdown("### 2️⃣ Itens da Compra")
    with st.container(border=True):
        if st.session_state.carrinho_novo:
            df_cart = pd.DataFrame(st.session_state.carrinho_novo)
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
                    "UPDATE produtos SET estoque_atual = estoque_atual - ? WHERE id = ?", 
                    (item["Quantidade"], item["ID_Prod"])
                )

            formas_usadas = []
            if val_dinheiro > 0:
                formas_usadas.append(f"Dinheiro: R$ {val_dinheiro:.2f}")
            if val_pix > 0:
                formas_usadas.append(f"Pix: R$ {val_pix:.2f}")
            if val_debito > 0:
                formas_usadas.append(f"Débito: R$ {val_debito:.2f}")
            if val_credito > 0:
                formas_usadas.append(f"Crédito: R$ {val_credito:.2f}")
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
                    num_cupom_gerado,
                    data_agora,
                    st.session_state.carrinho_novo,
                    subtotal,
                    desconto_geral_aplicado,
                    total_compra,
                    str_pagamento,
                    total_recebido,
                    troco
                )
            }
            st.session_state.carrinho_novo = []
            st.rerun()

    # Exibição do Recibo em destaque após finalizar
    if st.session_state.ultimo_recibo:
        with st.container(border=True):
            st.success(f"🎉 Venda #{st.session_state.ultimo_recibo['numero']:06d} concluída com sucesso!")
            col_r1, col_r2 = st.columns([1.5, 1.0])
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
# MÓDULO 2: ALMOXARIFADO / ESTOQUE (SABORES, GRAMATURA E ALARME DE VALIDADE)
# ==============================================================================
elif menu == "📦 Almoxarifado / Estoque":
    st.header("📦 Gestão de Estoque, Gramaturas e Validade")
    
    conn = sqlite3.connect(DB_NAME)
    df_almoxarifado = pd.read_sql_query("""
        SELECT id AS [ID], 
               codigo_barras AS [Cód. Barras], 
               produto_base AS [Produto Base],
               variacao AS [Sabor / Tipo],
               gramatura AS [Gramatura],
               preco_venda AS [Preço (R$)], 
               estoque_atual AS [Estoque],
               data_fabricacao AS [Fabricação],
               data_validade AS [Validade]
        FROM produtos
        ORDER BY produto_base ASC, variacao ASC, gramatura ASC
    """, conn)
    conn.close()

    # -------------------- ALARME DE VENCIMENTO (PRÓXIMOS 7 DIAS) --------------------
    if not df_almoxarifado.empty:
        hoje = datetime.now().date()
        alertas_validade = []
        for _, row in df_almoxarifado.iterrows():
            val_str = row["Validade"]
            if val_str and str(val_str).strip() not in ["", "None", "NaT"]:
                try:
                    dt_val = datetime.strptime(str(val_str)[:10], "%Y-%m-%d").date()
                    dias_restantes = (dt_val - hoje).days
                    if dias_restantes < 0:
                        alertas_validade.append(f"🔴 **VENCIDO há {abs(dias_restantes)} dia(s):** {row['Produto Base']} - {row['Sabor / Tipo']} ({row['Gramatura']}) | Val: {dt_val.strftime('%d/%m/%Y')}")
                    elif dias_restantes <= 7:
                        alertas_validade.append(f"🟡 **VENCE EM {dias_restantes} DIA(S):** {row['Produto Base']} - {row['Sabor / Tipo']} ({row['Gramatura']}) | Val: {dt_val.strftime('%d/%m/%Y')}")
                except ValueError:
                    pass
        
        if alertas_validade:
            with st.container(border=True):
                st.error("🚨 **ALARME DE VALIDADE / VENCIMENTO PRÓXIMO**")
                for aviso in alertas_validade:
                    st.markdown(aviso)

    st.subheader("Inventário Físico da Loja")
    st.dataframe(df_almoxarifado, use_container_width=True, hide_index=True)
    
    col_alm1, col_alm2 = st.columns([1.4, 1.0])
    
    with col_alm1:
        with st.expander("➕ Cadastrar / Abastecer Produto (Mesmo Cód. Barras ou Novo)", expanded=True):
            with st.form("entrada_produtos"):
                c_barras = st.text_input("Código de Barras (Pode repetir para sabores/gramaturas diferentes)")
                c_base = st.text_input("Produto Base / Linha (Ex: Chocolate Joaozinho)")
                
                col_sg1, col_sg2 = st.columns(2)
                with col_sg1:
                    c_var = st.text_input("Sabor / Variação (Ex: Chocolate Branco)")
                with col_sg2:
                    c_gram = st.text_input("Gramatura / Peso (Ex: 100g, 250g, 1kg)", value="Padrão")
                
                col_pq1, col_pq2 = st.columns(2)
                with col_pq1:
                    c_preco = st.number_input("Preço de Venda (R$)", min_value=0.0, format="%.2f")
                with col_pq2:
                    c_qtd = st.number_input("Quantidade Entrada", min_value=1, step=1)
                    
                col_dt1, col_dt2 = st.columns(2)
                with col_dt1:
                    c_fab = st.date_input("Data de Fabricação", value=datetime.now().date(), format="DD/MM/YYYY")
                with col_dt2:
                    c_val = st.date_input("Data de Validade", value=datetime.now().date() + timedelta(days=30), format="DD/MM/YYYY")
                    
                btn_salvar_estoque = st.form_submit_button("Confirmar Entrada no Estoque", type="primary", use_container_width=True)
                
                if btn_salvar_estoque:
                    if c_barras.strip() and c_base.strip() and c_var.strip() and c_gram.strip() and c_preco > 0:
                        nome_completo = f"{c_base.strip()} - {c_var.strip()} ({c_gram.strip()})"
                        conn = sqlite3.connect(DB_NAME)
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO produtos (codigo_barras, produto_base, variacao, gramatura, nome, preco_venda, estoque_atual, data_fabricacao, data_validade)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(codigo_barras, variacao, gramatura) DO UPDATE SET
                            estoque_atual = estoque_atual + excluded.estoque_atual,
                            preco_venda = excluded.preco_venda,
                            produto_base = excluded.produto_base,
                            nome = excluded.nome,
                            data_fabricacao = excluded.data_fabricacao,
                            data_validade = excluded.data_validade
                        """, (
                            c_barras.strip(), c_base.strip(), c_var.strip(), c_gram.strip(),
                            nome_completo, c_preco, c_qtd, c_fab.strftime("%Y-%m-%d"), c_val.strftime("%Y-%m-%d")
                        ))
                        conn.commit()
                        conn.close()
                        st.success(f"📦 '{nome_completo}' salvo no estoque com sucesso!")
                        st.rerun()
                    else:
                        st.error("⚠️ Preencha Código de Barras, Produto Base, Sabor, Gramatura e Preço.")

    with col_alm2:
        with st.expander("📉 Alertas de Estoque Baixo", expanded=True):
            conn = sqlite3.connect(DB_NAME)
            df_critico = pd.read_sql_query("""
                SELECT codigo_barras AS [Código], 
                       nome AS [Produto], 
                       estoque_atual AS [Qtd Atual], 
                       estoque_minimo AS [Mínimo] 
                FROM produtos 
                WHERE estoque_atual <= estoque_minimo
            """, conn)
            conn.close()
            
            if not df_critico.empty:
                st.warning("Itens precisando de reposição:")
                st.dataframe(df_critico, use_container_width=True, hide_index=True)
            else:
                st.success("✅ Níveis de estoque adequados!")

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
# MÓDULO 4: RELATÓRIOS DE VENDAS E FECHAMENTO DIÁRIO PARA IMPRESSÃO
# ==============================================================================
elif menu == "📊 Relatórios de Vendas":
    st.header("📊 Painel Gerencial e Fechamento do Dia")
    
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
    
    df_faturamento = pd.read_sql_query("""
        SELECT SUBSTR(data_hora, 1, 10) AS [Data], 
               SUM(total) AS [Total Faturado (R$)] 
        FROM vendas 
        GROUP BY [Data] 
        ORDER BY [Data] ASC
    """, conn)
    conn.close()

    # -------------------- SEÇÃO DE IMPRESSÃO DO FECHAMENTO DO DIA --------------------
    st.subheader("🖨️ Fechamento de Caixa para Impressão")
    with st.container(border=True):
        col_f1, col_f2 = st.columns([1.2, 2.0])
        
        with col_f1:
            agora_br = datetime.utcnow() - timedelta(hours=3)
            
            data_selecionada = st.date_input(
                "Selecione o dia para fechar o caixa:", 
                value=agora_br.date(),
                format="DD/MM/YYYY"
            )
            data_str = data_selecionada.strftime("%d/%m/%Y")
            
            if not df_vendas_todas.empty:
                df_dia = df_vendas_todas[df_vendas_todas["Data/Hora"].str.startswith(data_str)]
            else:
                df_dia = pd.DataFrame()

            if not df_dia.empty:
                texto_fechamento = gerar_relatorio_fechamento_dia(data_str, df_dia)
                st.metric("Total Vendido no Dia", f"R$ {df_dia['Total Pago (R$)'].sum():.2f}")
            else:
                st.info(f"Nenhuma venda registrada na data {data_str}.")
                texto_fechamento = (
                    f"==========================================\n"
                    f"    DOMINUS PDV - FECHAMENTO DE CAIXA     \n"
                    f"==========================================\n"
                    f"Data: {data_str}\n"
                    f"Status: SEM MOVIMENTACAO NESTA DATA\n"
                    f"=========================================="
                )

            st.download_button(
                label="📥 Baixar Arquivo (.txt)",
                data=texto_fechamento,
                file_name=f"fechamento_caixa_{data_selecionada.strftime('%d_%m_%Y')}.txt",
                mime="text/plain",
                use_container_width=True
            )

            texto_esc = texto_fechamento.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
            html_impressao = f"""
            <button onclick="imprimirRelatorio()" style="
                width: 100%;
                background-color: #28a745;
                color: white;
                border: none;
                padding: 14px 20px;
                font-size: 18px;
                font-weight: bold;
                border-radius: 8px;
                cursor: pointer;
            ">
                🖨️ IMPRIMIR RELATÓRIO
            </button>
            <script>
            function imprimirRelatorio() {{
                var janela = window.open('', '_blank', 'width=450,height=650');
                if (!janela) {{
                    alert('Por favor, permita pop-ups neste site para abrir a janela de impressão.');
                    return;
                }}
                janela.document.write('<html><head><title>Fechamento de Caixa</title>');
                janela.document.write('<style>body {{ font-family: monospace; font-size: 13px; margin: 10px; white-space: pre; }}</style>');
                janela.document.write('</head><body>');
                janela.document.write(`{texto_esc}`);
                janela.document.write('</body></html>');
                janela.document.close();
                janela.focus();
                setTimeout(function() {{
                    janela.print();
                    janela.close();
                }}, 300);
            }}
            </script>
            """
            components.html(html_impressao, height=65)

        with col_f2:
            st.write("**Pré-visualização do Comprovante de Fechamento:**")
            st.code(texto_fechamento, language="text")

    st.markdown("---")

    # -------------------- INDICADORES GERAIS E GRÁFICO --------------------
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        total_acumulado = df_faturamento["Total Faturado (R$)"].sum() if not df_faturamento.empty else 0.0
        st.metric(label="Faturamento Total Acumulado", value=f"R$ {total_acumulado:.2f}")
    with col_m2:
        total_dias = len(df_faturamento)
        st.metric(label="Dias Operacionais Registrados", value=total_dias)
        
    st.subheader("📈 Evolução do Faturamento Diário")
    if not df_faturamento.empty:
        df_grafico = df_faturamento.set_index("Data")
        st.line_chart(df_grafico, y="Total Faturado (R$)")
    else:
        st.info("Aguardando primeiras vendas para plotar o gráfico de desempenho.")
        
    st.markdown("---")
    st.subheader("📋 Histórico Completo de Cupons Finalizados")
    
    if not df_vendas_todas.empty:
        st.dataframe(df_vendas_todas, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma venda realizada até o momento.")
