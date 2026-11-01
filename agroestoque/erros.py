"""Erros de negócio e de validação da API (convertidos em JSON padronizado)."""


class ApiError(Exception):
    def __init__(self, status, codigo, mensagem, detalhes=None):
        super().__init__(mensagem)
        self.status = status
        self.codigo = codigo
        self.mensagem = mensagem
        self.detalhes = detalhes or {}


def erro_campo(campo, mensagem):
    """400 – dado inválido em um campo específico."""
    return ApiError(400, "DADOS_INVALIDOS", "Dados inválidos.", {campo: [mensagem]})


def regra(codigo, mensagem, detalhes=None):
    """422 – violação de regra de negócio."""
    return ApiError(422, codigo, mensagem, detalhes)


def nao_encontrado(mensagem="Recurso não encontrado."):
    return ApiError(404, "NAO_ENCONTRADO", mensagem)


def acesso_negado(papeis=None):
    return ApiError(403, "ACESSO_NEGADO", "Seu perfil não tem permissão para esta operação.",
                    {"papeis_permitidos": list(papeis)} if papeis else None)
