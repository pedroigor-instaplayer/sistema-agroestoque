"""Validação e conversão dos dados de entrada da API."""
import json
import re
from decimal import Decimal, InvalidOperation

from flask import request

from .erros import ApiError, erro_campo

LIMITE_INTEIRO = 1_000_000_000
LIMITE_CENTAVOS = 9_999_999_999  # R$ 99.999.999,99
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SENHAS_COMUNS = {"12345678", "123456789", "1234567890", "password", "senha123", "qwertyui",
                 "11111111", "abcd1234", "00000000"}


def ler_json():
    bruto = request.get_data()
    if not bruto:
        raise ApiError(400, "CORPO_AUSENTE", "O corpo da requisição (JSON) é obrigatório.")
    try:
        dados = json.loads(bruto.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise ApiError(400, "JSON_INVALIDO", "O corpo da requisição não é um JSON válido.")
    if not isinstance(dados, dict):
        raise ApiError(400, "JSON_INVALIDO", "O corpo da requisição deve ser um objeto JSON.")
    return dados


def texto(dados, nome, obrigatorio=True, max_len=None, padrao=""):
    valor = dados.get(nome)
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        if obrigatorio:
            raise erro_campo(nome, "Este campo é obrigatório.")
        return padrao
    if not isinstance(valor, str):
        raise erro_campo(nome, "Deve ser um texto.")
    valor = valor.strip()
    if max_len and len(valor) > max_len:
        raise erro_campo(nome, f"Máximo de {max_len} caracteres.")
    return valor


def inteiro(dados, nome, obrigatorio=True, minimo=0, padrao=0, maximo=LIMITE_INTEIRO):
    valor = dados.get(nome)
    if valor is None or valor == "":
        if obrigatorio:
            raise erro_campo(nome, "Este campo é obrigatório.")
        return padrao
    if isinstance(valor, bool):
        raise erro_campo(nome, "Número inteiro inválido.")
    try:
        if isinstance(valor, float):
            if not valor.is_integer():
                raise ValueError
            numero = int(valor)
        else:
            numero = int(str(valor).strip())
    except (TypeError, ValueError):
        raise erro_campo(nome, "Número inteiro inválido.")
    if minimo is not None and numero < minimo:
        raise erro_campo(nome, f"O valor deve ser maior ou igual a {minimo}.")
    if maximo is not None and numero > maximo:
        raise erro_campo(nome, f"O valor deve ser menor ou igual a {maximo}.")
    return numero


def dinheiro(dados, nome, obrigatorio=True, padrao=None):
    """Converte para CENTAVOS (int). Aceita 189.9, '189,90', '1.234,56' e 'R$ 10'."""
    valor = dados.get(nome)
    if valor is None or valor == "":
        if obrigatorio:
            raise erro_campo(nome, "Este campo é obrigatório.")
        return padrao
    if isinstance(valor, bool):
        raise erro_campo(nome, "Valor numérico inválido.")
    t = str(valor).strip().replace("R$", "").strip()
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    try:
        numero = Decimal(t)
    except InvalidOperation:
        raise erro_campo(nome, "Valor numérico inválido.")
    if not numero.is_finite():
        raise erro_campo(nome, "Valor numérico inválido.")
    if numero < 0:
        raise erro_campo(nome, "O valor deve ser maior ou igual a 0.")
    centavos = int((numero * 100).to_integral_value())
    if centavos > LIMITE_CENTAVOS:
        raise erro_campo(nome, "Valor acima do limite permitido.")
    return centavos


def email(dados, nome="email"):
    valor = texto(dados, nome, max_len=254).lower()
    if not EMAIL_RE.match(valor):
        raise erro_campo(nome, "E-mail inválido.")
    return valor


def validar_senha(senha, campo="senha"):
    if not isinstance(senha, str) or len(senha) < 8:
        raise erro_campo(campo, "A senha deve ter pelo menos 8 caracteres.")
    if senha.isdigit():
        raise erro_campo(campo, "A senha não pode conter apenas números.")
    if senha.lower() in SENHAS_COMUNS:
        raise erro_campo(campo, "Esta senha é muito comum.")
    return senha


def pagina_params(padrao=20, maximo=100):
    try:
        pagina = max(1, int(request.args.get("page", 1)))
        tamanho = int(request.args.get("page_size", padrao))
    except ValueError:
        raise ApiError(400, "PARAMETRO_INVALIDO", "Parâmetros de paginação inválidos.")
    return pagina, min(max(1, tamanho), maximo)
