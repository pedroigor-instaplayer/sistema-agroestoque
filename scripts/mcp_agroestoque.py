#!/usr/bin/env python3
"""Servidor MCP do AgroEstoque (transporte stdio, só biblioteca padrão).

É a peça do meio do desenho de arquitetura:

    WhatsApp / Telegram / outro  ->  agente de IA  ->  servidor MCP (este)  ->  sistema (API)

O agente de IA (qualquer cliente MCP: Claude Desktop, um bot de WhatsApp/Telegram etc.) olha a
foto ou lê a mensagem e chama a ferramenta ``cadastrar_produto``. Este servidor repassa o
pedido à API do sistema, que aplica as MESMAS regras do cadastro manual (validação, sem
duplicar, rastro de quem cadastrou). O agente nunca acessa o banco diretamente.

Variáveis de ambiente:
    AGROESTOQUE_URL     endereço da API (padrão http://127.0.0.1:5000)
    AGROESTOQUE_EMAIL   usuário do sistema em nome do qual o agente age
    AGROESTOQUE_SENHA   senha desse usuário (use um usuário OPERADOR dedicado ao agente)

Exemplo de configuração em um cliente MCP (ex.: claude_desktop_config.json):
    {"mcpServers": {"agroestoque": {"command": "python3", "args": ["scripts/mcp_agroestoque.py"],
      "env": {"AGROESTOQUE_URL": "http://127.0.0.1:5000",
              "AGROESTOQUE_EMAIL": "agente@daroca.com.br", "AGROESTOQUE_SENHA": "..."}}}}
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

VERSAO_PADRAO = "2025-06-18"

FERRAMENTAS = [
    {
        "name": "cadastrar_produto",
        "description": ("Cadastra um produto no estoque da Da Roça Agropecuária & Pet. Nunca duplica: se o "
                        "produto (mesmo código de barras ou mesmo nome) já existir, devolve o existente. "
                        "Chame depois de ler a foto ou a mensagem do funcionário."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "nome": {"type": "string", "description": "Nome completo, com marca e peso/volume."},
                "categoria": {"type": "string", "description": "Ex.: Rações, Medicamentos, Acessórios Pet."},
                "unidade": {"type": "string", "description": "unidade, kg, saco, litro..."},
                "preco_venda": {"type": "number", "description": "Preço em reais; omita se não souber."},
                "codigo_barras": {"type": "string", "description": "Somente dígitos legíveis; omita se não houver."},
                "quantidade": {"type": "integer", "minimum": 0,
                               "description": "Quantidade em estoque a lançar; omita se não informada."},
            },
            "required": ["nome"],
        },
    },
    {
        "name": "consultar_produto",
        "description": "Procura produtos por nome, código ou categoria e mostra saldo e situação. Use antes de cadastrar, se quiser conferir.",
        "inputSchema": {"type": "object", "properties": {"busca": {"type": "string"}}, "required": ["busca"]},
    },
]


class ErroApi(Exception):
    """Falha ao falar com o sistema; a mensagem é mostrada ao agente."""


class ClienteApi:
    def __init__(self, url=None, email=None, senha=None):
        self.url = (url or os.environ.get("AGROESTOQUE_URL") or "http://127.0.0.1:5000").rstrip("/")
        self.email = email or os.environ.get("AGROESTOQUE_EMAIL")
        self.senha = senha or os.environ.get("AGROESTOQUE_SENHA")
        self.token = None

    def _requisicao(self, metodo, caminho, corpo=None, token=None):
        dados = json.dumps(corpo).encode("utf-8") if corpo is not None else None
        req = urllib.request.Request(f"{self.url}/api/{caminho}", data=dados, method=metodo)
        req.add_header("Content-Type", "application/json")
        if token:
            req.add_header("Authorization", "Bearer " + token)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            try:
                erro = json.load(e).get("erro", {})
            except (ValueError, OSError):
                erro = {}
            msg = erro.get("mensagem") or f"O sistema respondeu com erro {e.code}."
            detalhes = erro.get("detalhes") or {}
            extra = " ".join(f"{k}: {' '.join(v)}" for k, v in detalhes.items() if isinstance(v, list))
            e.status_api = e.code
            raise ErroApi((msg + " " + extra).strip()) from e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise ErroApi(f"Não consegui falar com o sistema em {self.url}. Ele está ligado?") from e

    def _login(self):
        if not self.email or not self.senha:
            raise ErroApi("Defina AGROESTOQUE_EMAIL e AGROESTOQUE_SENHA no ambiente do servidor MCP.")
        self.token = self._requisicao("POST", "auth/login", {"email": self.email, "senha": self.senha})["token"]

    def chamar(self, metodo, caminho, corpo=None):
        if not self.token:
            self._login()
        try:
            return self._requisicao(metodo, caminho, corpo, self.token)
        except ErroApi as e:
            if "Sessão expirada" in str(e) or "Token de acesso inválido" in str(e):
                self._login()
                return self._requisicao(metodo, caminho, corpo, self.token)
            raise


# ----------------------------------------------------------------- ferramentas
def _cadastrar(api, args):
    corpo = {k: args[k] for k in ("nome", "categoria", "unidade", "preco_venda", "codigo_barras", "quantidade")
             if args.get(k) not in (None, "")}
    r = api.chamar("POST", "agente/produtos", corpo)
    p = r["produto"]
    linhas = [r["mensagem"], f"Código (SKU): {p['sku']} • Preço: R$ {p['preco_venda']} • ID {p['id']}"]
    linhas += r.get("avisos") or []
    return "\n".join(linhas)


def _consultar(api, args):
    r = api.chamar("GET", "produtos?" + urllib.parse.urlencode({"q": args.get("busca", "")}))
    itens = r.get("resultados", [])[:5]
    if not itens:
        return "Nenhum produto encontrado."
    return "\n".join(f"- {p['nome']} ({p['sku']}) • saldo {p['quantidade_atual']} • R$ {p['preco_venda']} • {p['situacao']}"
                     for p in itens)


EXECUTORES = {"cadastrar_produto": _cadastrar, "consultar_produto": _consultar}


# -------------------------------------------------------------------- protocolo
def _ok(id_, resultado):
    return {"jsonrpc": "2.0", "id": id_, "result": resultado}


def _erro(id_, codigo, mensagem):
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": codigo, "message": mensagem}}


def tratar(msg, api):
    """Responde a uma mensagem JSON-RPC; devolve None para notificações."""
    if not isinstance(msg, dict) or "method" not in msg:
        return _erro(msg.get("id") if isinstance(msg, dict) else None, -32600, "Requisição inválida")
    id_, metodo, params = msg.get("id"), msg["method"], msg.get("params") or {}
    if id_ is None:                       # notificação (ex.: notifications/initialized)
        return None
    if metodo == "initialize":
        return _ok(id_, {"protocolVersion": params.get("protocolVersion") or VERSAO_PADRAO,
                         "capabilities": {"tools": {}},
                         "serverInfo": {"name": "agroestoque", "version": "1.0.0"},
                         "instructions": "Ferramentas do estoque da Da Roça. Use cadastrar_produto quando o "
                                         "funcionário enviar a foto de um produto novo."})
    if metodo == "ping":
        return _ok(id_, {})
    if metodo == "tools/list":
        return _ok(id_, {"tools": FERRAMENTAS})
    if metodo == "tools/call":
        executor = EXECUTORES.get(params.get("name"))
        if executor is None:
            return _ok(id_, {"content": [{"type": "text", "text": f"Ferramenta desconhecida: {params.get('name')}"}],
                             "isError": True})
        try:
            texto, erro = executor(api, params.get("arguments") or {}), False
        except ErroApi as e:
            texto, erro = str(e), True
        except Exception as e:             # nunca derruba o servidor por causa de uma chamada
            print(f"erro inesperado: {e!r}", file=sys.stderr)
            texto, erro = "Erro inesperado ao executar a ferramenta.", True
        return _ok(id_, {"content": [{"type": "text", "text": texto}], "isError": erro})
    return _erro(id_, -32601, f"Método não suportado: {metodo}")


def main():
    api = ClienteApi()
    for linha in sys.stdin:
        linha = linha.strip()
        if not linha:
            continue
        try:
            resposta = tratar(json.loads(linha), api)
        except ValueError:
            resposta = _erro(None, -32700, "JSON inválido")
        if resposta is not None:
            sys.stdout.write(json.dumps(resposta, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
