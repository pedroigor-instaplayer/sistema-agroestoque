# TED 03 — Modelagem Preditiva e Machine Learning

Projeto Da Roça Inteligente | UNIBALSAS — ADS | 2026

## Arquivos para adicionar ao repositório
- `notebooks/TED03/TED03_modelagem_preditiva.ipynb`: notebook executável, com divisão temporal, Random Forest, baseline, métricas e exportação de gráficos.
- `docs/TED03_Documento_Tecnico_v3_0.pdf`: documento técnico consolidado, incluindo histórico das TEDs 01 e 02.
- `requirements-ted03.txt`: dependências da etapa.

## Como executar
Na raiz do repositório:

```bash
python -m pip install -r requirements-ted03.txt
jupyter notebook notebooks/TED03/TED03_modelagem_preditiva.ipynb
```

Execute **todas as células em ordem**. O notebook lê a base tratada do repositório público e cria a pasta `resultados/` no diretório de execução com:
- `TED03_metricas.csv`
- `TED03_real_vs_previsto.png`
- `TED03_distribuicao_erros.png`

Depois da execução, adicione os três resultados ao repositório, preferencialmente em `notebooks/TED03/resultados/`.

## Conferência obrigatória
O notebook foi reconstruído a partir da metodologia do documento técnico; não é o notebook original da equipe. **Não foram simuladas saídas ou inventadas métricas.** Confirme os valores reproduzidos contra os números do PDF (MAE 89,8715; RMSE 109,0583; R² -0,0151). Caso haja diferença, documente-a e ajuste o relatório antes de submeter. O repositório contém também uma TED 3 de Back-end, que pertence a outra atividade.

## Link
https://github.com/pedroigor-instaplayer/sistema-agroestoque
