# Sistema Inteligente de Gestão de Estoque com Análise de Dados e Apoio à Reposição

Projeto acadêmico desenvolvido no curso de Análise e Desenvolvimento de Sistemas – UNIBALSAS, integrando desenvolvimento web, análise de dados, banco de dados e técnicas de aprendizado de máquina para apoiar a gestão de estoque.

---

## Sobre o projeto

O **Da Roça Inteligente – AgroEstoque** é um sistema web desenvolvido para auxiliar a empresa Da Roça – Agropecuária & Pet no acompanhamento do estoque e na identificação de produtos que possam necessitar de reposição.

A proposta surgiu a partir da identificação de dificuldades relacionadas à análise das informações de vendas, ao acompanhamento dos produtos e ao planejamento de compras.

Embora a empresa já utilize um sistema para registrar automaticamente as entradas e saídas de mercadorias, ainda existem atividades que dependem de consultas e análises realizadas pelos responsáveis.

Nesse contexto, o AgroEstoque propõe utilizar dados de produtos, movimentações e vendas para gerar indicadores, alertas e recomendações que auxiliem o processo de tomada de decisão.

O sistema foi desenvolvido em Python, utilizando Flask no back-end, SQLite para persistência dos dados e tecnologias web na construção da interface.

## Problema identificado

A partir do levantamento realizado no contexto da Da Roça – Agropecuária & Pet, foi identificado que o principal desafio não é a ausência de um sistema de controle, mas a dificuldade de utilizar as informações disponíveis para antecipar necessidades de reposição.

Entre os pontos identificados estão:

- Dificuldade para identificar antecipadamente produtos que precisam ser repostos;
- Necessidade de verificar o sistema para localizar produtos próximos de acabar;
- Dificuldade para identificar rapidamente os produtos com maior saída;
- Aproveitamento limitado do histórico de vendas no planejamento de compras;
- Necessidade de melhorar a comunicação relacionada ao acompanhamento do estoque.

Diante disso, o projeto busca responder à seguinte questão:

**Como utilizar Inteligência Artificial e análise de dados para melhorar o controle de estoque e auxiliar nas decisões de pedido de produtos?**

## Proposta e MVP

O MVP do AgroEstoque consiste em uma aplicação web que reúne informações de produtos, estoque e movimentações, oferecendo recursos para acompanhamento e análise.

Entre as funcionalidades implementadas ou previstas no projeto estão:

- Cadastro, edição e consulta de produtos;
- Acompanhamento das quantidades disponíveis em estoque;
- Registro de entradas e saídas;
- Consulta do histórico de movimentações;
- Análise dos dados de vendas;
- Identificação de produtos com maior saída;
- Identificação de produtos com estoque baixo;
- Geração de alertas de necessidade de reposição;
- Cálculo de estimativas de demanda;
- Recomendações de quantidades para solicitação;
- Apresentação de justificativas para apoiar a decisão do gestor;
- Dashboard com indicadores operacionais.

As recomendações funcionam como apoio à decisão, cabendo ao gestor avaliar e decidir sobre cada sugestão.

## Base de dados

Foi selecionado o **Retail Store Inventory Forecasting Dataset**, disponibilizado na plataforma Kaggle.

A base utilizada possui 73.100 registros e 15 variáveis, relacionadas a produtos, estoque, vendas, demanda, preços, descontos, promoções e outros fatores.

A base foi utilizada para atividades acadêmicas de preparação, análise exploratória e estudo do comportamento da demanda.

Sua utilização contribuiu para compreender as informações disponíveis e desenvolver abordagens de análise aplicadas ao projeto.

É importante destacar que se trata de uma base sintética, utilizada para fins acadêmicos, não representando integralmente o comportamento comercial real da empresa Da Roça.

---

## TED 01 — Identificação do problema e seleção da base

Na primeira etapa foram realizadas atividades de identificação e planejamento da solução.

As principais atividades foram:

- Definição do problema;
- Identificação do público-alvo;
- Definição da proposta de solução;
- Construção do planejamento inicial do MVP;
- Pesquisa e seleção da base de dados;
- Descrição das principais variáveis;
- Análise preliminar da qualidade dos dados;
- Identificação das limitações da base;
- Relação entre os dados selecionados e o problema do projeto;
- Elaboração do Lean Canvas.

A etapa estabeleceu a relação entre a necessidade identificada no contexto empresarial e a proposta de desenvolvimento do sistema.

Os documentos referentes ao TED 01 estão disponíveis na pasta `docs/`.

## TED 02 — Limpeza, saneamento e análise exploratória

Na segunda etapa foi realizado o processo de preparação e compreensão dos dados selecionados.

As principais atividades foram:

- Carregamento e inspeção da base;
- Verificação dos tipos de dados;
- Identificação de valores ausentes;
- Identificação de registros duplicados;
- Análise de valores inconsistentes ou inválidos;
- Investigação de possíveis valores extremos;
- Tratamento e preparação dos dados;
- Geração de estatísticas descritivas;
- Análise da distribuição das principais variáveis;
- Investigação das relações entre variáveis;
- Geração de gráficos;
- Interpretação dos resultados;
- Relação dos resultados com o problema e o MVP.

### Principais resultados

A análise foi realizada sobre 73.100 registros, com os seguintes resultados:

| Verificação | Resultado |
|---|---:|
| Registros analisados | 73.100 |
| Variáveis | 15 |
| Valores ausentes | 0 |
| Registros totalmente duplicados | 0 |
| Valores negativos em `Demand Forecast` | 673 |

Foram identificados 673 valores negativos na variável `Demand Forecast`.

Como essa variável representa uma quantidade prevista de demanda, os valores negativos foram considerados inconsistentes para o contexto do projeto e ajustados para zero na versão processada da base.

Os possíveis valores extremos foram analisados antes de qualquer decisão de tratamento, evitando exclusões automáticas sem justificativa.

Os documentos, análises e materiais dessa etapa estão organizados na pasta `docs/` e nos diretórios destinados a dados e notebooks.

## TED 03 — Modelagem Preditiva e Machine Learning

Na terceira etapa foi desenvolvido um estudo de modelagem preditiva com o objetivo de utilizar técnicas de aprendizado de máquina para estimar a quantidade de unidades vendidas no dia seguinte.

A proposta foi ampliar as análises realizadas no TED 02, utilizando o histórico de vendas e outras informações disponíveis na base para avaliar a capacidade de previsão de um modelo computacional.

### Objetivo do modelo

O modelo tem como objetivo prever a variável `Units Sold`, representando a quantidade de unidades vendidas, considerando informações históricas de cada combinação de loja e produto.

A previsão pode contribuir futuramente para o planejamento de estoque e para a identificação de possíveis necessidades de reposição.

### Preparação dos dados e variáveis

Foram utilizadas informações históricas de vendas, identificadores de loja e produto, além de variáveis temporais.

Também foram criadas variáveis derivadas do histórico, como valores de vendas de períodos anteriores, permitindo que o modelo considerasse o comportamento passado.

A variável `Demand Forecast` foi excluída das variáveis de entrada para evitar possível vazamento de informação (*data leakage*), devido à sua forte correlação com `Units Sold`.

### Modelo utilizado

Foi utilizado o algoritmo **Random Forest Regressor**, uma técnica de aprendizado de máquina baseada na combinação de várias árvores de decisão.

O modelo foi escolhido para realizar uma tarefa de regressão, pois o objetivo é estimar um valor numérico correspondente à quantidade de unidades vendidas.

### Treinamento e avaliação

A divisão dos dados foi realizada respeitando a ordem cronológica, utilizando 80% dos registros para treinamento e 20% para teste.

Essa estratégia permite avaliar o modelo utilizando registros posteriores aos empregados durante o treinamento, aproximando a avaliação de uma situação de previsão temporal.

Também foi utilizado um modelo de referência (*baseline*), baseado nas vendas do dia anterior, para comparar o desempenho do Random Forest.

### Métricas de avaliação

Foram utilizadas três métricas principais:

- **MAE (Erro Absoluto Médio):** mede a média dos erros absolutos entre os valores previstos e reais.
- **RMSE (Raiz do Erro Quadrático Médio):** atribui maior peso aos erros de maior magnitude.
- **R² (Coeficiente de Determinação):** indica quanto da variação dos valores reais é explicada pelo modelo.

### Resultados obtidos

Os resultados obtidos durante a execução do notebook foram:

| Métrica | Random Forest | Baseline |
|---|---:|---:|
| MAE | 89,8715 | 119,7515 |
| RMSE | 109,0583 | 153,5053 |
| R² | -0,0151 | -1,0111 |

O modelo Random Forest apresentou resultados melhores que o baseline nas métricas MAE e RMSE.

Em comparação com o modelo de referência, houve redução aproximada de 25% no MAE e de 29% no RMSE.

Entretanto, o valor negativo de R² demonstra que o modelo ainda apresenta limitações na explicação da variação dos dados de teste.

Portanto, apesar da melhora em relação ao baseline, os resultados indicam que a capacidade preditiva ainda precisa ser aprimorada.

### Limitações e considerações

Os resultados devem ser interpretados considerando as características da base utilizada.

Entre as principais limitações estão:

- Utilização de dados sintéticos;
- Ausência de validação com o histórico real de vendas da empresa;
- Desempenho preditivo ainda limitado;
- Necessidade de testar outros algoritmos e configurações;
- Necessidade de avaliar o comportamento do modelo em diferentes produtos e lojas.

O modelo desenvolvido representa um estudo acadêmico de previsão de vendas e não deve ser considerado, nesta etapa, uma ferramenta validada para decisões reais de compra ou reposição.

### Arquivos e materiais do TED 03

Os materiais relacionados à modelagem preditiva estão organizados nos seguintes arquivos:

- `notebooks/TED03/TED03_Modelagem_Da_Roca.ipynb` — notebook com preparação, treinamento e avaliação do modelo;
- `TED03_metricas.csv` — resultados das métricas de avaliação;
- `TED03_previsoes_teste.csv` — valores reais e previstos no conjunto de teste;
- `TED03_real_vs_previsto.png` — gráfico de comparação entre valores reais e previstos;
- `TED03_distribuicao_erros.png` — gráfico da distribuição dos erros;
- `TED03_modelo_random_forest.joblib` — modelo treinado e salvo.

A etapa permitiu aplicar conceitos de aprendizado de máquina ao contexto do projeto, comparar resultados com uma referência simples e identificar pontos que precisam ser aprimorados em trabalhos futuros.

---

## Implementação do back-end, integração e evolução da aplicação

Durante a evolução do projeto, o protótipo visual foi transformado em uma aplicação web funcional.

O back-end desenvolvido em Flask implementa as regras de negócio, a persistência em banco de dados, a autenticação, a autorização e uma API REST documentada. A interface utiliza HTML, CSS e JavaScript para interagir com os serviços disponibilizados pela aplicação.

### Mudança tecnológica em relação ao planejamento inicial

O planejamento das primeiras etapas considerava a utilização do Django. Durante a evolução do projeto, a equipe adotou o Flask para implementar o back-end.

A mudança foi realizada considerando a estrutura da aplicação, a organização dos componentes e a simplicidade de execução e manutenção do projeto.

A implementação atual utiliza Flask, não Django.

## Funcionalidades

- **Autenticação:** acesso por e-mail e senha, com token assinado do tipo Bearer, validade de oito horas, senhas protegidas com hash PBKDF2-SHA256 e bloqueio temporário após cinco tentativas inválidas;
- **Autorização por perfil:** controle de permissões para `OPERADOR`, `GESTOR` e `ADMINISTRADOR`, incluindo gerenciamento de usuários pelo administrador;
- **Produtos:** cadastro, edição, desativação lógica, pesquisa sem distinção de acentos, filtros por situação e paginação;
- **Movimentações de estoque:** registro de entradas e saídas, atualização atômica do saldo, bloqueio de saídas acima da quantidade disponível e histórico imutável, protegido também por gatilhos no banco;
- **Recomendações de reposição:** estimativa de demanda por média ponderada, cobertura em dias, ponto de pedido, quantidade sugerida e justificativa em português;
- **Decisão do gestor:** possibilidade de aceitar ou ignorar recomendações;
- **Dashboard:** indicadores de produtos, estoque baixo, vendas e faturamento do mês, saídas dos últimos sete dias, produtos mais vendidos e itens que bloqueiam ações;
- **Fornecedores e categorias:** organização de cadastros e utilização do prazo de entrega do fornecedor nas estimativas;
- **Documentação da API:** Swagger UI e especificação OpenAPI;
- **Integração com Postman:** coleção para testes das rotas;
- **Importação de dados:** recurso para importar a base utilizada no TED 02 para o banco de dados.

---

## Arquitetura do sistema

A aplicação utiliza uma arquitetura organizada em camadas, separando a interface, a API, os serviços, o motor de análise e a persistência dos dados.

```text
Navegador (HTML/CSS/JS)
          |
          | HTTP/JSON + Bearer Token
          v
Flask — Blueprint / API
          |
          +------ agroestoque/api.py
          |
          +------ agroestoque/auth.py
          |
          +------ agroestoque/validacao.py
          |
          v
Regras de negócio
          |
          +------ agroestoque/servicos.py
          |
          v
Motor de análise
          |
          +------ agroestoque/analise.py
          |
          v
Persistência
          |
          +------ agroestoque/db.py
          |
          v
SQLite
instance/agroestoque.sqlite3
```

### Organização das camadas

| Camada | Arquivos | Responsabilidade |
|---|---|---|
| Interface | `agroestoque/templates`, `agroestoque/static` | Interface da aplicação |
| API | `api.py`, `auth.py`, `validacao.py`, `erros.py` | Rotas, autenticação, autorização e validações |
| Serviços | `servicos.py` | Regras de negócio e transações |
| Análise | `analise.py` | Estimativa de demanda e classificação de risco |
| Persistência | `database/schema.sql`, `db.py` | Estrutura, consultas e operações no banco |

A separação das responsabilidades facilita a manutenção, a organização do código e a evolução do sistema.

## Modelo de dados

O modelo de dados organiza as relações entre categorias, produtos, fornecedores, movimentações, usuários e recomendações.

Principais relacionamentos:

```text
categoria 1 ─── N produto
fornecedor 1 ── N produto
produto 1 ───── N movimentacao
usuario 1 ───── N movimentacao
produto 1 ───── N recomendacao
```

O script responsável pela estrutura do banco está em:

`database/schema.sql`

As consultas auxiliares para auditoria estão em:

`database/consultas_uteis.sql`

Os dados são armazenados em UTC e os valores financeiros são registrados em centavos, utilizando números inteiros para evitar erros de arredondamento.

## Regras de negócio principais

O sistema possui regras destinadas a preservar a consistência das informações e garantir o funcionamento adequado das operações.

1. O saldo do produto é alterado por meio de movimentações, e não por edição direta;
2. Uma saída não pode ultrapassar o saldo disponível;
3. O motivo da movimentação precisa ser compatível com seu tipo;
4. Produtos inativos não podem receber movimentações;
5. A desativação de produtos é lógica, preservando o histórico;
6. As movimentações são imutáveis; revisões devem ser realizadas por novas movimentações;
7. A classificação de risco considera o saldo, o estoque mínimo, a cobertura e o prazo de entrega;
8. A demanda diária prevista considera a média ponderada das vendas dos últimos 14 e 30 dias;
9. A quantidade sugerida considera a demanda estimada, o prazo de entrega, uma margem adicional de 15 dias, o estoque mínimo e o saldo disponível.

## Critérios de classificação de risco

| Classificação | Critério |
|---|---|
| Crítico | Sem estoque, saldo menor ou igual ao estoque mínimo ou cobertura inferior ao prazo de entrega |
| Atenção | Saldo menor ou igual a 1,5 vez o estoque mínimo ou menor ou igual ao ponto de pedido |

## Cálculo da demanda prevista

A estimativa da demanda diária utiliza:

- 60% da média de vendas dos últimos 14 dias;
- 40% da média de vendas dos últimos 30 dias.

A fórmula conceitual é:

```text
Demanda diária prevista =
(0,60 × média de vendas de 14 dias)
+
(0,40 × média de vendas de 30 dias)
```

## Cálculo da quantidade sugerida

```text
Quantidade sugerida =
Demanda diária prevista × (prazo de entrega + 15 dias)
+ estoque mínimo
− saldo disponível
```

A recomendação funciona como uma referência para o planejamento de compras. A decisão final permanece com o gestor.

## Perfis de acesso

O AgroEstoque possui três perfis de usuário, com permissões específicas.

| Ação | Operador | Gestor | Administrador |
|---|:---:|:---:|:---:|
| Consultar produtos | ✔ | ✔ | ✔ |
| Visualizar painel | ✔ | ✔ | ✔ |
| Consultar movimentações | ✔ | ✔ | ✔ |
| Consultar categorias | ✔ | ✔ | ✔ |
| Registrar movimentações | ✔ | ✔ | ✔ |
| Cadastrar e editar produtos | ✖ | ✔ | ✔ |
| Gerenciar categorias e fornecedores | ✖ | ✔ | ✔ |
| Gerar análises e recomendações | ✖ | ✔ | ✔ |
| Aceitar ou ignorar recomendações | ✖ | ✔ | ✔ |
| Gerenciar usuários | ✖ | ✖ | ✔ |

---

## Como executar em localhost

### Requisitos

- Python 3.10 ou superior;
- Git;
- Terminal ou PowerShell;
- Navegador.

### 1. Clonar o repositório

```bash
git clone https://github.com/pedroigor-instaplayer/sistema-agroestoque.git
```

### 2. Entrar na pasta do projeto

```bash
cd sistema-agroestoque
```

### 3. Criar o ambiente virtual

```bash
python -m venv .venv
```

### 4. Ativar o ambiente virtual

Windows — PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux ou macOS:

```bash
source .venv/bin/activate
```

### 5. Instalar as dependências

```bash
pip install -r requirements.txt
```

### 6. Carregar os dados de demonstração

```bash
flask --app agroestoque seed-demo
```

Esse comando prepara os dados de demonstração, incluindo o banco de dados, usuários, produtos, movimentações e recomendações.

### 7. Iniciar o servidor

```bash
python run.py
```

### 8. Acessar o sistema

Abra o navegador e acesse:

[http://127.0.0.1:5000/](http://127.0.0.1:5000/)

O servidor precisa permanecer em execução enquanto a aplicação estiver sendo utilizada.

### Usuários de demonstração

A senha padrão dos usuários de demonstração é:

`Agro@2026`

| E-mail | Perfil |
|---|---|
| `gestor@daroca.com.br` | Gestor |
| `operador@daroca.com.br` | Operador |
| `admin@daroca.com.br` | Administrador |

A conta de administrador possui acesso à funcionalidade de gerenciamento de usuários.

> Atenção: as credenciais são destinadas exclusivamente à demonstração acadêmica. Não utilize uma senha padrão em um ambiente de produção.

O banco SQLite é criado automaticamente:

`instance/agroestoque.sqlite3`

Importante: o comando `seed-demo` carrega os dados de demonstração. A opção `--limpar` deve ser utilizada somente quando houver intenção de limpar os dados existentes. Antes de qualquer operação de limpeza, faça uma cópia de segurança do banco.

## Comandos

| Comando | Finalidade |
|---|---|
| `flask --app agroestoque init-db` | Cria as tabelas, caso ainda não existam |
| `flask --app agroestoque seed-demo` | Carrega os dados de demonstração |
| `flask --app agroestoque seed-demo --limpar` | Recarrega a demonstração com limpeza dos dados anteriores |
| `flask --app agroestoque criar-usuario` | Cria um usuário informando nome, e-mail, perfil e senha |
| `flask --app agroestoque importar-base --dias 90 --loja S001` | Importa a base do TED 02 |

Para consultar as opções adicionais de cada comando, utilize a opção `--help` disponibilizada pelo Flask.

Na base importada, o estoque cobre poucos dias de venda, característica da base sintética utilizada. Por esse motivo, diversos produtos podem aparecer classificados como críticos. Esse comportamento deve ser interpretado considerando as características dos dados utilizados.

## Testes automatizados

O projeto possui testes automatizados organizados no diretório `tests/`.

Para executar os testes:

```bash
python -m unittest discover -s tests -v
```

A suíte documentada contempla 72 testes, relacionados a:

- Motor de análise;
- Autenticação;
- Autorização por perfil;
- Validações;
- Consistência de estoque;
- Recomendações;
- Painel;
- Segurança.

Os testes auxiliaram na verificação das regras de negócio e na identificação de falhas durante a evolução da aplicação.

## Documentação da API

A aplicação disponibiliza uma API REST para comunicação entre a interface e o back-end.

A documentação interativa pode ser acessada pelo endereço:

[http://127.0.0.1:5000/api-docs](http://127.0.0.1:5000/api-docs)

A interface Swagger UI é fornecida por CDN e precisa de conexão com a internet.

### Arquivos de documentação

- OpenAPI: `docs/api/openapi.yaml`
- Coleção Postman: `docs/api/AgroEstoque.postman_collection.json`

A coleção pode ser importada no Postman ou Insomnia para executar e testar as rotas da aplicação.

Para regenerar a coleção Postman após alterações no OpenAPI:

```bash
pip install pyyaml
python scripts/gerar_postman.py
```

## Exemplo de autenticação com cURL

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"gestor@daroca.com.br","senha":"Agro@2026"}' \
  | python -c "import sys,json;print(json.load(sys.stdin)['token'])")
```

Consulta do dashboard utilizando o token:

```bash
curl -H "Authorization: Bearer $TOKEN" \
http://127.0.0.1:5000/api/dashboard
```

## Principais rotas da API

| Método e rota | Descrição |
|---|---|
| `POST /api/auth/login` | Autenticação |
| `GET /api/auth/me` | Consulta do usuário autenticado |
| `POST /api/auth/alterar-senha` | Alteração de senha |
| `GET/POST /api/usuarios` | Consulta e cadastro de usuários |
| `PATCH /api/usuarios/{id}` | Atualização de usuário |
| `GET/POST /api/produtos` | Consulta e cadastro de produtos |
| `GET/PUT/PATCH/DELETE /api/produtos/{id}` | Operações sobre produtos |
| `GET /api/produtos/{id}/analise` | Análise detalhada da situação |
| `GET/POST /api/movimentacoes` | Consulta e registro de movimentações |
| `GET /api/dashboard` | Indicadores do sistema |
| `GET /api/recomendacoes` | Consulta de recomendações |
| `POST /api/recomendacoes/gerar` | Geração de recomendações |
| `POST /api/recomendacoes/{id}/decidir` | Decisão sobre recomendação |
| `GET/POST /api/categorias` | Consulta e cadastro de categorias |
| `GET/POST /api/fornecedores` | Consulta e cadastro de fornecedores |
| `GET/PUT/DELETE /api/fornecedores/{id}` | Operações sobre fornecedores |
| `GET /api/saude` | Verificação de disponibilidade |

Os erros da API seguem um formato padronizado:

```json
{
  "erro": {
    "codigo": "...",
    "mensagem": "...",
    "detalhes": {}
  }
}
```

---

## Publicação na web

A aplicação pode ser preparada para hospedagem em ambiente de produção, desde que sejam definidas as dependências e variáveis de ambiente necessárias.

O arquivo `requirements-deploy.txt` contém as dependências destinadas à implantação.

### Exemplo de configuração

```bash
pip install -r requirements-deploy.txt

export AGROESTOQUE_PRODUCAO=1

export AGROESTOQUE_SECRET_KEY="<valor longo e aleatório>"

export AGROESTOQUE_DATABASE="/caminho/persistente/agroestoque.sqlite3"

flask --app agroestoque init-db

flask --app agroestoque criar-usuario

gunicorn wsgi:app --bind 0.0.0.0:$PORT
```

No Windows, as variáveis de ambiente devem ser definidas de acordo com o terminal utilizado. O exemplo acima utiliza sintaxe de shell compatível com ambientes Linux.

### Variáveis de ambiente

| Variável | Finalidade |
|---|---|
| `AGROESTOQUE_PRODUCAO` | Ativa as configurações de produção |
| `AGROESTOQUE_SECRET_KEY` | Chave utilizada para assinar os tokens |
| `AGROESTOQUE_DATABASE` | Caminho do banco de dados SQLite |
| `HOST` | Endereço de inicialização do servidor |
| `PORT` | Porta de execução |
| `FLASK_DEBUG` | Controle do modo de depuração |

### Observações sobre hospedagem

- Utilize HTTPS para proteger a comunicação;
- Configure uma chave secreta longa e segura;
- Utilize armazenamento persistente para o banco SQLite;
- Mantenha uma configuração adequada de processos do Gunicorn;
- Para cenários com múltiplos processos ou maior concorrência, considere migrar para PostgreSQL e usar armazenamento compartilhado para o controle de tentativas de login.

O repositório no GitHub contém o código-fonte do projeto. Sua publicação no GitHub não significa que o aplicativo esteja automaticamente hospedado ou disponível na internet.

---

## Organização do projeto

```text
sistema-agroestoque/
│
├── README.md
├── run.py
├── wsgi.py
├── requirements.txt
├── requirements-deploy.txt
│
├── agroestoque/
│   ├── __init__.py
│   ├── api.py
│   ├── auth.py
│   ├── servicos.py
│   ├── analise.py
│   ├── db.py
│   ├── validacao.py
│   ├── erros.py
│   ├── serializers.py
│   ├── util.py
│   ├── cli.py
│   ├── web.py
│   ├── config.py
│   ├── templates/
│   └── static/
│
├── database/
│   ├── schema.sql
│   └── consultas_uteis.sql
│
├── tests/
│
├── scripts/
│   └── gerar_postman.py
│
├── docs/
│   ├── api/
│   │   ├── openapi.yaml
│   │   └── AgroEstoque.postman_collection.json
│   ├── prototipo/
│   └── documentos das TEDs
│
├── data/
│
└── notebooks/
    ├── TED02/
    └── TED03/
```

A estrutura apresenta os principais diretórios e arquivos do projeto. Os conteúdos internos podem ser ampliados conforme a evolução da implementação.

## Tecnologias utilizadas

| Tecnologia | Utilidade |
|---|---|
| Python 3.10+ | Linguagem principal |
| Flask 3 | Estrutura web |
| SQLite | Banco de dados |
| `sqlite3` | Comunicação com o banco |
| Werkzeug | Segurança e hash de senhas |
| itsdangerous | Assinatura de tokens |
| HTML5 | Estrutura da interface |
| CSS3 | Estilização |
| JavaScript ES2020 | Interatividade e comunicação com a API |
| OpenAPI 3 | Documentação da API |
| Swagger UI | Documentação interativa |
| Postman | Testes das rotas |
| Pandas | Análise e manipulação de dados |
| NumPy | Operações numéricas |
| Matplotlib | Visualização de dados |
| Scikit-learn | Desenvolvimento e avaliação de modelos de Machine Learning |
| Jupyter Notebook | Desenvolvimento das análises e modelos |
| Git | Controle de versão |
| GitHub | Gerenciamento e compartilhamento do código |

## Decisões técnicas

- **Flask e sqlite3:** utilização de um framework web e da biblioteca de banco de dados disponível na biblioteca padrão do Python, mantendo a aplicação organizada e com poucas dependências;
- **Separação das responsabilidades:** regras de negócio isoladas da camada HTTP, facilitando a manutenção e a evolução do sistema;
- **Valores financeiros em centavos:** armazenamento com números inteiros para evitar problemas de arredondamento;
- **Dados em UTC:** padronização das informações temporais;
- **Token Bearer:** autenticação adequada à comunicação entre a interface, a API, o Swagger e o Postman;
- **Motor de análise em Python:** utilização de cálculos estatísticos explicáveis para apresentar estimativas e recomendações;
- **Aprendizado de máquina:** utilização do Random Forest Regressor em estudo experimental de previsão de vendas;
- **Defesa em profundidade:** aplicação de validações tanto na API quanto no banco de dados, incluindo restrições e gatilhos.

## Limitações conhecidas

A versão atual possui algumas limitações técnicas que devem ser consideradas:

- O bloqueio de tentativas de login utiliza memória do processo; em ambientes com múltiplos processos, recomenda-se armazenamento compartilhado;
- O Swagger UI é carregado por CDN e precisa de internet;
- A seleção de produtos na tela de movimentações apresenta até 100 itens;
- A estimativa de demanda depende da qualidade e da disponibilidade do histórico de vendas;
- A base utilizada no TED 02 e no TED 03 é sintética e não representa integralmente o comportamento comercial real da Da Roça;
- O modelo Random Forest apresentou resultados melhores que o baseline, mas ainda possui limitações preditivas, incluindo R² negativo no conjunto de teste;
- O modelo de Machine Learning ainda não está integrado ao fluxo operacional de recomendações do sistema.

Essas limitações representam pontos que podem ser considerados em evoluções futuras.

## Possibilidades de evolução

Entre as possibilidades de continuidade do AgroEstoque estão:

- Aprimoramento dos métodos de previsão de demanda;
- Avaliação de outras técnicas de aprendizado de máquina;
- Integração entre o modelo preditivo e o sistema de estoque;
- Integração com sistemas de gestão utilizados pelos estabelecimentos;
- Ampliação de indicadores e relatórios;
- Melhorias na experiência de utilização;
- Validação das recomendações com dados reais;
- Avaliação da precisão das sugestões de reposição junto aos usuários.

Essas possibilidades representam propostas futuras, não devendo ser confundidas com funcionalidades já implementadas.

---

## Equipe e contexto

Projeto desenvolvido no curso de Análise e Desenvolvimento de Sistemas – UNIBALSAS, no contexto das atividades acadêmicas de desenvolvimento de software e projeto integrador.

**Instituição parceira:** Da Roça – Agropecuária & Pet.

**Equipe de desenvolvimento:**

- André Rocha;
- Michel Guido;
- Mickael Miranda;
- Pedro Igor;
- Dhonathan dos Santos.

**Professor:** Marcos David Souza Ramos.

---

## Considerações finais

O Da Roça Inteligente – AgroEstoque representa a aplicação prática de conhecimentos de desenvolvimento web, banco de dados, análise de dados e aprendizado de máquina na construção de uma solução voltada para uma necessidade identificada no contexto empresarial.

O projeto parte do reconhecimento de que o registro das movimentações, embora essencial, não resolve sozinho todas as dificuldades relacionadas ao planejamento de reposição. É necessário transformar as informações armazenadas em indicadores e análises que ajudem os responsáveis a compreender melhor a situação dos produtos.

A solução desenvolvida contribui para esse processo, organizando informações, apresentando alertas e disponibilizando recomendações para apoiar a tomada de decisão.

As atividades de modelagem preditiva ampliaram o estudo dos dados, permitindo experimentar um modelo de aprendizado de máquina e comparar seu desempenho com uma referência simples. Os resultados demonstraram avanços em algumas métricas, mas também evidenciaram a necessidade de melhorias e validação com dados reais.

Além de sua aplicação no contexto da Da Roça – Agropecuária & Pet, o projeto reúne conhecimentos técnicos e acadêmicos, envolvendo levantamento de requisitos, modelagem, programação, análise de dados, testes, documentação e controle de versão.

---

## Repositório

GitHub: https://github.com/pedroigor-instaplayer/sistema-agroestoque

**Da Roça Inteligente — AgroEstoque**

Tecnologia, análise de dados e informação a serviço de uma gestão de estoque mais eficiente.
