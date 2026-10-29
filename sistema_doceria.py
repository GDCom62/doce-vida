import streamlit as st
import sqlite3
import time

# Configuração visual profissional da página da Doceria
st.set_page_config(page_title="CandySystem Web Pro", page_icon="🧁", layout="wide")

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

inicializar_banco()

# Gerenciamento de Estado da Sessão (Session State)
if 'usuario_logado' not in st.session_state:
    st.session_state.usuario_logado = None
if 'cargo_logado' not in st.session_state:
    st.session_state.cargo_logado = None
if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []

# =====================================================================
# 2. TELA DE LOGIN (Interface Web)
# =====================================================================
if st.session_state.usuario_logado is None:
    st.markdown("<h2 style='text-align: center; color: #5D4037;'>🧁 CandySystem Pro - Login</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("Formulário de Login"):
            usuario = st.text_input("Usuário:", value="caixa1")
            senha = st.text_input("Senha:", value="1234", type="password")
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
                    st.success("Login efetuado com sucesso!")
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
    st.stop()

# =====================================================================
# 3. INTERFACE PRINCIPAL APÓS LOGIN
# =====================================================================
st.markdown(f"<p style='float: right; font-weight: bold; color: #7D5A50;'>👤 Logado como: {st.session_state.usuario_logado.upper()} ({st.session_state.cargo_logado})</p>", unsafe_allow_html=True)
st.title("🧁 Doce Vida - Painel de Gestão")

aba_caixa, aba_adm, aba_clientes = st.tabs(["🛒 Frente de Caixa (PDV)", "📦 Almoxarifado / Estoque", "👥 Cadastro de Clientes"])

# -----------------------------------------------------------------
# ABA 1: FRENTE DE CAIXA
# -----------------------------------------------------------------
with aba_caixa:
    col_esq, col_dir = st.columns([1, 2])
    
    with col_esq:
        st.subheader("Entrada de Produto")
        
        # Entrada unificada para Leitores de Código, QR Code ou manual
        codigo_digitado = st.text_input("Bipar Código, QR ou Digitar Manual:", key="input_codigo")
        
        # Botão Simulação Comando de Voz
        if st.button("🎙️ Ativar Comando de Voz (Simulação Nuvem)"):
            st.warning("Ouvindo...")
            time.sleep(1.5)
            codigo_digitado = "7891000101"  # Força entrada do Brigadeiro
            st.success("Produto detectado por voz: Brigadeiro!")
            
        if codigo_digitado:
            conn = sqlite3.connect('doceria.db')
            cursor = conn.cursor()
            cursor.execute("SELECT codigo_barras, nome, preco, estoque FROM produtos WHERE codigo_barras = ?", (codigo_digitado,))
            produto = cursor.fetchone()
            conn.close()
            
            if produto:
                if produto[3] > 0:
                    st.session_state.carrinho.append({'codigo': produto[0], 'nome': produto[1], 'preco': produto[2], 'qtd': 1})
                    st.success(f"Adicionado: {produto[1]}")
                else:
                    st.error(f"O produto '{produto[1]}' está sem estoque!")
            else:
                st.error("Código não cadastrado.")
        
        # Exibição do total acumulado
        total_venda = sum(item['preco'] * item['qtd'] for item in st.session_state.carrinho)
        st.markdown(f"### Total do Pedido: <span style='color: #D32F2F;'>R$ {total_venda:.2f}</span>", unsafe_allow_html=True)
        
        if st.button("💸 Finalizar Venda", type="primary"):
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
                st.success("Venda concluída com sucesso!")
                st.rerun()
            else:
                st.warning("O carrinho está vazio.")
                
    with col_dir:
        st.subheader("Carrinho de Compras")
        if st.session_state.carrinho:
            st.table(st.session_state.carrinho)
            if st.button("🗑️ Limpar Carrinho"):
                st.session_state.carrinho = []
                st.rerun()
        else:
            st.info("Nenhum produto adicionado no momento.")

# -----------------------------------------------------------------
# ABA 2: ALMOXARIFADO / ESTOQUE
# -----------------------------------------------------------------
with aba_adm:
    if st.session_state.cargo_logado != "Gerente":
        st.error("🔒 Acesso Restrito. Apenas Gerentes podem acessar o Almoxarifado.")
    else:
        st.subheader("Gerenciamento do Almoxarifado")
        
        conn = sqlite3.connect('doceria.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, codigo_barras, nome, preco, estoque FROM produtos")
        produtos_lista = cursor.fetchall()
        conn.close()
        
        st.dataframe(produtos_lista, column_config={
            "0": "ID", "1": "Código de Barras", "2": "Nome", "3": "Preço de Venda", "4": "Estoque Atual"
        }, use_container_width=True)
        
        # Operações de Estoque
        col_adm1, col_adm2 = st.columns(2)
        with col_adm1:
            st.markdown("#### 📥 Dar Entrada de Mercadoria")
            with st.form("Entrada Estoque"):
                cod_entrada = st.text_input("Código de Barras:")
                qtd_entrada = st.number_input("Quantidade:", min_value=1, step=1)
                sub_entrada = st.form_submit_button("Registrar Entrada")
                
                if sub_entrada:
                    conn = sqlite3.connect('doceria.db')
                    cursor = conn.cursor()
                    cursor.execute("UPDATE produtos SET estoque = estoque + ? WHERE codigo_barras = ?", (qtd_entrada, cod_entrada))
                    if cursor.rowcount > 0:
                        st.success("Estoque reabastecido!")
                        conn.commit()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Produto não localizado.")
                    conn.close()

# -----------------------------------------------------------------
# ABA 3: CADASTRO DE CLIENTES
# -----------------------------------------------------------------
with aba_clientes:
    st.subheader("Cadastro de Clientes da Loja")
    
    with st.form("Novo Cliente"):
        nome_cli = st.text_input("Nome Completo:")
        cpf_cli = st.text_input("CPF:")
        tel_cli = st.text_input("Telefone:")
        sub_cli = st.form_submit_button("Cadastrar Cliente")
        
        if sub_cli and nome_cli:
            conn = sqlite3.connect('doceria.db')
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO clientes (nome, cpf, telefone) VALUES (?, ?, ?)", (nome_cli, cpf_cli, tel_cli))
                conn.commit()
                st.success("Cliente cadastrado com sucesso!")
            except sqlite3.IntegrityError:
                st.error("Este CPF já está cadastrado.")
            finally:
                conn.close()
                time.sleep(1)
                st.rerun()

    # Visualização em tempo real de todos os clientes cadastrados
    st.markdown("#### Clientes Cadastrados")
    conn = sqlite3.connect('doceria.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, cpf, telefone FROM clientes")
    clientes_lista = cursor.fetchall()
    conn.close()
    
    if clientes_lista:
        st.dataframe(clientes_lista, column_config={
            "0": "ID", "1": "Nome Completo", "2": "CPF", "3": "Telefone"
        }, use_container_width=True)
    else:
        st.info("Nenhum cliente cadastrado ainda.")
# =====================================================================
# 4. FUNÇÃO DO COMANDO DE VOZ INTEGRADO (Suporte para Nuvem/Navegador)
# =====================================================================
def processar_comando_voz(texto_ouvido):
    texto_ouvido = texto_ouvido.lower()
    codigo_detectado = None
    
    # Mapeamento inteligente de palavras-chave faladas para códigos
    if "brigadeiro" in texto_ouvido:
        codigo_detectado = "7891000101"
        st.toast("🧁 Brigadeiro Gourmet detectado por voz!", icon="🧁")
    elif "bolo" in texto_ouvido or "pote" in texto_ouvido:
        codigo_detectado = "7891000102"
        st.toast("🍰 Bolo de Pote detectado por voz!", icon="🍰")
    elif "palha" in texto_ouvido or "italiana" in texto_ouvido:
        codigo_detectado = "7891000103"
        st.toast("🍪 Palha Italiana detectada por voz!", icon="🍪")
        
    if codigo_detectado:
        conn = sqlite3.connect('doceria.db')
        cursor = conn.cursor()
        cursor.execute("SELECT codigo_barras, nome, preco, estoque FROM produtos WHERE codigo_barras = ?", (codigo_detectado,))
        produto = cursor.fetchone()
        conn.close()
        
        if produto:
            if produto[3] > 0:
                st.session_state.carrinho.append({'codigo': produto[0], 'nome': produto[1], 'preco': produto[2], 'qtd': 1})
                st.success(f"Adicionado via Voz: {produto[1]}")
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"O produto '{produto[1]}' está sem estoque!")
        else:
            st.error("Produto por voz não cadastrado no banco.")
    else:
        st.warning("Comando de voz não reconhecido. Tente falar o nome de um doce do cardápio.")
# Adiciona a interface do microfone no menu lateral (Sidebar) para fácil acesso
with st.sidebar:
    st.markdown("### 🎙️ Comandos Rápidos")
    
    # Nota: Em servidores de nuvem como o Streamlit Cloud, capturar áudio real do cliente
    # exige componentes de áudio do navegador (WebRTC). Usamos o botão inteligente para gatilho.
    teste_voz = st.text_input("Fale ou digite o comando de voz aqui (Ex: 'Quero brigadeiro'):")
    
    if st.button("🎙️ Processar Áudio"):
        if teste_voz:
            processar_comando_voz(teste_voz)
        else:
            # Simulação automática na ausência de entrada para fins de teste no servidor
            st.info("Simulando escuta do microfone...")
            time.sleep(1.5)
            processar_comando_voz("adicionar brigadeiro gourmet")
            
    st.markdown("---")
    if st.button("🚪 Sair do Sistema (Log Out)", type="secondary"):
        st.session_state.usuario_logado = None
        st.session_state.cargo_logado = None
        st.session_state.carrinho = []
        st.success("Sessão encerrada!")
        st.rerun()
