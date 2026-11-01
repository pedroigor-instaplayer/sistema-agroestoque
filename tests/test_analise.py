"""Testes do motor de análise (Python puro, não exigem banco de dados)."""
import unittest
from datetime import date

from agroestoque import analise as a


class SituacaoPorSaldoTests(unittest.TestCase):
    def test_critico_quando_zerado(self):
        self.assertEqual(a.situacao_por_saldo(0, 0), a.CRITICO)

    def test_critico_quando_abaixo_ou_igual_ao_minimo(self):
        self.assertEqual(a.situacao_por_saldo(4, 8), a.CRITICO)
        self.assertEqual(a.situacao_por_saldo(8, 8), a.CRITICO)

    def test_atencao_ate_um_e_meio_do_minimo(self):
        self.assertEqual(a.situacao_por_saldo(12, 10), a.ATENCAO)
        self.assertEqual(a.situacao_por_saldo(15, 10), a.ATENCAO)

    def test_normal(self):
        self.assertEqual(a.situacao_por_saldo(28, 8), a.NORMAL)
        self.assertEqual(a.situacao_por_saldo(5, 0), a.NORMAL)


class MediasTests(unittest.TestCase):
    def test_serie_vazia(self):
        self.assertEqual(a.calcular_medias([]), (0.0, 0.0, 0.0, None))

    def test_media_ponderada(self):
        serie = [0] * 16 + [10] * 14  # 30 dias; últimos 14 = 10/dia
        rec, base, dem, tend = a.calcular_medias(serie)
        self.assertAlmostEqual(rec, 10.0)
        self.assertAlmostEqual(base, 140 / 30)
        self.assertAlmostEqual(dem, 0.6 * 10 + 0.4 * 140 / 30)
        self.assertIsNone(tend)  # período anterior sem vendas => sem tendência

    def test_tendencia_positiva(self):
        serie = [5] * 16 + [10] * 14
        *_, tend = a.calcular_medias(serie)
        self.assertAlmostEqual(tend, 100.0)

    def test_valores_negativos_sao_tratados_como_zero(self):
        rec, *_ = a.calcular_medias([-5, -5, 10, 10])
        self.assertAlmostEqual(rec, 5.0)


class AnalisarTests(unittest.TestCase):
    def test_risco_alto_por_cobertura(self):
        r = a.analisar(4, 8, [1] * 30, prazo_entrega_dias=7)
        self.assertEqual(r.nivel, a.CRITICO)
        self.assertAlmostEqual(r.dias_cobertura, 4.0)
        self.assertGreater(r.quantidade_sugerida, 0)
        self.assertIn("4 dias", r.justificativa)
        self.assertIn("abaixo do estoque mínimo", r.justificativa)

    def test_sem_estoque_com_minimo(self):
        r = a.analisar(0, 5, [0] * 30)
        self.assertEqual(r.nivel, a.CRITICO)
        self.assertEqual(r.quantidade_sugerida, 5)
        self.assertIn("sem estoque", r.justificativa)

    def test_produto_novo_sem_minimo_e_sem_historico_e_normal(self):
        r = a.analisar(0, 0, [])
        self.assertEqual(r.nivel, a.NORMAL)
        self.assertEqual(r.quantidade_sugerida, 0)

    def test_normal_com_estoque_confortavel(self):
        r = a.analisar(300, 10, [2] * 30)
        self.assertEqual(r.nivel, a.NORMAL)
        self.assertEqual(r.quantidade_sugerida, 0)
        self.assertEqual(r.acao_sugerida, "Nenhuma ação necessária")

    def test_atencao_por_ponto_de_pedido(self):
        # demanda 2/dia, prazo 7 => ponto de pedido 14 + 5 = 19; cobertura 9,5 > 7
        r = a.analisar(19, 5, [2] * 30, prazo_entrega_dias=7)
        self.assertEqual(r.nivel, a.ATENCAO)

    def test_prazo_padrao_quando_ausente(self):
        r = a.analisar(10, 1, [1] * 30, prazo_entrega_dias=None)
        self.assertEqual(r.prazo_entrega_dias, a.PRAZO_PADRAO_DIAS)

    def test_quantidade_sugerida_formula(self):
        r = a.analisar(2, 5, [1] * 30, prazo_entrega_dias=7, horizonte_dias=15)
        # ceil(1 * 22) + 5 - 2 = 25
        self.assertEqual(r.quantidade_sugerida, 25)

    def test_tendencia_aparece_na_justificativa(self):
        serie = [1] * 16 + [2] * 14
        r = a.analisar(3, 2, serie)
        self.assertIn("aumentaram", r.justificativa)

    def test_singular(self):
        r = a.analisar(1, 1, [0] * 30)
        self.assertIn("1 unidade", r.justificativa + r.acao_sugerida)


class LivroTests(unittest.TestCase):
    def test_saldo_nunca_fica_negativo_e_fecha_no_saldo_final(self):
        dias = [(date(2024, 1, d), e, s) for d, e, s in
                [(1, 0, 10), (2, 100, 5), (3, 0, 20), (4, 50, 30)]]
        inicial, efetivas, _ = a_reconstruir(dias, 40)
        saldo = inicial
        for _, ent, sai in efetivas:
            saldo += ent
            self.assertGreaterEqual(saldo, sai)
            saldo -= sai
            self.assertGreaterEqual(saldo, 0)
        self.assertEqual(saldo, 40)

    def test_limita_entradas_excessivas(self):
        dias = [(date(2024, 1, 1), 0, 5), (date(2024, 1, 2), 1000, 5)]
        inicial, efetivas, ajustes = a_reconstruir(dias, 3)
        self.assertEqual(ajustes, 1)
        self.assertLessEqual(efetivas[1][1], 3 + 5)
        self.assertGreaterEqual(inicial, 0)


def a_reconstruir(dias, saldo):
    return a.reconstruir_livro(dias, saldo)


if __name__ == "__main__":
    unittest.main()
