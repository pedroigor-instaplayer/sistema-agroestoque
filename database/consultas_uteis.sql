-- Consultas úteis para auditoria e conferência (SQLite)

-- 1) Conferência de integridade: saldo do produto = entradas - saídas (deve retornar 0 linhas)
SELECT p.id, p.sku, p.quantidade_atual AS saldo_cadastro,
       COALESCE(SUM(CASE m.tipo WHEN 'ENTRADA' THEN m.quantidade ELSE -m.quantidade END), 0) AS saldo_calculado
FROM produto p LEFT JOIN movimentacao m ON m.produto_id = p.id
GROUP BY p.id
HAVING saldo_cadastro <> saldo_calculado;

-- 2) Produtos em situação crítica (saldo <= mínimo ou zerado)
SELECT sku, nome, quantidade_atual, estoque_minimo
FROM produto
WHERE ativo = 1 AND (quantidade_atual <= 0 OR (estoque_minimo > 0 AND quantidade_atual <= estoque_minimo));

-- 3) Vendas dos últimos 30 dias por produto
SELECT p.nome, SUM(m.quantidade) AS unidades
FROM movimentacao m JOIN produto p ON p.id = m.produto_id
WHERE m.tipo = 'SAIDA' AND m.motivo = 'VENDA' AND m.data >= datetime('now', '-30 days')
GROUP BY p.id ORDER BY unidades DESC;

-- 4) Faturamento do mês corrente (em reais)
SELECT SUM(quantidade * valor_unitario_centavos) / 100.0 AS faturamento
FROM movimentacao
WHERE tipo = 'SAIDA' AND motivo = 'VENDA' AND data >= strftime('%Y-%m-01', 'now');

-- 5) Recomendações pendentes por nível
SELECT nivel, COUNT(*) FROM recomendacao WHERE status = 'PENDENTE' GROUP BY nivel;
