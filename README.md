# 📦 ERP Logística Visionary com IA Transacional

Este repositório contém um Sistema de Planeamento de Recursos Empresariais (ERP) focado em Supply Chain e Logística, potenciado por Inteligência Artificial. 

A aplicação não atua apenas como um painel de controlo (Dashboard), mas sim como um **Agente Autónomo** capaz de ler faturas em diferentes formatos, interagir com bases de dados SQL em tempo real e realizar faturamentos de forma autónoma através de um chat inteligente (Agentic Workflow).

## 🚀 Principais Automações e Funcionalidades

### 1. Workflow Agêntico (Vendas Autónomas)
Módulo focado na Torre de Comando, permitindo que o Administrador converse com a IA (Nvidia Nemotron 120B) para insights ou ações diretas.
* **Interceção de Intenções:** Lê o chat humano e identifica intenções de compra (ex: *"Quero 10 Maçãs para a Zona Sul"*).
* **Faturação em Background:** Cria automaticamente o payload JSON do pedido por debaixo dos panos.
* **Roteamento em Tempo Real:** O sistema processa o JSON da IA, emite a Nota Fiscal (DANFE visual) e notifica o fornecedor correspondente instantaneamente na base de dados.

### 2. Extração Híbrida de Documentos (Inbound)
Motor de processamento de Notas Fiscais de entrada (Upload) à prova de falhas.
* **Leitura Nativa (PDFs Digitais):** Extração ultrarrápida de texto utilizando `PyMuPDF (fitz)`.
* **Fallback Visual (OCR + LLM):** Deteção automática de documentos digitalizados ou imagens. O sistema converte o ficheiro e aciona o modelo **Llama 3.2 Vision** para extrair tabelas e itens.
* **Auditoria Financeira:** Cruza a soma dos itens extraídos com o valor total da nota para bloquear furos logísticos.

### 3. Arquitetura Multi-Perfil (Portais Dedicados)
Sistema de login com renderização de páginas e menus baseados em permissões (RBAC).
* **⚙️ Admin:** Visão total do negócio, acesso à Torre de Comando (IA), Dashboards de BI e Gestão de Master Data.
* **🏪 Cliente:** Acesso restrito para fazer pedidos, cálculo de risco/prazo e acompanhamento de status.
* **🏭 Fornecedor:** Painel dedicado para receber pedidos, atualizar status logístico (Em Trânsito, Entregue, Recusado) e fazer upload de notas.

### 4. Arquitetura de Base de Dados Dupla
Separação de responsabilidades (Segregação de Dados) utilizando o SQLite.
* **Master Data (`db_cadastros.db`):** Armazena Entidades estáticas (Utilizadores, Fornecedores, Catálogo de Produtos).
* **Transacional (`db_operacional.db`):** Armazena Eventos (Fluxo Inbound/Outbound, Histórico de NFs e Logs).

---

## 🛠️ Tecnologias Utilizadas

* **Python 3.10+**
* **Streamlit** (Framework Frontend e Controlo de Estado UI)
* **Google/OpenRouter API** (`nvidia/nemotron-3-super-120b-a12b:free` e `meta-llama/llama-3.2-11b-vision-instruct:free`)
* **SQLite3** (Gestão de base de dados relacional local)
* **PyMuPDF / fitz** (Manipulação e leitura de binários PDF)
* **Pandas** (Estruturação e limpeza de DataFrames para visualização de BI)

---

## ⚙️ Como Instalar e Usar

1. Clone o repositório para a sua máquina local:
   ```bash
   git clone [https://github.com/teu-utilizador/erp-visionary.git](https://github.com/teu-utilizador/erp-visionary.git)
   cd erp-visionary
