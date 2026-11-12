# 🛒 Dominus PDV - Sistema de Frente de Caixa e Gestão de Estoque

O **Dominus PDV** é uma aplicação web completa de Ponto de Venda (PDV), controle de almoxarifado, cadastro de clientes/equipe e relatórios gerenciais, desenvolvida em **Python** com **Streamlit** e **SQLite**.

O sistema foi projetado com foco em **simplicidade, acessibilidade e alta legibilidade**, utilizando fluxo linear em etapas numeradas, fontes ampliadas e botões de destaque para facilitar a operação no dia a dia.

---

## ✨ Funcionalidades Principais

### 1. 🛒 Frente de Caixa (PDV Acessível)
* **Fluxo Linear em 3 Passos:**
  1. **Escolher Produto:** Leitura rápida por código de barras ou seleção inteligente em cascata por **Produto Base** (ex: *Chocolate Joaozinho*) e **Variação/Sabor** (ex: *Chocolate Branco*).
  2. **Conferir Itens da Compra:** Tabela limpa com numeração sequencial, descrição, quantidade, preço unitário e valor total, com opções de cancelamento de item ou venda recolhidas para evitar cliques acidentais.
  3. **Pagamento e Fechamento:** Visor de alto contraste para o total a pagar e suporte a **pagamento dividido** (Dinheiro, Pix, Débito e Crédito simultâneos).
* **Cálculos Automáticos e Travas:** Calcula automaticamente o subtotal, descontos (por item ou no total), valor recebido, valor restante e troco, impedindo que pagamentos eletrônicos (Pix/Cartão) ultrapassem o valor da venda.
* **Emissão de Recibo:** Gera comprovante não fiscal formatado imediatamente após a finalização da venda, pronto para visualização na tela ou download em `.txt` para impressão.

### 2. 📦 Almoxarifado / Estoque
* Cadastro e abastecimento de produtos organizados por **Linha/Produto Base** e **Variação**.
* Atualização automática de saldo (baixa imediata ao finalizar vendas no PDV e soma nas entradas de lote).
* Painel de alertas para itens com estoque igual ou abaixo do nível mínimo configurado.

### 3. 👥 Cadastros (Clientes e Equipe)
* **Clientes Fidelidade:** Registro de nome completo, CPF (com validação de duplicidade) e telefone.
* **Funcionários & Cargos:** Controle de acesso individual com login, senha e nível operacional (*Operador de Caixa*, *Gerente* ou *Almoxarife*).

### 4. 📊 Relatórios de Vendas
* Indicadores de faturamento total acumulado e dias operacionais registrados.
* Gráfico interativo de evolução do faturamento diário.
* Histórico completo de cupons finalizados com detalhamento de descontos e formas de pagamento.

### 5. 💾 Segurança e Backup de Dados
* Ferramenta integrada no menu lateral para **baixar o arquivo do banco de dados (`.db`)** a qualquer momento e **restaurar backups** com um clique, garantindo a persistência dos dados em ambientes em nuvem como o Streamlit Cloud.

---

## 🛠️ Tecnologias Utilizadas

* **Python 3.10+**
* **Streamlit** (Interface web interativa e responsiva)
* **SQLite3** (Banco de dados relacional leve e local)
* **Pandas** (Manipulação de tabelas, relatórios e exibição de dados)

---

## 📁 Estrutura de Arquivos

```text
doce-vida/
├── mainb.py                                   # Código-fonte principal da aplicação
├── logo_empresa.png                           # Logotipo exibido no login e menu lateral (opcional)
├── requirements.txt                           # Dependências do projeto
├── README.md                                  # Documentação do sistema
└── banco_dados/
    └── estoque_loja_independente.db           # Banco de dados SQLite (gerado automaticamente)
```

---

## 🚀 Como Executar o Projeto Localmente

### 1. Pré-requisitos
Certifique-se de ter o **Python** instalado em sua máquina. Clone este repositório ou baixe os arquivos para uma pasta local.

### 2. Instalar as Dependências
No terminal, dentro da pasta do projeto, execute:

```bash
pip install streamlit pandas
```
*(Ou utilize `pip install -r requirements.txt` caso possua o arquivo de dependências).*

### 3. Adicionar o Logotipo (Opcional)
Para exibir a marca da sua loja na tela de login e no topo do menu lateral, salve a imagem com o nome exato **`logo_empresa.png`** na mesma pasta do arquivo `mainb.py`.

### 4. Iniciar o Sistema
Execute o comando abaixo no terminal:

```bash
streamlit run mainb.py
```

O sistema abrirá automaticamente no seu navegador padrão (geralmente em `http://localhost:8501`).

---

## 🔐 Credenciais de Primeiro Acesso

Na primeira execução, o banco de dados cria automaticamente um usuário administrador padrão e alguns produtos de exemplo:

* **Usuário:** `admin`
* **Senha:** `admin123`

> **Dica de Segurança:** Após o primeiro acesso, acesse o módulo **👥 Cadastros (Clientes/Equipe)** para registrar os operadores da loja.

---

## ⚠️ Nota sobre Hospedagem no Streamlit Cloud

Em servidores gratuitos como o **Streamlit Community Cloud**, o sistema de arquivos local pode ser reiniciado após períodos de inatividade ou novas atualizações no GitHub. Utilize regularmente a opção **📥 Baixar Backup (`.db`)** na barra lateral ao final do expediente para manter uma cópia de segurança dos seus registros.
# doce-vida
Controle de vendas da Doce Vida

Desenvolvedor GDCom
