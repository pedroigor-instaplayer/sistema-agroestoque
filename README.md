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

## Desenvolvimento da Interface da Aplicação

Nesta etapa foi desenvolvida e organizada a interface web do **Sistema AgroEstoque**, seguindo a proposta definida para o projeto.

A aplicação foi estruturada utilizando o framework **Django**, com separação entre configurações do projeto, aplicação de estoque, templates e arquivos estáticos.

A interface desenvolvida contempla:

- tela de acesso ao sistema;
- dashboard com indicadores de estoque e movimentações;
- visualização de produtos;
- formulário demonstrativo para cadastro de produtos;
- pesquisa de produtos;
- identificação visual da situação do estoque;
- registro demonstrativo de entradas e saídas;
- histórico de movimentações;
- recomendações de reposição;
- justificativas para as recomendações apresentadas;
- navegação responsiva para diferentes tamanhos de tela.

Nesta versão acadêmica, parte das informações apresentadas na interface é demonstrativa e tem como objetivo validar a navegação, a organização visual e a experiência do usuário.

## Arquitetura da aplicação

O projeto utiliza uma estrutura baseada no padrão adotado pelo Django.

O módulo `sistema_agroestoque` contém as configurações principais da aplicação, enquanto o módulo `estoque` concentra os componentes relacionados ao gerenciamento de estoque.

A interface está armazenada na pasta de templates e é renderizada pelo Django por meio da view inicial da aplicação.

## Organização do repositório

```text
sistema-agroestoque/
├── README.md
├── requirements.txt
├── .gitignore
├── manage.py
├── sistema_agroestoque/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── estoque/
│   ├── migrations/
│   │   └── __init__.py
│   ├── templates/
│   │   └── index.html
│   ├── static/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── urls.py
│   ├── views.py
│   └── tests.py
├── data/
│   ├── raw/
│   │   └── retail_store_inventory.csv
│   └── processed/
│       └── retail_store_inventory_processed.csv
├── notebooks/
│   └── TED02/
│       └── TED02_limpeza_eda.ipynb
├── docs/
└── index.html
```

## Tecnologias utilizadas

- Python
- Django
- SQLite
- HTML5
- CSS3
- JavaScript
- Pandas
- NumPy
- Matplotlib
- Jupyter Notebook
- Git
- GitHub

## Instalação

Para executar o projeto localmente, é necessário possuir o **Python** instalado.

Clone o repositório:

```bash
git clone https://github.com/pedroigor-instaplayer/sistema-agroestoque.git
```

Entre na pasta do projeto:

```bash
cd sistema-agroestoque
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

## Execução da aplicação

Com as dependências instaladas, execute:

```bash
python manage.py migrate
```

Em seguida:

```bash
python manage.py runserver
```

O Django iniciará o servidor de desenvolvimento. A aplicação poderá ser acessada pelo endereço informado no terminal, normalmente:

```text
http://127.0.0.1:8000/
```

## Utilização da aplicação

Ao acessar a aplicação, será apresentada a tela inicial do **AgroEstoque**.

Na versão demonstrativa da interface, o usuário pode:

1. acessar o sistema pela tela de entrada;
2. visualizar os principais indicadores no dashboard;
3. navegar até a área de produtos;
4. pesquisar e visualizar produtos;
5. abrir o formulário demonstrativo de cadastro;
6. acessar a área de movimentações;
7. simular entradas e saídas de estoque;
8. consultar recomendações de reposição.

Os dados exibidos na interface são utilizados para demonstração e validação do MVP acadêmico.

## Reprodutibilidade da análise de dados

A base original utilizada no projeto está disponível em:

`data/raw/retail_store_inventory.csv`

A versão preparada após o processo de limpeza está disponível em:

`data/processed/retail_store_inventory_processed.csv`

O código utilizado para limpeza, preparação, estatísticas e análise exploratória está disponível em:

`notebooks/TED02/TED02_limpeza_eda.ipynb`

## Histórico de desenvolvimento

O histórico de commits do repositório registra a evolução do projeto, incluindo a preparação dos dados, documentação, organização da estrutura Django e implementação da interface.

## Integrantes

- André Rocha Figueredo
- Michel Guido Teixeira
- Mickael Sousa Miranda
- Pedro Igor Ferreira de Carvalho
- Dhonantan dos Santos Anchieta Junior

## Instituição

**Centro Universitário de Balsas – UNIBALSAS**  
Curso de Análise e Desenvolvimento de Sistemas  
Balsas – MA  
2026
