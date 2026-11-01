"""Motor de análise de estoque e recomendação de reposição.

Este módulo é Python puro (não depende do Flask nem do banco de dados),
o que permite testá-lo isoladamente e auditar cada decisão tomada.

Abordagem (apoio à decisão, explicável):

1. Demanda diária prevista = média ponderada do consumo recente
   (60% últimos 14 dias + 40% últimos 30 dias).
2. Cobertura (dias) = saldo atual / demanda diária prevista.
3. Ponto de pedido = demanda diária * prazo de entrega + estoque mínimo.
4. Classificação de risco:
   - CRITICO: sem estoque, saldo <= mínimo, ou cobertura menor que o prazo de entrega;
   - ATENCAO: saldo até 1,5x o mínimo, ou saldo <= ponto de pedido;
   - NORMAL: demais casos.
5. Quantidade sugerida = demanda * (prazo + horizonte) + mínimo - saldo.

A decisão de compra é sempre do gestor: o sistema apenas recomenda.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Sequence

CRITICO = "CRITICO"
ATENCAO = "ATENCAO"
NORMAL = "NORMAL"

JANELA_DIAS = 30          # tamanho da série diária analisada
JANELA_RECENTE = 14       # janela "recente" usada na média e na tendência
PESO_RECENTE = 0.6
PESO_BASE = 0.4
FATOR_ATENCAO = 1.5       # saldo <= 1,5 x mínimo => atenção
PRAZO_PADRAO_DIAS = 7     # usado quando o produto não tem fornecedor definido
HORIZONTE_PADRAO_DIAS = 15  # por quantos dias a compra deve cobrir a demanda


@dataclass(frozen=True)
class ResultadoAnalise:
    nivel: str
    saldo: int
    estoque_minimo: int
    media_recente: float
    media_base: float
    demanda_diaria: float
    dias_cobertura: Optional[float]
    tendencia_pct: Optional[float]
    prazo_entrega_dias: int
    ponto_de_pedido: int
    quantidade_sugerida: int
    justificativa: str
    acao_sugerida: str


def situacao_por_saldo(saldo: int, minimo: int) -> str:
    """Classificação simples, sem histórico: usada nas listagens de produtos."""
    if saldo <= 0:
        return CRITICO
    if minimo > 0 and saldo <= minimo:
        return CRITICO
    if minimo > 0 and saldo * 2 <= minimo * 3:
        return ATENCAO
    return NORMAL


def _fmt(valor: float, casas: int = 1) -> str:
    """Formata número no padrão brasileiro (vírgula decimal)."""
    texto = f"{valor:.{casas}f}"
    if casas > 0:
        texto = texto.rstrip("0").rstrip(".")
    return texto.replace(".", ",")


def _unidades(qtd: int) -> str:
    return f"{qtd} unidade" if qtd == 1 else f"{qtd} unidades"


def _dias(valor: float) -> str:
    arred = max(0, int(round(valor)))
    return "menos de 1 dia" if arred == 0 else (
        "1 dia" if arred == 1 else f"{arred} dias")


def calcular_medias(saidas_diarias: Sequence[int]) -> tuple[float, float, float, Optional[float]]:
    """Retorna (media_recente, media_base, demanda_diaria, tendencia_pct).

    `saidas_diarias` é a série de vendas por dia, do mais antigo para o mais
    recente (idealmente JANELA_DIAS valores, incluindo dias sem venda = 0).
    """
    serie = [max(0, int(v)) for v in saidas_diarias]
    if not serie:
        return 0.0, 0.0, 0.0, None
    recente = serie[-JANELA_RECENTE:]
    media_recente = sum(recente) / len(recente)
    media_base = sum(serie) / len(serie)
    demanda = PESO_RECENTE * media_recente + PESO_BASE * media_base

    tendencia = None
    anterior = serie[-2 * JANELA_RECENTE:-JANELA_RECENTE]
    if len(anterior) == JANELA_RECENTE:
        soma_ant = sum(anterior)
        if soma_ant > 0:
            tendencia = (sum(recente) - soma_ant) / soma_ant * 100.0
    return media_recente, media_base, demanda, tendencia


def analisar(
    saldo: int,
    estoque_minimo: int,
    saidas_diarias: Sequence[int],
    prazo_entrega_dias: Optional[int] = None,
    horizonte_dias: int = HORIZONTE_PADRAO_DIAS,
) -> ResultadoAnalise:
    """Analisa um produto e devolve nível de risco, quantidade e justificativa."""
    saldo = max(0, int(saldo))
    minimo = max(0, int(estoque_minimo))
    prazo = int(prazo_entrega_dias) if prazo_entrega_dias else PRAZO_PADRAO_DIAS

    media_rec, media_base, demanda, tendencia = calcular_medias(saidas_diarias)
    cobertura = (saldo / demanda) if demanda > 0 else None
    ponto_pedido = math.ceil(demanda * prazo) + minimo

    # --- classificação de risco ---
    if saldo <= 0 and (minimo > 0 or demanda > 0):
        nivel = CRITICO
    elif minimo > 0 and saldo <= minimo:
        nivel = CRITICO
    elif demanda > 0 and cobertura is not None and cobertura < prazo:
        nivel = CRITICO
    elif minimo > 0 and saldo * 2 <= minimo * 3:
        nivel = ATENCAO
    elif demanda > 0 and saldo <= ponto_pedido:
        nivel = ATENCAO
    else:
        nivel = NORMAL

    # --- quantidade sugerida ---
    if nivel == NORMAL:
        sugerida = 0
    else:
        alvo = math.ceil(demanda * (prazo + horizonte_dias)) + minimo
        sugerida = max(0, alvo - saldo)

    # --- justificativa explicável ---
    partes: list[str] = []
    if saldo <= 0:
        partes.append("O produto está sem estoque.")
    elif cobertura is not None:
        partes.append(
            f"O estoque atual ({_unidades(saldo)}) deve durar aproximadamente "
            f"{_dias(cobertura)}; o prazo de reposição considerado é de {prazo} dias."
        )
    else:
        partes.append(
            f"O estoque atual é de {_unidades(saldo)} e não houve vendas "
            f"registradas nos últimos {JANELA_DIAS} dias."
        )
    if demanda > 0:
        partes.append(
            f"A demanda diária prevista é de {_fmt(demanda)} unidade(s) por dia "
            f"(60% da média dos últimos {JANELA_RECENTE} dias + 40% da média dos "
            f"últimos {JANELA_DIAS} dias)."
        )
    if minimo > 0:
        if saldo < minimo:
            pct = (minimo - saldo) / minimo * 100
            partes.append(
                f"O saldo está {_fmt(pct, 0)}% abaixo do estoque mínimo definido ({minimo})."
            )
        elif saldo == minimo:
            partes.append(f"O saldo está no estoque mínimo definido ({minimo}).")
    if tendencia is not None and abs(tendencia) >= 10:
        sinal = "aumentaram" if tendencia > 0 else "diminuíram"
        partes.append(
            f"As saídas {sinal} {_fmt(abs(tendencia), 0)}% nos últimos "
            f"{JANELA_RECENTE} dias em relação aos {JANELA_RECENTE} anteriores."
        )

    if nivel == CRITICO:
        acao = f"Repor {_unidades(sugerida)} com urgência" if sugerida else "Verificar reposição com urgência"
    elif nivel == ATENCAO:
        acao = f"Programar a compra de {_unidades(sugerida)}" if sugerida else "Acompanhar o estoque nos próximos dias"
    else:
        acao = "Nenhuma ação necessária"

    return ResultadoAnalise(
        nivel=nivel,
        saldo=saldo,
        estoque_minimo=minimo,
        media_recente=round(media_rec, 2),
        media_base=round(media_base, 2),
        demanda_diaria=round(demanda, 2),
        dias_cobertura=None if cobertura is None else round(cobertura, 1),
        tendencia_pct=None if tendencia is None else round(tendencia, 1),
        prazo_entrega_dias=prazo,
        ponto_de_pedido=int(ponto_pedido),
        quantidade_sugerida=int(sugerida),
        justificativa=" ".join(partes),
        acao_sugerida=acao,
    )


def reconstruir_livro(dias: Sequence[tuple], saldo_final: int):
    """Reconstrói um livro de movimentações coerente a partir de dados diários.

    `dias` é uma sequência ordenada de tuplas (data, entradas, saidas).
    Partindo do saldo final conhecido, caminha de trás para frente e limita as
    entradas para que o saldo nunca fique negativo. Dentro de cada dia as
    entradas ocorrem antes das saídas.

    Retorna (estoque_inicial, lista[(data, entradas_efetivas, saidas)],
    qtd_entradas_ajustadas).
    """
    saldo = max(0, int(saldo_final))
    efetivas = []
    ajustes = 0
    for data, entradas, saidas in reversed(list(dias)):
        entradas = max(0, int(entradas))
        saidas = max(0, int(saidas))
        max_entrada = saldo + saidas  # saldo de abertura não pode ser negativo
        if entradas > max_entrada:
            entradas = max_entrada
            ajustes += 1
        saldo = saldo + saidas - entradas
        efetivas.append((data, entradas, saidas))
    efetivas.reverse()
    return saldo, efetivas, ajustes
