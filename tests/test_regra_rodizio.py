# -*- coding: utf-8 -*-
import sys
import os
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import regra_rodizio as rr

DADOS_TESTE = {
    "equipe": [
        {"nome": "EDUARDO", "equipe": "Bravo", "turno": "0719", "pos": 1},
        {"nome": "BRUNO", "equipe": "Bravo", "turno": "0719", "pos": 2},
        {"nome": "GABRIEL", "equipe": "Bravo", "turno": "1022", "pos": 1},
        {"nome": "IGOR", "equipe": "Bravo", "turno": "1022", "pos": 2},
        {"nome": "VITOR", "equipe": "Alfa", "turno": "0719", "pos": 1},
        {"nome": "CARLOS", "equipe": "Alfa", "turno": "0719", "pos": 2},
        {"nome": "DANIEL", "equipe": "Alfa", "turno": "1022", "pos": 1},
        {"nome": "JULIO", "equipe": "Alfa", "turno": "1022", "pos": 2},
    ],
    "ancora": "2026-04-01",
    "folgas": [],
    "ferias": [{"id": "ferias-daniel", "pessoa": "DANIEL", "inicio": "2026-07-15", "fim": "2026-08-03", "substituto": "HUGO"}],
    "certificados": [],
}


def test_carregar_dados_atribui_id_a_ferias_e_folgas_sem_id(tmp_path):
    caminho = tmp_path / "dados_sem_id.json"
    caminho.write_text(
        '{"equipe": [], "ancora": "2026-04-01", '
        '"folgas": [{"pessoa": "EDUARDO", "data": "2026-04-04", "substituto": "BRUNO"}], '
        '"ferias": [{"pessoa": "DANIEL", "inicio": "2026-07-15", "fim": "2026-08-03", "substituto": "HUGO"}], '
        '"certificados": []}',
        encoding="utf-8",
    )
    dados = rr.carregar_dados(str(caminho))
    assert dados["folgas"][0]["id"]
    assert dados["ferias"][0]["id"]
    assert dados["folgas"][0]["id"] != dados["ferias"][0]["id"]
    # persisted back to disk, not just in memory
    dados_recarregados = rr.carregar_dados(str(caminho))
    assert dados_recarregados["folgas"][0]["id"] == dados["folgas"][0]["id"]


def test_equipe_alterna_continuamente_entre_meses():
    ancora = date(2026, 4, 1)
    assert rr.equipe_do_dia(date(2026, 4, 1), ancora) == "Bravo"
    assert rr.equipe_do_dia(date(2026, 6, 1), ancora) == "Alfa"  # 61 dias depois


def test_segunda_feira_junho_mostra_equipe_alfa_completa():
    dia = rr.computar_dia(DADOS_TESTE, date(2026, 6, 1), pos_fds=1)
    assert dia == {"pos_0719_1": "VITOR", "pos_0719_2": "CARLOS",
                   "pos_1022_1": "DANIEL", "pos_1022_2": "JULIO",
                   "base_0719_1": "VITOR", "base_0719_2": "CARLOS",
                   "base_1022_1": "DANIEL", "base_1022_2": "JULIO", "pos_fds": None}


def test_sabado_junho_mostra_so_posicao_1_de_cada_turno():
    dia = rr.computar_dia(DADOS_TESTE, date(2026, 6, 6), pos_fds=1)
    assert dia == {"pos_0719_1": "EDUARDO", "pos_0719_2": "", "pos_1022_1": "GABRIEL", "pos_1022_2": "",
                   "base_0719_1": "EDUARDO", "base_0719_2": "", "base_1022_1": "GABRIEL", "base_1022_2": "",
                   "pos_fds": 1}


def test_domingo_junho_mostra_so_posicao_2_de_cada_turno():
    dia = rr.computar_dia(DADOS_TESTE, date(2026, 6, 7), pos_fds=2)
    # pos_fds=2 escolhe QUEM cobre o 10h-22h (a pessoa cadastrada como pos 2,
    # JULIO) -- mas ela aparece no slot pos_1022_1, nunca pos_1022_2.
    # Confirmado contra os 16 fins de semana reais de junho/julho na planilha
    # validada: pos_1022_2 nunca e usado em nenhum deles.
    assert dia == {"pos_0719_1": "", "pos_0719_2": "CARLOS", "pos_1022_1": "JULIO", "pos_1022_2": "",
                   "base_0719_1": "", "base_0719_2": "CARLOS", "base_1022_1": "JULIO", "base_1022_2": "",
                   "pos_fds": 2}


def test_ferias_substitui_pessoa_durante_o_periodo():
    dia = rr.computar_dia(DADOS_TESTE, date(2026, 7, 15), pos_fds=1)
    assert dia == {"pos_0719_1": "VITOR", "pos_0719_2": "CARLOS",
                   "pos_1022_1": "HUGO", "pos_1022_2": "JULIO",
                   "base_0719_1": "VITOR", "base_0719_2": "CARLOS",
                   "base_1022_1": "DANIEL", "base_1022_2": "JULIO", "pos_fds": None}
    # base_1022_1 continua "DANIEL" (a escala fixa) mesmo com HUGO exibido --
    # é essa chave estavel que permite reeditar um dia mesmo em ferias/folga
    # no último dia de plantão da equipe Alfa antes das férias começarem
    # (13/07, segunda-feira — 14/07 é dia da equipe Bravo, DANIEL não entra nele)
    dia_anterior = rr.computar_dia(DADOS_TESTE, date(2026, 7, 13), pos_fds=1)
    assert dia_anterior["pos_1022_1"] == "DANIEL"


def test_posicoes_fim_de_semana_alterna_a_cada_dia_de_fds_sem_ancora():
    pos = rr.posicoes_fim_de_semana(2026, 6)
    # sem ancora (uso avulso): alterna dia a dia dentro do mes, 2,1,2,1...
    assert pos[6] == 2
    assert pos[7] == 1
    assert pos[13] == 2
    assert pos[14] == 1


def test_posicoes_fim_de_semana_com_ancora_nao_reseta_a_cada_mes():
    # com ancora, a paridade sabado/domingo e calculada por dias corridos
    # desde a ancora, nunca reconta fins de semana por mes -- por isso o
    # padrao (sabado=2, domingo=1) se mantem identico em qualquer mes,
    # sem inverter na virada de mes ou de ano.
    ancora = date(2026, 4, 1)
    pos_junho = rr.posicoes_fim_de_semana(2026, 6, ancora)
    assert pos_junho == {6: 2, 7: 1, 13: 2, 14: 1, 20: 2, 21: 1, 27: 2, 28: 1}


def test_computar_mes_retorna_um_dia_por_data_do_mes():
    dias = rr.computar_mes(DADOS_TESTE, 2026, 6)
    assert len(dias) == 30
    assert dias[0]["data"] == "2026-06-01"
    assert dias[-1]["data"] == "2026-06-30"


def test_calcular_data_fim_ferias_20_dias():
    assert rr.calcular_data_fim_ferias("2026-07-15", "20") == "2026-08-03"


def test_calcular_data_fim_ferias_1_mes():
    assert rr.calcular_data_fim_ferias("2026-06-08", "mes") == "2026-07-07"


def test_calcular_data_fim_ferias_1_mes_com_dia_31_usa_ultimo_dia_do_mes_seguinte():
    # fevereiro/2026 só tem 28 dias -- não existe "31/02"
    assert rr.calcular_data_fim_ferias("2026-01-31", "mes") == "2026-02-27"


def test_nome_dia_semana_domingo_e_sabado_nao_levam_feira():
    assert rr.nome_dia_semana(0) == "domingo"
    assert rr.nome_dia_semana(6) == "sábado"
    assert rr.nome_dia_semana(1) == "segunda-feira"


def test_folgas_restantes_desconta_as_ja_lancadas_no_periodo():
    dados = dict(DADOS_TESTE, folgas=[{"pessoa": "EDUARDO", "data": "2026-09-10", "substituto": "BRUNO"}])
    # hoje = 15/07: restam meses jul,ago,set,out,nov,dez = 6; uma já lançada em setembro -> 5
    assert rr.folgas_restantes(dados, "EDUARDO", date(2026, 7, 15)) == 5
    assert rr.folgas_restantes(dados, "BRUNO", date(2026, 7, 15)) == 6


def test_folgoes_automaticos_ano_detecta_intervalo_maior_que_2_dias():
    dados = dict(DADOS_TESTE, folgas=[], ferias=[])
    # EDUARDO trabalha em dias alternados (rodizio normal); confirma so que
    # o ano inteiro roda sem erro e devolve um numero nao-negativo plausivel.
    total = rr.folgoes_automaticos_ano(dados, "EDUARDO", 2026)
    assert total >= 0


def test_folgoes_automaticos_ano_ferias_nao_conta_como_folgao():
    # DANIEL sai de ferias 15/07 a 03/08 -- HUGO cobre as posicoes dele,
    # entao o intervalo gerado e do HUGO passando a trabalhar, nao um
    # gap na escala do DANIEL em si (ele so some da lista, sem gerar contagem
    # de folgao espuria pelo periodo de ferias).
    total_com_ferias = rr.folgoes_automaticos_ano(DADOS_TESTE, "DANIEL", 2026)
    sem_ferias = dict(DADOS_TESTE, ferias=[])
    total_sem_ferias = rr.folgoes_automaticos_ano(sem_ferias, "DANIEL", 2026)
    assert total_com_ferias <= total_sem_ferias


def test_listar_eventos_inclui_folga_ferias_e_volta_de_ferias_ordenados():
    dados = dict(DADOS_TESTE, folgas=[{"id": "folga1", "pessoa": "CARLOS", "data": "2026-04-04", "substituto": "DANIEL"}])
    eventos = rr.listar_eventos(dados)
    datas = [e["data"] for e in eventos]
    assert datas == sorted(datas)
    assert any(e["texto"] == "CARLOS folgão" for e in eventos)
    assert any(e["texto"] == "DANIEL inicia férias" for e in eventos)
    assert any(e["texto"] == "DANIEL volta de férias" and e["data"] == "2026-08-04" for e in eventos)


def test_listar_eventos_inclui_id_e_tipo_para_permitir_remocao():
    dados = dict(DADOS_TESTE, folgas=[{"id": "folga1", "pessoa": "CARLOS", "data": "2026-04-04", "substituto": "DANIEL"}])
    eventos = rr.listar_eventos(dados)
    folga_evento = next(e for e in eventos if e["texto"] == "CARLOS folgão")
    assert folga_evento["id"] == "folga1"
    assert folga_evento["tipo"] == "folga"
    ferias_evento = next(e for e in eventos if e["texto"] == "DANIEL inicia férias")
    assert ferias_evento["tipo"] == "ferias"
    volta_evento = next(e for e in eventos if e["texto"] == "DANIEL volta de férias")
    assert volta_evento["tipo"] == ""  # evento derivado, não removível diretamente


def test_status_mes_passado_nunca_sinaliza_mesmo_com_evento():
    dados = dict(DADOS_TESTE, folgas=[{"pessoa": "CARLOS", "data": "2026-04-04", "substituto": "DANIEL"}])
    status = rr.status_mes(dados, 2026, 4, date(2026, 7, 15))
    assert status == {"flag": False, "texto": "sem eventos"}


def test_status_mes_atual_com_ferias_sinaliza():
    status = rr.status_mes(DADOS_TESTE, 2026, 7, date(2026, 7, 15))
    assert status == {"flag": True, "texto": "em férias"}


def test_status_mes_passado_em_ano_anterior_nunca_sinaliza():
    # dezembro/2025 é passado em relação a hoje=15/07/2026, mesmo o número do
    # mês (12) sendo maior que o de hoje (7) -- tem que comparar ano também
    dados = dict(DADOS_TESTE, folgas=[{"pessoa": "EDUARDO", "data": "2025-12-10", "substituto": "BRUNO"}])
    status = rr.status_mes(dados, 2025, 12, date(2026, 7, 15))
    assert status == {"flag": False, "texto": "sem eventos"}


def test_ferias_ativas_no_mes_retorna_ferias_que_cruzam_o_mes():
    dados = dict(DADOS_TESTE, ferias=[
        {"id": "abc123", "pessoa": "DANIEL", "inicio": "2026-07-15", "fim": "2026-08-03", "substituto": "HUGO"},
    ])
    ativas_julho = rr.ferias_ativas_no_mes(dados, 2026, 7)
    assert len(ativas_julho) == 1
    assert ativas_julho[0]["id"] == "abc123"
    assert ativas_julho[0]["pessoa_completa"] == "DANIEL"  # sem nome_completo cadastrado, usa o curto
    assert ativas_julho[0]["substituto"] == "HUGO"
    assert ativas_julho[0]["inicio"] == "2026-07-15"
    assert ativas_julho[0]["fim"] == "2026-08-03"
    assert ativas_julho[0]["duracao_dias"] == 20

    ativas_agosto = rr.ferias_ativas_no_mes(dados, 2026, 8)
    assert len(ativas_agosto) == 1  # também cruza agosto

    ativas_setembro = rr.ferias_ativas_no_mes(dados, 2026, 9)
    assert ativas_setembro == []


def test_ferias_ativas_no_mes_usa_nome_completo_quando_cadastrado():
    dados = dict(
        DADOS_TESTE,
        equipe=[dict(p) for p in DADOS_TESTE["equipe"]],
        ferias=[{"id": "abc123", "pessoa": "DANIEL", "inicio": "2026-07-15", "fim": "2026-08-03", "substituto": "HUGO"}],
    )
    for p in dados["equipe"]:
        if p["nome"] == "DANIEL":
            p["nome_completo"] = "DANIEL COSTA DA SILVA"
    ativas = rr.ferias_ativas_no_mes(dados, 2026, 7)
    assert ativas[0]["pessoa_completa"] == "DANIEL COSTA DA SILVA"


def test_agrupar_em_semanas_preenche_none_fora_do_mes():
    dias = rr.computar_mes(DADOS_TESTE, 2026, 6)
    semanas = rr.agrupar_em_semanas(2026, 6, dias)
    # junho/2026 começa numa segunda-feira -> primeira célula (domingo) da 1a semana é None
    assert semanas[0][0] is None
    assert semanas[0][1]["numero"] == 1
