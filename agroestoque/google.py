"""Verificação do ID token do "Entrar com o Google" (Google Identity Services).

O navegador recebe do Google um JWT (``credential``). O servidor o confere no endpoint
oficial ``tokeninfo`` do Google, que valida assinatura e validade, e então checa:
público (``aud`` = o nosso Client ID), emissor e e-mail verificado.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
EMISSORES = {"accounts.google.com", "https://accounts.google.com"}


class TokenGoogleInvalido(Exception):
    """O Google recusou o token ou ele não é destinado a esta aplicação."""


class GoogleIndisponivel(Exception):
    """Não foi possível consultar o Google (rede, tempo esgotado, resposta ilegível)."""


def verificar(credential, client_id, timeout=6):
    """Devolve {'email', 'nome', 'sub'} se o token for válido para ``client_id``."""
    url = TOKENINFO_URL + "?" + urllib.parse.urlencode({"id_token": credential})
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            dados = json.load(resp)
    except urllib.error.HTTPError as e:
        if 400 <= e.code < 500:
            raise TokenGoogleInvalido("token recusado pelo Google") from e
        raise GoogleIndisponivel(str(e)) from e
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        raise GoogleIndisponivel(str(e)) from e

    if not isinstance(dados, dict) or dados.get("aud") != client_id:
        raise TokenGoogleInvalido("token emitido para outra aplicação")
    if dados.get("iss") not in EMISSORES:
        raise TokenGoogleInvalido("emissor inesperado")
    if str(dados.get("email_verified")).lower() != "true" or not dados.get("email"):
        raise TokenGoogleInvalido("e-mail não verificado")
    return {"email": dados["email"].strip().lower(), "nome": dados.get("name") or "", "sub": dados.get("sub")}
