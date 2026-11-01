# Da Roça Inteligente – Sistema Inteligente de Gestão de Estoque com IA

Projeto acadêmico desenvolvido no curso de **Análise e Desenvolvimento de Sistemas – UNIBALSAS**, integrando conceitos de desenvolvimento web, análise de dados e apoio inteligente à gestão de estoque.

## Sobre o projeto

O projeto tem como objetivo desenvolver um sistema inteligente para auxiliar a empresa **Da Roça – Agropecuária & Pet** no controle de estoque e na identificação antecipada de produtos que podem necessitar de reposição.

A proposta utiliza dados de vendas, estoque e demanda para gerar informações que auxiliem na tomada de decisões.

## Problema identificado

A empresa apresenta dificuldades no acompanhamento do estoque, na identificação de produtos com maior saída e na reposição antecipada de mercadorias.

O projeto busca utilizar análise de dados e técnicas de Inteligência Artificial como apoio à gestão de estoque.

## Solução proposta e MVP

O MVP prevê um sistema capaz de:

- cadastrar e consultar produtos;
- acompanhar informações de estoque;
- analisar dados de vendas;
- identificar produtos com maior saída;
- identificar produtos com estoque baixo;
- gerar alertas de necessidade de reposição;
- utilizar dados históricos para apoiar previsões de demanda;
- fornecer informações para auxiliar a tomada de decisão.

## Base de dados

Foi selecionado o **Retail Store Inventory Forecasting Dataset**, disponibilizado no Kaggle.

A base utilizada possui **73.100 registros e 15 variáveis**, relacionadas a produtos, estoque, vendas, demanda, preços, descontos, promoções e outros fatores.

A base é utilizada para fins acadêmicos e para desenvolvimento e validação da abordagem proposta.

## TED 01 – Definição do problema e seleção da base

Na primeira etapa do projeto foram realizados:

- definição do problema;
- definição da solução proposta;
- definição inicial do MVP;
- pesquisa e seleção da base de dados;
- descrição das principais variáveis;
- análise preliminar da qualidade dos dados;
- identificação de limitações;
- relação entre a base selecionada e o problema do projeto.

Os documentos referentes à TED 01 estão disponíveis na pasta `docs/`.

## TED 02 – Limpeza, Saneamento e Análise Exploratória

Na segunda etapa foi realizado o processo de preparação e compreensão dos dados.

As principais atividades realizadas foram:

- carregamento e inspeção da base;
- verificação dos tipos de dados;
- identificação de valores ausentes;
- identificação de registros duplicados;
- análise de valores inconsistentes ou inválidos;
- investigação de possíveis outliers;
- tratamento e preparação dos dados;
- geração de estatísticas descritivas;
- análise da distribuição das principais variáveis;
- investigação das relações entre variáveis;
- geração de gráficos;
- interpretação dos resultados;
- relação dos resultados com o problema e o MVP do projeto.

### Principais resultados

A análise foi realizada sobre **73.100 registros**.

Foram identificados:

- **0 valores ausentes**;
- **0 registros totalmente duplicados**;
- **673 valores negativos** na variável `Demand Forecast`.

Como `Demand Forecast` representa uma quantidade prevista de demanda, os valores negativos foram considerados inconsistentes para o contexto do projeto e ajustados para **0** na versão tratada da base.

Os possíveis valores extremos foram analisados antes de qualquer decisão de tratamento, evitando exclusões automáticas sem justificativa.

## TED 03 e TED 04 – Back-end, integração e versão final

Nestas etapas o protótipo visual foi transformado em uma **aplicação web funcional**: o back-end em **Flask** implementa as regras de negócio, a persistência em banco de dados, a autenticação/autorização e uma API REST documentada, e a interface consome essa API (não há mais dados fictícios).

> **Mudança em relação ao planejamento (TED 1/2):** o planejamento previa Django; o back-end foi implementado em **Flask**, por ser mais leve, simples de executar em qualquer máquina e de publicar. A justificativa completa consta no Documento Técnico v3.0.

### Funcionalidades implementadas

- **Autenticação** por e-mail/senha com token assinado (Bearer, 8 h), senhas com hash PBKDF2-SHA256 e bloqueio temporário após 5 tentativas inválidas;
- **Autorização por perfil**: `OPERADOR`, `GESTOR` e `ADMINISTRADOR`, e tela de **gestão de usuários** (administrador);
- **Produtos**: cadastro, edição, desativação lógica, busca sem distinção de acentos, filtro por situação e paginação;
- **Movimentações de estoque** (entrada e saída) com saldo atualizado de forma atômica, bloqueio de saída acima do saldo e livro imutável (garantido também por triggers no banco);
- **Recomendações de reposição explicáveis**: previsão de demanda por média ponderada, cobertura em dias, ponto de pedido, quantidade sugerida e justificativa em português; o gestor aceita ou ignora cada sugestão;
- **Dashboard** com indicadores reais (produtos, estoque baixo, vendas e faturamento do mês, saídas dos últimos 7 dias, mais vendidos, itens que exigem ação);
- **Fornecedores e categorias** (o prazo de entrega do fornecedor alimenta a previsão);
- **Documentação interativa da API** (Swagger UI) e coleção Postman;
- **Importação da base da TED 02** (73 mil registros) para o banco.

### Arquitetura

```text
 Navegador (HTML/CSS/JS)  ──HTTP/JSON + Bearer──►  Flask: Blueprint /api  (agroestoque/api.py)
                                                        │
                                  regras de negócio ◄───┤  agroestoque/servicos.py
                                  motor de análise  ◄───┤  agroestoque/analise.py (Python puro)
                                                        ▼
                                            sqlite3 ──► SQLite (instance/agroestoque.sqlite3)
```

| Camada | Arquivos | Responsabilidade |
|---|---|---|
| Apresentação | `agroestoque/templates`, `agroestoque/static` | Interface (SPA em JavaScript puro) |
| API | `agroestoque/api.py`, `auth.py`, `validacao.py`, `erros.py` | Rotas, autenticação, autorização, validação, erros padronizados |
| Serviços | `agroestoque/servicos.py` | Regras de negócio e transações |
| Análise | `agroestoque/analise.py` | Previsão de demanda e classificação de risco |
| Persistência | `database/schema.sql`, `agroestoque/db.py` | Esquema, restrições, transações |

### Modelo de dados

`categoria 1─N produto N─1 fornecedor` · `produto 1─N movimentacao N─1 usuario` · `produto 1─N recomendacao`.
Script de criação em [`database/schema.sql`](database/schema.sql); consultas de auditoria em [`database/consultas_uteis.sql`](database/consultas_uteis.sql). Datas ficam em UTC e valores monetários em centavos (inteiros), evitando erros de arredondamento.

### Regras de negócio principais

1. O saldo do produto só muda por movimentações (nunca por edição direta).
2. Saída não pode exceder o saldo disponível (HTTP 422 `ESTOQUE_INSUFICIENTE`).
3. O motivo precisa ser compatível com o tipo (ex.: `VENDA` só em saída) — validado na API **e** no banco.
4. Produtos inativos não podem ser movimentados; a exclusão é lógica para preservar o histórico.
5. Movimentações são imutáveis; correções são feitas por novas movimentações.
6. Classificação de risco: **crítico** (sem estoque, saldo ≤ mínimo, ou cobertura menor que o prazo de entrega) e **atenção** (saldo ≤ 1,5 × mínimo ou ≤ ponto de pedido).
7. Demanda diária prevista = 60 % da média dos últimos 14 dias + 40 % da média dos últimos 30 dias (somente vendas).
8. Quantidade sugerida = demanda × (prazo de entrega + 15 dias) + estoque mínimo − saldo.

### Perfis de acesso

| Ação | Operador | Gestor | Administrador |
|---|:-:|:-:|:-:|
| Consultar produtos, dashboard, movimentações e recomendações | ✔ | ✔ | ✔ |
| Registrar movimentações | ✔ | ✔ | ✔ |
| Cadastrar/editar/desativar produtos, categorias, fornecedores | ✖ | ✔ | ✔ |
| Gerar análise e aceitar/ignorar recomendações | ✖ | ✔ | ✔ |
| Gerenciar usuários | ✖ | ✖ | ✔ |

## Como executar em localhost

Pré-requisito: **Python 3.10 ou superior**.

```bash
# 1) ambiente virtual
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows (PowerShell)
# source .venv/bin/activate         # Linux / macOS

# 2) dependências
pip install -r requirements.txt

# 3) carregar dados de demonstração (cria o banco, usuários, produtos e 60 dias de vendas)
flask --app agroestoque seed-demo

# 4) iniciar o servidor
python run.py
```

Acesse **http://127.0.0.1:5000/**. (Alternativa ao passo 4: `flask --app agroestoque run --debug`.)

Usuários de demonstração (senha `Agro@2026`; altere com `seed-demo --senha`):

| E-mail | Perfil |
|---|---|
| `gestor@daroca.com.br` | Gestor |
| `operador@daroca.com.br` | Operador |
| `admin@daroca.com.br` | Administrador (vê a aba **Usuários**) |

> A senha de demonstração é apenas para ambiente acadêmico. Em produção, crie usuários próprios (veja abaixo).

O banco SQLite é criado automaticamente em `instance/agroestoque.sqlite3` na primeira execução. Para recomeçar do zero, apague a pasta `instance/` ou use `seed-demo --limpar`.

### Comandos úteis

| Comando | O que faz |
|---|---|
| `flask --app agroestoque init-db` | Cria as tabelas (se não existirem) |
| `flask --app agroestoque seed-demo [--limpar] [--senha X]` | Carrega a demonstração |
| `flask --app agroestoque criar-usuario` | Cria um usuário (pergunta nome, e-mail, perfil e senha) |
| `flask --app agroestoque importar-base --dias 90 --loja S001` | Importa a base da TED 02 (`--limpar` reimporta) |

Na base importada o estoque cobre poucos dias de venda (característica da base sintética), então muitos itens aparecem como críticos — comportamento esperado.

### Testes automatizados

```bash
python -m unittest discover -s tests -v
```

São 72 testes: motor de análise, autenticação, autorização por perfil, validações, regras de estoque, recomendações, dashboard e segurança.

### Documentação da API

- Swagger UI: **http://127.0.0.1:5000/api-docs** (carrega o Swagger UI por CDN; requer internet)
- Especificação OpenAPI: [`docs/api/openapi.yaml`](docs/api/openapi.yaml)
- Coleção Postman/Insomnia: [`docs/api/AgroEstoque.postman_collection.json`](docs/api/AgroEstoque.postman_collection.json) (importe, execute o login e o token é salvo automaticamente). Para regenerá-la após mudar o OpenAPI: `python scripts/gerar_postman.py` (requer `pip install pyyaml`).

Exemplo rápido com `curl`:

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"gestor@daroca.com.br","senha":"Agro@2026"}' | python -c "import sys,json;print(json.load(sys.stdin)['token'])")

curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:5000/api/dashboard
```

| Método e rota | Descrição |
|---|---|
| `POST /api/auth/login` · `GET /api/auth/me` · `POST /api/auth/alterar-senha` | Autenticação |
| `GET/POST /api/usuarios` · `PATCH /api/usuarios/{id}` | Usuários (administrador) |
| `GET/POST /api/produtos` · `GET/PUT/PATCH/DELETE /api/produtos/{id}` | Produtos |
| `GET /api/produtos/{id}/analise` | Análise detalhada de reposição |
| `GET/POST /api/movimentacoes` | Entradas e saídas |
| `GET /api/dashboard` | Indicadores |
| `GET /api/recomendacoes` · `POST /api/recomendacoes/gerar` · `POST /api/recomendacoes/{id}/decidir` | Recomendações |
| `GET/POST /api/categorias` · `GET/POST /api/fornecedores` · `GET/PUT/DELETE /api/fornecedores/{id}` | Cadastros auxiliares |
| `GET /api/saude` | Verificação de disponibilidade |

Todos os erros seguem o formato `{"erro": {"codigo": "...", "mensagem": "...", "detalhes": {}}}`.

## Publicação na web (depois do localhost)

```bash
pip install -r requirements-deploy.txt
export AGROESTOQUE_PRODUCAO=1
export AGROESTOQUE_SECRET_KEY="<valor longo e aleatório>"      # obrigatório em produção
export AGROESTOQUE_DATABASE=/caminho/persistente/agroestoque.sqlite3
flask --app agroestoque init-db
flask --app agroestoque criar-usuario                          # primeiro administrador
gunicorn wsgi:app --bind 0.0.0.0:$PORT
```

| Variável | Uso |
|---|---|
| `AGROESTOQUE_PRODUCAO` | `1` exige `AGROESTOQUE_SECRET_KEY` (recusa subir sem ela) |
| `AGROESTOQUE_SECRET_KEY` | Chave que assina os tokens |
| `AGROESTOQUE_DATABASE` | Caminho do arquivo SQLite (use um disco **persistente**) |
| `HOST`, `PORT`, `FLASK_DEBUG` | Usadas por `python run.py` (padrão `127.0.0.1`, `5000`, `1`) |

Observações para a hospedagem: use HTTPS (o token trafega no cabeçalho `Authorization`); escolha um serviço que ofereça disco persistente, pois o SQLite é um arquivo; mantenha **um único processo/worker** do gunicorn (ou migre para PostgreSQL) porque o bloqueio de tentativas de login fica em memória.

## Organização do repositório

```text
sistema-agroestoque/
├── README.md
├── run.py  wsgi.py             # servidor local e entrada WSGI
├── requirements*.txt
├── agroestoque/                # aplicação Flask
│   ├── __init__.py             # fábrica create_app, erros e cabeçalhos
│   ├── api.py  auth.py  servicos.py  analise.py  db.py
│   ├── validacao.py  erros.py  serializers.py  util.py  cli.py  web.py  config.py
│   ├── templates/              # index.html, swagger.html
│   └── static/                 # app.css, app.js
├── database/                   # schema.sql, consultas_uteis.sql
├── tests/                      # test_analise.py, test_api.py
├── scripts/gerar_postman.py
├── docs/
│   ├── api/                    # openapi.yaml, coleção Postman
│   ├── prototipo/              # protótipo visual da etapa anterior
│   └── *.pdf                   # documentos das TEDs 01 e 02
├── data/                       # base bruta e tratada (TED 02)
└── notebooks/TED02/
```

## Tecnologias utilizadas

Python 3.10+ · Flask 3 · SQLite (`sqlite3`) · Werkzeug (hash de senhas) · itsdangerous (tokens assinados) · HTML5 · CSS3 · JavaScript (ES2020) · OpenAPI 3 / Swagger UI · Postman · Pandas, NumPy, Matplotlib e Jupyter (análise da TED 02) · Git e GitHub.

## Decisões técnicas

- **Flask + `sqlite3` da biblioteca padrão**: poucas dependências (apenas o Flask), fácil de instalar e de auditar; as regras ficam em `servicos.py`, isoladas da camada HTTP. A migração para SQLAlchemy/PostgreSQL é possível sem alterar a API.
- **Valores monetários em centavos (inteiro)** e datas em UTC: sem erros de arredondamento e sem ambiguidade de fuso.
- **Token assinado (Bearer) em vez de cookie de sessão**: simplifica o uso por Swagger/Postman e elimina o risco de CSRF na API. Os tokens expiram em 8 h e são invalidados quando a senha muda.
- **Motor de análise em Python puro**: previsão estatística explicável, sem "caixa-preta"; pode evoluir para modelos de aprendizado de máquina com a base da TED 02.
- **Defesa em profundidade**: as principais regras (saldo não negativo, motivo × tipo, imutabilidade do livro) são garantidas também por `CHECK` e triggers no banco.

## Limitações conhecidas

- O bloqueio de login usa memória do processo; com vários processos, use Redis ou outro armazenamento compartilhado.
- O Swagger UI é carregado por CDN (necessita internet).
- A seleção de produto na tela de movimentações lista até 100 itens.

## Equipe e contexto

Projeto da disciplina de projeto integrador – ADS/UNIBALSAS, em parceria com a Da Roça Agropecuária & Pet.
