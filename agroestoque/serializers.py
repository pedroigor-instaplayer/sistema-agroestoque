"""Conversão de linhas do banco em dicionários JSON."""
from . import analise, util
from .servicos import DESCRICAO_MOTIVO

NIVEIS = {"CRITICO": "Risco alto", "ATENCAO": "Atenção"}


def usuario(u):
    return {"id": u["id"], "username": u["email"], "email": u["email"], "nome": u["nome"],
            "papel": u["papel"], "ativo": bool(u["ativo"])}


def categoria(c):
    return {"id": c["id"], "nome": c["nome"]}


def fornecedor(f):
    return {"id": f["id"], "nome": f["nome"], "telefone": f["telefone"], "email": f["email"],
            "prazo_entrega_dias": f["prazo_entrega_dias"], "ativo": bool(f["ativo"])}


def produto(p):
    return {
        "id": p["id"], "sku": p["sku"], "nome": p["nome"],
        "categoria": p["categoria"], "categoria_id": p["categoria_id"], "unidade": p["unidade"],
        "preco_venda": util.centavos_str(p["preco_venda_centavos"]),
        "quantidade_atual": p["quantidade_atual"], "estoque_minimo": p["estoque_minimo"],
        "situacao": analise.situacao_por_saldo(p["quantidade_atual"], p["estoque_minimo"]),
        "fornecedor_id": p["fornecedor_id"], "fornecedor": p["fornecedor"],
        "ativo": bool(p["ativo"]),
        "criado_em": util.iso_local(p["criado_em"]), "atualizado_em": util.iso_local(p["atualizado_em"]),
    }


def movimentacao(m):
    return {
        "id": m["id"], "produto_id": m["produto_id"], "produto": m["produto"],
        "tipo": m["tipo"], "motivo": m["motivo"], "motivo_descricao": DESCRICAO_MOTIVO[m["motivo"]],
        "quantidade": m["quantidade"], "valor_unitario": util.centavos_str(m["valor_unitario_centavos"]),
        "saldo_apos": m["saldo_apos"], "observacao": m["observacao"], "usuario": m["usuario"],
        "data": util.iso_local(m["data"]),
    }


def _num(v):
    return None if v is None else str(v)


def recomendacao(r):
    return {
        "id": r["id"], "produto_id": r["produto_id"], "produto": r["produto"], "sku": r["sku"],
        "nivel": r["nivel"], "nivel_descricao": NIVEIS[r["nivel"]], "status": r["status"],
        "quantidade_sugerida": r["quantidade_sugerida"], "saldo_no_calculo": r["saldo_no_calculo"],
        "saldo_atual": r["saldo_atual"], "media_diaria": f"{r['media_diaria']:.2f}",
        "dias_cobertura": _num(r["dias_cobertura"]), "tendencia_percentual": _num(r["tendencia_percentual"]),
        "acao_sugerida": r["acao_sugerida"], "justificativa": r["justificativa"],
        "gerada_em": util.iso_local(r["gerada_em"]), "decidida_em": util.iso_local(r["decidida_em"]),
        "decidida_por": r["decidida_por"],
    }
