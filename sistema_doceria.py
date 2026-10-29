import streamlit as st
import sqlite3
import pandas as pd
import random
import os
from datetime import datetime, timedelta
from PIL import Image

# --- CONFIGURAÇÃO DA PÁGINA (ESTILO PREMIUM APP) ---
st.set_page_config(page_title="Candy Shop - PDV", layout="wide", initial_sidebar_state="expanded")

# --- BANCO DE DADOS LOCAL RESILIENTE ---
def inicializar_banco():
    conn = sqlite3.connect("loja_doces.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            codigo TEXT PRIMARY KEY, nome TEXT, preco REAL, estoque INTEGER,
            fabricacao TEXT, recebimento TEXT, vencimento TEXT, imagem TEXT, ativo TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, total REAL, forma_pagto TEXT
        )
    """)
    # Garante a existência de colunas preventivas
    for col in ["fabricacao", "recebimento", "vencimento", "imagem", "ativo"]:
        try: cursor.execute(f"ALTER TABLE produtos ADD COLUMN {col} TEXT")
        except: pass
    
    # Carga inicial demonstrativa se o estoque estiver zerado
    cursor.execute("SELECT COUNT(*) FROM produtos")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO produtos VALUES ('1001', 'Brigadeiro Gourmet Gp', 4.50, 99, '2026-10-28', '2026-10-28', '2026-11-05', '', 'Sim')")
        cursor.execute("INSERT INTO produtos VALUES ('1002', 'Beijinho de Coco', 4.00, 50, '2026-10-28', '2026-10-28', '2026-11-05', '', 'Sim')")
    conn.commit()
    conn.close()

inicializar_banco()

# --- GERENCIAMENTO DE SESSÃO (CARRINHO) ---
if "carrinho" not in st.session_state:
    st.session_state.carrinho = []

# --- MENU LATERAL FIXO (LOGOS DA EMPRESA E DESENVOLVEDOR) ---
with st.sidebar:
    # 🏢 Logo da Empresa (Topo)
    if os.path.exists("logo_empresa.png"):
        st.image("logo_empresa.png", use_container_width=True)
    else:
        st.markdown("<h2 style='text-align: center; color: #FF6B8B;'>🍬 Candy Shop</h2>", unsafe_allow_html=True)
        
    st.markdown("---")
    
    # Navegação entre as Abas Comerciais
    aba_selecionada = st.radio(
        "Navegar por:",
        ["🧁 Balcão de Vendas", "📦 Almoxarifado", "📊 Relatórios Gerenciais"],
        index=0
    )
    
    st.markdown("---")
    
    # 💻 Logo do Desenvolvedor (Rodapé Fixado)
    if os.path.exists("logo_desenvolvedor.png"):
        st.image("logo_desenvolvedor.png", use_container_width=True)
    else:
        st.caption("💻 Dev: @SweetManager")

# --- ABA 1: BALCÃO DE VENDAS (MURAL DE CARDS ESTILO DELIVERY) ---
if aba_selecionada == "🧁 Balcão de Vendas":
    st.title("🧁 Balcão de Vendas")
    
    # Barra de pesquisa global superior
    termo_busca = st.text_input("🔍 Procurar doce pelo nome...", placeholder="O que você quer adoçar hoje?")
    
    col_vitrine, col_sacola = st.columns([2.5, 1])
    
    with col_vitrine:
        # Busca produtos ativos diretamente do SQLite
        conn = sqlite3.connect("loja_doces.db")
        query = "SELECT codigo, nome, preco, estoque, imagem FROM produtos WHERE lower(nome) LIKE ? AND (ativo = 'Sim' OR ativo IS NULL)"
        df_doces = pd.read_sql_query(query, conn, params=(f"%{termo_busca.lower()}%",))
        conn.close()
        
        if df_doces.empty:
            st.info("Nenhum doce ativo encontrado no mural.")
        else:
            # Renderização em Grid Comercial (Grade de 3 Colunas)
            cols_grid = st.columns(3)
            for idx, row in df_doces.iterrows():
                with cols_grid[idx % 3]:
                    st.markdown("<div style='border: 1px solid #E9ECEF; border-radius: 10px; padding: 15px; background-color: white; text-align: center; margin-bottom: 15px;'>", unsafe_allow_html=True)
                    
                    # Foto real ou ícone padrão
                    if row['imagem'] and os.path.exists(row['imagem']):
                        st.image(row['imagem'], use_container_width=True)
                    else:
                        st.markdown("<h1 style='text-align: center;'>🍬</h1>", unsafe_allow_html=True)
                        
                    st.markdown(f"**{row['nome']}**")
                    st.markdown(f"<span style='color: #FF6B8B; font-weight: bold;'>R$ {row['preco']:.2f}</span>", unsafe_allow_html=True)
                    st.caption(f"Estoque: {row['estoque']} un")
                    
                    # Botão estilo App para incluir na Sacola
                    if st.button(f"➕ Adicionar", key=f"add_{row['codigo']}"):
                        st.session_state.carrinho.append({"codigo": row['codigo'], "nome": row['nome'], "preco": row['preco']})
                        st.rerun()
                        
                    st.markdown("</div>", unsafe_allow_html=True)

    with col_sacola:
        st.subheader("🛍️ Sacola de Compras")
        if not st.session_state.carrinho:
            st.caption("Sua sacola está vazia...")
        else:
            # Agrupa e exibe o resumo financeiro dos itens selecionados
            df_sacola = pd.DataFrame(st.session_state.carrinho)
            resumo_sacola = df_sacola.groupby('nome').agg(Qtd=('preco', 'count'), Total=('preco', 'sum')).reset_index()
            
            for _, item in resumo_sacola.iterrows():
                st.write(f"**{item['nome']}** x{item['Qtd']} — R$ {item['Total']:.2f}")
                
            total_geral = df_sacola['preco'].sum()
            st.markdown(f"### Total: <span style='color: #28A745;'>R$ {total_geral:.2f}</span>", unsafe_allow_html=True)
            
            forma_pagto = st.selectbox("Forma de Pagamento:", ["Pix", "Cartão de Débito", "Cartão de Crédito", "Dinheiro"])
            
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("Clear ❌", use_container_width=True):
                    st.session_state.carrinho = []
                    st.rerun()
            with col_b2:
                if st.button("Fechar Venda 💳", type="primary", use_container_width=True):
                    # Processamento documental e baixa no estoque
                    agora = datetime.now()
                    conn = sqlite3.connect("loja_doces.db")
                    cursor = conn.cursor()
                    for item in st.session_state.carrinho:
                        cursor.execute("UPDATE produtos SET estoque = estoque - 1 WHERE codigo=?", (item['codigo'],))
                    cursor.execute("INSERT INTO vendas (data, total, forma_pagto) VALUES (?, ?, ?)", (agora.strftime("%Y-%m-%d %H:%M:%S"), total_geral, forma_pagto))
                    conn.commit()
                    conn.close()
                    
                    # Emissão de Cupom em Bloco Texto (.txt)
                    num_fiscal = random.randint(100000, 999999)
                    with open(f"cupom_fiscal_{num_fiscal}.txt", "w", encoding="utf-8") as f:
                        f.write(f"CUPOM FISCAL SAT\nDATA: {agora.strftime('%d/%m/%Y')}\nFORMA: {forma_pagto.upper()}\nTOTAL: R$ {total_geral:.2f}")
                        
                    st.success(f"Venda Aprovada! Cupom Nº {num_fiscal} gerado.")
                    st.session_state.carrinho = []
                    st.loading = True
                    st.rerun()

# --- ABA 2: ALMOXARIFADO COM EDIÇÃO POR FORMULÁRIO ---
elif aba_selecionada == "📦 Almoxarifado":
    st.title("📦 Retaguarda e Almoxarifado")
    
    conn = sqlite3.connect("loja_doces.db")
    df_estoque = pd.read_sql_query("SELECT codigo, nome, preco, estoque, fabricacao, recebimento, vencimento, ativo FROM produtos", conn)
    conn.close()
    
    st.subheader("📋 Estoque Cadastrado")
    st.dataframe(df_estoque, use_container_width=True)
    
    st.markdown("---")
    st.subheader("✏️ Cadastro / Edição de Doces")
    
    # Seletor inteligente para carregar dados existentes para correção
    opcao_edicao = st.selectbox("Selecione um doce para EDITAR (ou escolha 'Cadastrar Novo'):", ["[ Novo Doce ]"] + list(df_estoque['nome']))
    
    dados_iniciais = {"codigo": "", "nome": "", "preco": 0.0, "estoque": 0, "fab": "", "rec": "", "venc": "", "ativo": "Sim"}
    if opcao_edicao != "[ Novo Doce ]":
        row_edicao = df_estoque[df_estoque['nome'] == opcao_edicao].iloc[0]
        dados_iniciais = {"codigo": row_edicao['codigo'], "nome": row_edicao['nome'], "preco": float(row_edicao['preco']), "estoque": int(row_edicao['estoque']), "fab": row_edicao['fabricacao'], "rec": row_edicao['recebimento'], "venc": row_edicao['vencimento'], "ativo": row_edicao['ativo']}
        
    with st.form("form_almoxarifado"):
        c1, c2, c3, c4 = st.columns(4)
        v_cod = c1.text_input("Código de Barras:", value=dados_iniciais["codigo"])
        v_nome = c2.text_input("Nome do Doce:", value=dados_iniciais["nome"])
        v_preco = c3.number_input("Preço de Venda:", value=dados_iniciais["preco"], min_value=0.0, step=0.1)
        v_qtd = c4.number_input("Quantidade Inicial:", value=dados_iniciais["estoque"], min_value=0, step=1)
        
        c5, c6, c7, c8 = st.columns(4)
        v_fab = c5.text_input("Fabricação (DD/MM/AA):", value=dados_iniciais["fab"])
        v_rec = c6.text_input("Recebimento (DD/MM/AA):", value=dados_iniciais["rec"])
        v_venc = c7.text_input("Vencimento (DD/MM/AA):", value=dados_iniciais["venc"])
        v_ativo = c8.selectbox("Disponível no Mural?", ["Sim", "Não"], index=0 if dados_iniciais["ativo"] == "Sim" else 1)
        
        v_foto = st.text_input("Caminho Local da Imagem/Foto (.png/.jpg):", placeholder="Ex: C:/imagens/brigadeiro.png")
        
        btn_gravar = st.form_submit_button("💾 Salvar Permanentemente no Almoxarifado")
        
        if btn_gravar:
            if not v_cod or not v_nome:
                st.error("Código e Nome são obrigatórios!")
            else:
                conn = sqlite3.connect("loja_doces.db")
                cursor = conn.cursor()
                try:
                    cursor.execute("INSERT INTO produtos VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (v_cod, v_nome, v_preco, v_qtd, v_fab, v_rec, v_venc, v_foto, v_ativo))
                except:
                    cursor.execute("UPDATE produtos SET nome=?, preco=?, estoque=?, fabricacao=?, recebimento=?, vencimento=?, imagem=?, ativo=? WHERE codigo=?", (v_nome, v_preco, v_qtd, v_fab, v_rec, v_venc, v_foto, v_ativo, v_cod))
                conn.commit()
                conn.close()
                st.success("Dados gravados com sucesso!")
                st.rerun()

# --- ABA 3: RELATÓRIOS CRONOLÓGICOS ---
elif aba_selecionada == "📊 Relatórios Gerenciais":
    st.title("📊 Relatórios Gerenciais de Faturamento")
    
    periodo = st.radio("Selecione o filtro cronológico:", ["Diário", "Semanal", "Mensal", "Anual"], horizontal=True)
    
    conn = sqlite3.connect("loja_doces.db")
    df_vendas = pd.read_sql_query("SELECT data, total FROM vendas", conn)
    conn.close()
    
    faturamento_total = 0.0
    hoje = datetime.now().date()
    
    for idx, row in df_vendas.iterrows():
        try: d_venda = datetime.strptime(row['data'], "%Y-%m-%d %H:%M:%S").date()
        except: continue
        
        if periodo == "Diário" and d_venda == hoje: faturamento_total += row['total']
        elif periodo == "Semanal" and d_venda >= (hoje - timedelta(days=7)): faturamento_total += row['total']
        elif periodo == "Mensal" and d_venda.month == hoje.month and d_venda.year == hoje.year: faturamento_total += row['total']
        elif periodo == "Anual" and d_venda.year == hoje.year: faturamento_total += row['total']
        
    st.metric(label=f"Faturamento Real Registrado ({periodo})", value=f"R$ {faturamento_total:.2f}")
    st.subheader("Histórico Recente Eletrônico SAT")
    st.dataframe(df_vendas, use_container_width=True)
