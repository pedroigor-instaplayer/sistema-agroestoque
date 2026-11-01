"""Gera a coleção Postman a partir de docs/api/openapi.yaml.

Uso:  python scripts/gerar_postman.py        (requer PyYAML: pip install pyyaml)
"""
import json
import uuid
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
spec = yaml.safe_load((RAIZ / "docs" / "api" / "openapi.yaml").read_text(encoding="utf-8"))

EXEMPLOS = {
    ("/api/auth/login", "post"): {"email": "gestor@daroca.com.br", "senha": "Agro@2026"},
    ("/api/auth/alterar-senha", "post"): {"senha_atual": "Agro@2026", "nova_senha": "NovaSenha#2026"},
    ("/api/usuarios", "post"): {"nome": "Maria Souza", "email": "maria@daroca.com.br", "senha": "Maria#2026", "papel": "GESTOR"},
    ("/api/usuarios/{id}", "patch"): {"ativo": False},
    ("/api/produtos", "post"): {"nome": "Ração Canina Premium 15 kg", "categoria": "Rações", "preco_venda": "189,90",
                                "quantidade_atual": 10, "estoque_minimo": 8},
    ("/api/produtos/{id}", "patch"): {"estoque_minimo": 12},
    ("/api/produtos/{id}", "put"): {"nome": "Ração Canina Premium 15 kg", "categoria": "Rações",
                                    "preco_venda": "195,00", "estoque_minimo": 10},
    ("/api/movimentacoes", "post"): {"produto_id": 1, "tipo": "SAIDA", "motivo": "VENDA", "quantidade": 2,
                                     "observacao": "Venda balcão"},
    ("/api/recomendacoes/{id}/decidir", "post"): {"status": "ACEITA"},
    ("/api/recomendacoes/gerar", "post"): {},
    ("/api/categorias", "post"): {"nome": "Veterinária"},
    ("/api/fornecedores", "post"): {"nome": "Nutrimais Distribuidora", "telefone": "(99) 3541-0001", "prazo_entrega_dias": 5},
    ("/api/fornecedores/{id}", "put"): {"nome": "Nutrimais Distribuidora", "prazo_entrega_dias": 6},
}

pastas = {}
for caminho, ops in spec["paths"].items():
    for metodo, op in ops.items():
        if metodo not in ("get", "post", "put", "patch", "delete"):
            continue
        partes = [seg.replace("{id}", "1") for seg in caminho.strip("/").split("/")]
        query = [{"key": p["name"], "value": "", "disabled": True}
                 for p in op.get("parameters", []) if p.get("in") == "query" and "name" in p]
        req = {"method": metodo.upper(), "header": [],
               "url": {"raw": "{{baseUrl}}/" + "/".join(partes), "host": ["{{baseUrl}}"], "path": partes}}
        if query:
            req["url"]["query"] = query
        if (caminho, metodo) in EXEMPLOS:
            req["header"].append({"key": "Content-Type", "value": "application/json"})
            req["body"] = {"mode": "raw", "raw": json.dumps(EXEMPLOS[(caminho, metodo)], ensure_ascii=False, indent=2),
                           "options": {"raw": {"language": "json"}}}
        if op.get("security") == []:
            req["auth"] = {"type": "noauth"}
        item = {"name": f"{metodo.upper()} {caminho} — {op['summary']}", "request": req, "response": []}
        if caminho == "/api/auth/login":
            item["event"] = [{"listen": "test", "script": {"type": "text/javascript", "exec": [
                "const r = pm.response.json();",
                "if (r.token) { pm.collectionVariables.set('token', r.token); }",
                "pm.test('Login retornou token', () => pm.expect(r.token).to.be.a('string'));"]}}]
        pastas.setdefault(op["tags"][0], []).append(item)

colecao = {
    "info": {"_postman_id": str(uuid.uuid4()), "name": "AgroEstoque API v3.0",
             "description": "Execute primeiro 'POST /api/auth/login'; o token é salvo automaticamente em {{token}}.",
             "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
    "auth": {"type": "bearer", "bearer": [{"key": "token", "value": "{{token}}", "type": "string"}]},
    "variable": [{"key": "baseUrl", "value": "http://127.0.0.1:5000"}, {"key": "token", "value": ""}],
    "item": [{"name": t, "item": i} for t, i in pastas.items()],
}
saida = RAIZ / "docs" / "api" / "AgroEstoque.postman_collection.json"
saida.write_text(json.dumps(colecao, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"{sum(len(i) for i in pastas.values())} requisições em {len(pastas)} pastas -> {saida}")
