# -*- coding: utf-8 -*-
import sys
import os
import json
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "site"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))


def _preparar_app(tmp_path, monkeypatch):
    """Copia o dados.example.json (dados ficticios) pra um arquivo temporário e aponta o app pra ele,
    pra cada teste rodar isolado sem afetar o dados.json de produção."""
    origem = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dados.example.json")
    destino = tmp_path / "dados.json"
    shutil.copy(origem, destino)
    import app as app_module
    monkeypatch.setattr(app_module, "DADOS_PATH", str(destino))
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client(), destino


def test_api_renomear_grava_nome_completo(tmp_path, monkeypatch):
    client, destino = _preparar_app(tmp_path, monkeypatch)
    resp = client.post(
        "/api/renomear",
        json={"nome_antigo": "DANIEL", "nome_novo": "DANIEL", "nome_completo": "DANIEL COSTA DA SILVA"},
    )
    assert resp.status_code == 200
    dados = json.loads(destino.read_text(encoding="utf-8"))
    pessoa = next(p for p in dados["equipe"] if p["nome"] == "DANIEL")
    assert pessoa["nome_completo"] == "DANIEL COSTA DA SILVA"


def test_api_renomear_sem_nome_completo_nao_apaga_o_existente(tmp_path, monkeypatch):
    client, destino = _preparar_app(tmp_path, monkeypatch)
    client.post(
        "/api/renomear",
        json={"nome_antigo": "DANIEL", "nome_novo": "DANIEL", "nome_completo": "DANIEL COSTA DA SILVA"},
    )
    resp = client.post("/api/renomear", json={"nome_antigo": "DANIEL", "nome_novo": "DANIEL"})
    assert resp.status_code == 200
    dados = json.loads(destino.read_text(encoding="utf-8"))
    pessoa = next(p for p in dados["equipe"] if p["nome"] == "DANIEL")
    assert pessoa["nome_completo"] == "DANIEL COSTA DA SILVA"


def test_api_certificados_regrava_a_lista_inteira(tmp_path, monkeypatch):
    client, destino = _preparar_app(tmp_path, monkeypatch)
    nova_lista = [
        {"pessoa": "EDUARDO", "codigo": "99-99"},
        {"pessoa": "BRUNO", "codigo": "05-19"},
        {"pessoa": "GABRIEL", "codigo": "11-25"},
        {"pessoa": "IGOR", "codigo": "11-25"},
        {"pessoa": "VITOR", "codigo": "12-26"},
        {"pessoa": "CARLOS", "codigo": "04-12"},
        {"pessoa": "DANIEL", "codigo": "18-26"},
        {"pessoa": "JULIO", "codigo": "04-18"},
    ]
    resp = client.post("/api/certificados", json={"certificados": nova_lista})
    assert resp.status_code == 200
    dados = json.loads(destino.read_text(encoding="utf-8"))
    assert dados["certificados"] == nova_lista


def test_api_ferias_remover_apaga_o_registro(tmp_path, monkeypatch):
    client, destino = _preparar_app(tmp_path, monkeypatch)
    dados_antes = json.loads(destino.read_text(encoding="utf-8"))
    ferias_id = dados_antes["ferias"][0]["id"]
    resp = client.post("/api/ferias/remover", json={"id": ferias_id})
    assert resp.status_code == 200
    dados_depois = json.loads(destino.read_text(encoding="utf-8"))
    assert all(f["id"] != ferias_id for f in dados_depois["ferias"])


def test_api_folga_remover_apaga_o_registro(tmp_path, monkeypatch):
    client, destino = _preparar_app(tmp_path, monkeypatch)
    dados_antes = json.loads(destino.read_text(encoding="utf-8"))
    folga_id = dados_antes["folgas"][0]["id"]
    resp = client.post("/api/folga/remover", json={"id": folga_id})
    assert resp.status_code == 200
    dados_depois = json.loads(destino.read_text(encoding="utf-8"))
    assert all(f["id"] != folga_id for f in dados_depois["folgas"])


def test_api_ferias_editar_substituto_troca_so_o_substituto(tmp_path, monkeypatch):
    client, destino = _preparar_app(tmp_path, monkeypatch)
    dados_antes = json.loads(destino.read_text(encoding="utf-8"))
    ferias = dados_antes["ferias"][0]
    resp = client.post(
        "/api/ferias/editar-substituto",
        json={"id": ferias["id"], "substituto": "OUTRO SUBSTITUTO"},
    )
    assert resp.status_code == 200
    dados_depois = json.loads(destino.read_text(encoding="utf-8"))
    ferias_depois = next(f for f in dados_depois["ferias"] if f["id"] == ferias["id"])
    assert ferias_depois["substituto"] == "OUTRO SUBSTITUTO"
    assert ferias_depois["pessoa"] == ferias["pessoa"]
    assert ferias_depois["inicio"] == ferias["inicio"]
    assert ferias_depois["fim"] == ferias["fim"]
