# -*- coding: utf-8 -*-
"""Testes do Motor Universal (scripts/motor.py) -- valida que o mesmo motor
reproduz o CENTRAL (modelo 'grupo', 2 turnos) e a NORTE (modelo 'grupo', dupla
fixa + folga legal por data), sem nenhum código específico de posto, e que
postos são isolados entre si."""
import copy
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import regra_rodizio as rr
import motor

DADOS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dados.example.json")


def _dados_central_generico():
    dados = json.load(open(DADOS_PATH, encoding="utf-8"))
    dados["modelo_rotacao"] = "grupo"
    dados["turnos"] = [
        {"id": "0719", "n_posicoes": 2, "modo_fds": "alterna"},
        {"id": "1022", "n_posicoes": 2, "modo_fds": "unico"},
    ]
    return dados


def test_central_painel_do_ano_generico_bate_com_original():
    """Regressão: as estatísticas do painel do ano genérico (motor.py) têm
    que bater exatamente com as do painel original do CENTRAL (regra_rodizio.py)
    -- dias trabalhados por mês e folgões automáticos por pessoa."""
    dados_original = rr.carregar_dados(DADOS_PATH)
    dados_generico = rr.carregar_dados(DADOS_PATH)
    dados_generico["modelo_rotacao"] = "grupo"
    dados_generico["turnos"] = [
        {"id": "0719", "n_posicoes": 2, "modo_fds": "alterna"},
        {"id": "1022", "n_posicoes": 2, "modo_fds": "unico"},
    ]

    hoje = datetime.date(2026, 7, 23)
    for mes in range(1, 13):
        nome_mes = rr.MES_NOMES[mes]
        overrides = dados_original.get("overrides_fds", {}).get(nome_mes, {})
        esperado = rr.dias_trabalhados_mes(dados_original, 2026, mes, overrides)
        obtido = motor.dias_trabalhados_mes_generico(dados_generico, 2026, mes, dados_generico.get("overrides_fds", {}))
        assert obtido == esperado, f"mês {mes}: esperado {esperado}, obtido {obtido}"

    for p in dados_original["equipe"]:
        nome = p["nome"]
        esperado = rr.folgoes_automaticos_ano(dados_original, nome, 2026, hoje)
        obtido = motor.folgoes_automaticos_ano_generico(dados_generico, nome, 2026, hoje)
        assert obtido == esperado, f"{nome}: esperado {esperado}, obtido {obtido}"


def test_central_motor_generico_igual_ao_original_2026_2027():
    dados_original = json.load(open(DADOS_PATH, encoding="utf-8"))
    dados_generico = _dados_central_generico()
    for ano in (2026, 2027):
        for mes in range(1, 13):
            dias_antigo = rr.computar_mes(dados_original, ano, mes)
            dias_novo = motor.computar_mes_generico(dados_generico, ano, mes)
            for a, n in zip(dias_antigo, dias_novo):
                t0719 = n["turnos"]["0719"]["valores"]
                t1022 = n["turnos"]["1022"]["valores"]
                esperado = (a["pos_0719_1"], a["pos_0719_2"], a["pos_1022_1"], a["pos_1022_2"])
                obtido = (t0719[0], t0719[1], t1022[0], t1022[1])
                assert obtido == esperado, f"{a['data']}: esperado {esperado}, obtido {obtido}"


def _posto_norte():
    dados = motor.novo_posto(
        nome="NORTE", empresa="EMPRESA NORTE", ancora_iso="2026-06-01",
        turnos=[
            {"id": "0719", "n_posicoes": 1, "modo_fds": "parceiro_ativo"},
            {"id": "0921", "n_posicoes": 1, "modo_fds": "parceiro_ativo"},
        ],
        modelo_rotacao="grupo",
        equipe=[
            {"nome": "LUCAS", "equipe": "Bravo", "turno": "0719", "pos": 1},
            {"nome": "RAFAEL", "equipe": "Alfa", "turno": "0719", "pos": 1},
            {"nome": "FELIPE", "equipe": "Bravo", "turno": "0921", "pos": 1},
            {"nome": "MATEUS", "equipe": "Alfa", "turno": "0921", "pos": 1},
        ],
    )
    dados["folgas_legais"] = {
        "2026-06": {"RAFAEL": [6, 14], "MATEUS": [20, 28], "FELIPE": [13, 21], "LUCAS": [7, 27]},
        "2026-07": {"RAFAEL": [4, 12], "MATEUS": [18, 26], "FELIPE": [11, 19], "LUCAS": [5, 25]},
    }
    dados["ferias"] = [{"pessoa": "RAFAEL", "inicio": "2026-07-20", "fim": "2026-08-18", "substituto": "IVO"}]
    return dados


# Referência verificada célula a célula contra as escalas reais BCI NORTE
# nº 06/2026 e nº 07/2026 (NORTE_escalas_referencia_verificada.md).
REF_JUNHO_2026 = {
    1: ("LUCAS", "FELIPE"), 2: ("RAFAEL", "MATEUS"), 3: ("LUCAS", "FELIPE"),
    4: ("RAFAEL", "MATEUS"), 5: ("LUCAS", "FELIPE"), 6: "MATEUS", 7: "FELIPE",
    8: ("RAFAEL", "MATEUS"), 9: ("LUCAS", "FELIPE"), 10: ("RAFAEL", "MATEUS"),
    11: ("LUCAS", "FELIPE"), 12: ("RAFAEL", "MATEUS"), 13: "LUCAS", 14: "MATEUS",
    15: ("LUCAS", "FELIPE"), 16: ("RAFAEL", "MATEUS"), 17: ("LUCAS", "FELIPE"),
    18: ("RAFAEL", "MATEUS"), 19: ("LUCAS", "FELIPE"), 20: "RAFAEL", 21: "LUCAS",
    22: ("RAFAEL", "MATEUS"), 23: ("LUCAS", "FELIPE"), 24: ("RAFAEL", "MATEUS"),
    25: ("LUCAS", "FELIPE"), 26: ("RAFAEL", "MATEUS"), 27: "FELIPE", 28: "RAFAEL",
    29: ("LUCAS", "FELIPE"), 30: ("RAFAEL", "MATEUS"),
}
REF_JULHO_2026 = {
    1: ("LUCAS", "FELIPE"), 2: ("RAFAEL", "MATEUS"), 3: ("LUCAS", "FELIPE"),
    4: "MATEUS", 5: "FELIPE",
    6: ("RAFAEL", "MATEUS"), 7: ("LUCAS", "FELIPE"), 8: ("RAFAEL", "MATEUS"),
    9: ("LUCAS", "FELIPE"), 10: ("RAFAEL", "MATEUS"), 11: "LUCAS", 12: "MATEUS",
    13: ("LUCAS", "FELIPE"), 14: ("RAFAEL", "MATEUS"), 15: ("LUCAS", "FELIPE"),
    16: ("RAFAEL", "MATEUS"), 17: ("LUCAS", "FELIPE"), 18: "RAFAEL", 19: "LUCAS",
    20: ("IVO", "MATEUS"), 21: ("LUCAS", "FELIPE"), 22: ("IVO", "MATEUS"),
    23: ("LUCAS", "FELIPE"), 24: ("IVO", "MATEUS"), 25: "FELIPE", 26: "IVO",
    27: ("LUCAS", "FELIPE"), 28: ("IVO", "MATEUS"), 29: ("LUCAS", "FELIPE"),
    30: ("IVO", "MATEUS"), 31: ("LUCAS", "FELIPE"),
}


def _checar_norte(dados, ano, mes, referencia):
    dias = motor.computar_mes_generico(dados, ano, mes)
    for d in dias:
        dia = d["dia"]
        esperado = referencia[dia]
        v0719 = d["turnos"]["0719"]["valores"][0]
        v0921 = d["turnos"]["0921"]["valores"][0]
        obtido = (v0719, v0921) if isinstance(esperado, tuple) else (v0719 or v0921)
        assert obtido == esperado, f"{ano}-{mes:02d}-{dia:02d}: esperado {esperado}, obtido ({v0719},{v0921})"


def test_norte_junho_2026_bate_com_escala_real():
    _checar_norte(_posto_norte(), 2026, 6, REF_JUNHO_2026)


def test_norte_julho_2026_bate_com_escala_real_incluindo_ferias_e_cobertura():
    _checar_norte(_posto_norte(), 2026, 7, REF_JULHO_2026)


def test_posto_ficticio_4_pessoas_2_grupos_alterna_sem_quebra():
    p = motor.novo_posto(
        "Ficticio4", "TesteCo", "2026-01-01",
        turnos=[{"id": "0719", "n_posicoes": 2, "modo_fds": "alterna"}],
        modelo_rotacao="grupo",
        equipe=[
            {"nome": "A1", "equipe": "Alfa", "turno": "0719", "pos": 1},
            {"nome": "A2", "equipe": "Alfa", "turno": "0719", "pos": 2},
            {"nome": "B1", "equipe": "Bravo", "turno": "0719", "pos": 1},
            {"nome": "B2", "equipe": "Bravo", "turno": "0719", "pos": 2},
        ],
    )
    ancora = datetime.date(2026, 1, 1)
    dia_anterior = equipe_anterior = None
    for ano in (2026, 2027):
        for mes in range(1, 13):
            for d in motor.computar_mes_generico(p, ano, mes):
                data = datetime.date.fromisoformat(d["data"])
                diff = (data - ancora).days
                equipe_esperada = "Alfa" if diff % 2 == 0 else "Bravo"
                if dia_anterior is not None and (data - dia_anterior).days == 1:
                    assert equipe_anterior != equipe_esperada, f"equipe nao alternou em {d['data']}"
                dia_anterior, equipe_anterior = data, equipe_esperada
                dow = (data.weekday() + 1) % 7
                v = d["turnos"]["0719"]["valores"]
                if dow == 0:
                    assert v[0] == ""
                if dow == 6:
                    assert v[1] == ""


def test_posto_ficticio_8_pessoas_2_grupos_2_turnos():
    p = motor.novo_posto(
        "Ficticio8", "TesteCo", "2027-03-15",
        turnos=[
            {"id": "0719", "n_posicoes": 2, "modo_fds": "alterna"},
            {"id": "1022", "n_posicoes": 2, "modo_fds": "unico"},
        ],
        modelo_rotacao="grupo",
        equipe=[
            {"nome": "A1", "equipe": "Alfa", "turno": "0719", "pos": 1},
            {"nome": "A2", "equipe": "Alfa", "turno": "0719", "pos": 2},
            {"nome": "A3", "equipe": "Alfa", "turno": "1022", "pos": 1},
            {"nome": "A4", "equipe": "Alfa", "turno": "1022", "pos": 2},
            {"nome": "B1", "equipe": "Bravo", "turno": "0719", "pos": 1},
            {"nome": "B2", "equipe": "Bravo", "turno": "0719", "pos": 2},
            {"nome": "B3", "equipe": "Bravo", "turno": "1022", "pos": 1},
            {"nome": "B4", "equipe": "Bravo", "turno": "1022", "pos": 2},
        ],
    )
    for ano in (2026, 2027):
        for mes in range(1, 13):
            for d in motor.computar_mes_generico(p, ano, mes):
                data = datetime.date.fromisoformat(d["data"])
                dow = (data.weekday() + 1) % 7
                v0719 = d["turnos"]["0719"]["valores"]
                v1022 = d["turnos"]["1022"]["valores"]
                if dow == 0:
                    assert v0719[0] == ""
                if dow == 6:
                    assert v0719[1] == ""
                if dow in (0, 6):
                    assert v1022[1] == ""
                else:
                    assert "" not in v0719 and "" not in v1022


def test_modelo_individual_rotacao_por_fila_com_bloco_trabalho_folga():
    p = motor.novo_posto(
        "FicticioIndividual", "TesteCo", "2026-01-01",
        turnos=[{"id": "unico", "n_posicoes": 1, "modo_fds": "alterna"}],
        modelo_rotacao="individual", dias_trabalho=6, dias_folga=2,
        equipe=[{"nome": "P1", "turno": "unico"}, {"nome": "P2", "turno": "unico"}, {"nome": "P3", "turno": "unico"}],
    )
    ancora = datetime.date(2026, 1, 1)
    ciclo = 8
    for d in motor.computar_mes_generico(p, 2026, 3):
        data = datetime.date.fromisoformat(d["data"])
        diff = (data - ancora).days
        num_ciclo, dia_no_ciclo = divmod(diff, ciclo)
        esperado = ["P1", "P2", "P3"][num_ciclo % 3] if dia_no_ciclo < 6 else ""
        assert d["turnos"]["unico"]["valores"][0] == esperado


def test_isolamento_entre_postos():
    equipe_base = [
        {"nome": "X1", "equipe": "Alfa", "turno": "t", "pos": 1},
        {"nome": "X2", "equipe": "Alfa", "turno": "t", "pos": 2},
        {"nome": "Y1", "equipe": "Bravo", "turno": "t", "pos": 1},
        {"nome": "Y2", "equipe": "Bravo", "turno": "t", "pos": 2},
    ]
    posto1 = motor.novo_posto("P1", "Empresa1", "2026-01-01",
                               turnos=[{"id": "t", "n_posicoes": 2, "modo_fds": "alterna"}],
                               modelo_rotacao="grupo", equipe=copy.deepcopy(equipe_base))
    posto2 = motor.novo_posto("P2", "Empresa2", "2026-01-01",
                               turnos=[{"id": "t", "n_posicoes": 2, "modo_fds": "alterna"}],
                               modelo_rotacao="grupo", equipe=copy.deepcopy(equipe_base))
    antes = copy.deepcopy(posto2)

    posto1["folgas"].append({"pessoa": "X1", "data": "2026-01-06", "substituto": "SUBSTITUTO"})
    posto1["equipe"][0]["nome"] = "RENOMEADO"

    assert posto2["folgas"] == antes["folgas"]
    assert posto2["equipe"] == antes["equipe"]


def test_alteracao_manual_afeta_so_o_dia_e_ciclo_volta_no_dia_seguinte():
    p = motor.novo_posto(
        "P1", "Empresa1", "2026-01-01",
        turnos=[{"id": "t", "n_posicoes": 2, "modo_fds": "alterna"}],
        modelo_rotacao="grupo",
        equipe=[
            {"nome": "X1", "equipe": "Alfa", "turno": "t", "pos": 1},
            {"nome": "X2", "equipe": "Alfa", "turno": "t", "pos": 2},
            {"nome": "Y1", "equipe": "Bravo", "turno": "t", "pos": 1},
            {"nome": "Y2", "equipe": "Bravo", "turno": "t", "pos": 2},
        ],
    )
    p["folgas"].append({"pessoa": "X1", "data": "2026-01-06", "substituto": "SUBSTITUTO"})
    dias = {d["dia"]: d for d in motor.computar_mes_generico(p, 2026, 1)}
    assert dias[6]["turnos"]["t"]["valores"] == ["SUBSTITUTO", "X2"]
    assert dias[7]["turnos"]["t"]["valores"] == dias[5]["turnos"]["t"]["valores"]
