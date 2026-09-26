# Da Roça Inteligente – Sistema Inteligente de Gestão de Estoque com IA

Projeto acadêmico desenvolvido no curso de **Análise e Desenvolvimento de Sistemas – UNIBALSAS**, na disciplina de **Big Data e Ciência de Dados**.

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

Fonte:  
https://www.kaggle.com/datasets/anirudhchauhan/retail-store-inventory-forecasting-dataset

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

- 0 valores ausentes;
- 0 registros totalmente duplicados;
- 673 valores negativos na variável `Demand Forecast`.

Como `Demand Forecast` representa uma quantidade prevista de demanda, os valores negativos foram considerados inconsistentes para o contexto do projeto e ajustados para **0** na versão tratada da base.

Os possíveis valores extremos foram analisados antes de qualquer decisão de tratamento, evitando exclusões automáticas sem justificativa.

A análise exploratória também permitiu investigar o comportamento das variáveis relacionadas a estoque, vendas e previsão de demanda, contribuindo para compreender como os dados poderão apoiar o futuro sistema inteligente.

## Organização do repositório

```text
sistema-agroestoque/
├── README.md
├── docs/
│   ├── documentos da TED 01
│   └── TED02_Documento_Tecnico.pdf
├── data/
│   ├── raw/
│   │   └── retail_store_inventory.csv
│   └── processed/
│       └── retail_store_inventory_processed.csv
├── notebooks/
│   └── TED02/
│       └── TED02_limpeza_eda.ipynb
├── .gitignore
└── index.html
Reprodutibilidade
A base original utilizada no projeto está disponível em:
data/raw/retail_store_inventory.csv
A versão preparada após o processo de limpeza está disponível em:
data/processed/retail_store_inventory_processed.csv
O código utilizado para limpeza, preparação, estatísticas e análise exploratória está disponível em:
notebooks/TED02/TED02_limpeza_eda.ipynb
O Documento Técnico – Versão 2.0 está disponível em:
docs/TED02_Documento_Tecnico.pdf
Tecnologias utilizadas
- Python
- Pandas
- NumPy
- Matplotlib
- Jupyter Notebook
- Django
- SQLite
- HTML
- CSS
- JavaScript
- Git e GitHub
Integrantes
- André Rocha Figueredo
- Michel Guido Teixeira
- Mickael Sousa Miranda
- Pedro Igor Ferreira de Carvalho
- Dhonantan dos Santos Anchieta Junior
Instituição
Centro Universitário de Balsas – UNIBALSAS
Curso de Análise e Desenvolvimento de Sistemas
Balsas – MA
2026
