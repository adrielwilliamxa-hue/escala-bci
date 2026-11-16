# -*- coding: utf-8 -*-
"""Motor Universal de Escalas.

Único motor de cálculo para qualquer posto de Brigada Contra Incêndio.
Toda a matemática (data-base, dias corridos, rodízio contínuo sem
recontagem por mês/ano, substituições pontuais) vem de regra_rodizio.py,
já auditada e validada contra as escalas oficiais do CENTRAL. Este módulo não
reimplementa essa matemática -- apenas generaliza a ESTRUTURA do posto
(quantos turnos, quantas posições, qual modelo de rotação) em parâmetros.

Dois modelos de rotação, ambos amarrados a "distância em dias desde a
âncora", nunca a posição de calendário:

  - "grupo": um responsável por posição do turno, escolhido por qual das 2
    equipes (nomeadas) está de plantão naquele dia -- exatamente o modelo
    do CENTRAL (regra_rodizio.equipe_do_dia). Cada posição do turno tem 2
    pessoas fixas que se alternam dia a dia.
  - "individual": N brigadistas nomeados em fila, sem grupo. Cada um
    trabalha um bloco de `dias_trabalho` dias corridos e depois folga um
    bloco de `dias_folga` dias corridos, revezando em fila -- o padrão da
    Lei 11.901/2009 observado na NORTE. Quem está de plantão em cada dia é
    calculado só por (dias desde a âncora) dividido pelo ciclo, nunca por
    dia da semana ou do mês.

Fim de semana: cada turno declara `modo_fds`, um entre três comportamentos
reais já confirmados em escalas oficiais -- não é recalculado por modelo
de rotação, é o mesmo parâmetro em qualquer modelo:

  - "alterna": cada posição só aparece no dia (sábado OU domingo) que lhe
    cabe -- padrão do turno 0719 do CENTRAL.
  - "unico": uma posição escolhida por posicoes_fim_de_semana cobre
    sábado E domingo sozinha -- padrão do turno 1022 do CENTRAL.
  - "parceiro_ativo": as pessoas do turno formam duplas fixas (a mesma
    dupla que alterna nos dias de semana). dados["folgas_legais"][mes_iso]
    [pessoa] = [dia1, dia2] são as DUAS datas (dias do mês, não um
    intervalo) em que aquela pessoa folga naquele mês. Sempre que o
    sábado ou domingo cai numa dessas datas, quem cobre sozinho o dia
    inteiro é o parceiro fixo dela -- padrão real da NORTE (Lei
    11.901/2009), validado célula a célula contra 16 fins de semana reais
    (junho+julho/2026) sem exceção.
"""
import calendar
import datetime

import regra_rodizio as rr

equipe_do_dia = rr.equipe_do_dia
posicoes_fim_de_semana = rr.posicoes_fim_de_semana
aplicar_substituicoes = rr.aplicar_substituicoes
encontrar_pessoa = rr.encontrar_pessoa
_dow = rr._dow


def _mapa_parceiros(dados):
    """Modelo 'grupo': dentro de cada equipe (Alfa/Bravo), as pessoas de
    diferentes turnos que trabalham no mesmo dia são parceiras fixas --
    ex.: LUCAS(turno 0719, Bravo) e FELIPE(turno 0921, Bravo) sempre
    trabalham juntos, alternando com RAFAEL/MATEUS (Alfa) no dia
    seguinte. Retorna {nome: nome_do_parceiro}."""
    por_equipe = {}
    for p in dados["equipe"]:
        por_equipe.setdefault(p["equipe"], []).append(p["nome"])
    parceiros = {}
    for nomes in por_equipe.values():
        if len(nomes) == 2:
            parceiros[nomes[0]] = nomes[1]
            parceiros[nomes[1]] = nomes[0]
    return parceiros


def _pessoa_de_folga_legal(dados, data):
    """Retorna o nome da pessoa cuja data de folga legal do mês (uma das
    duas datas cadastradas) cai em `data`, ou None se ninguém folga hoje."""
    mes_iso = f"{data.year:04d}-{data.month:02d}"
    folgas_mes = dados.get("folgas_legais", {}).get(mes_iso, {})
    for pessoa, datas in folgas_mes.items():
        if data.day in datas:
            return pessoa
    return None


def _pessoa_individual(pessoas, ciclo_total, dias_trabalho, data, ancora):
    """Modelo 'individual': `pessoas` é uma fila fixa (ordem de cadastro).
    O ciclo tem `ciclo_total` dias (dias_trabalho + dias_folga); dentro do
    ciclo, os primeiros `dias_trabalho` dias são de plantão dessa pessoa.
    A fila avança 1 pessoa a cada ciclo completo -- puro (dias desde a
    âncora) // ciclo_total, nunca dia do mês ou da semana."""
    diff = (data - ancora).days
    numero_ciclo, dia_no_ciclo = divmod(diff, ciclo_total)
    if dia_no_ciclo >= dias_trabalho:
        return None  # ninguém dessa fila plantona hoje -- dia de folga do ciclo
    pessoa = pessoas[numero_ciclo % len(pessoas)]
    return pessoa


def computar_dia_generico(dados, data, pos_fds_por_turno):
    """Calcula o dia de um posto genérico (modelo 'grupo' ou 'individual').

    pos_fds_por_turno: {turno_id: 1|2} -- só usado por turnos modo_fds="unico".
    """
    data_iso = data.isoformat()
    ancora = datetime.date.fromisoformat(dados["ancora"])
    dow = _dow(data)
    fim_de_semana = dow in (0, 6)
    modelo = dados.get("modelo_rotacao", "grupo")

    resultado = {}
    for turno in dados["turnos"]:
        turno_id = turno["id"]
        n_pos = turno["n_posicoes"]
        modo_fds = turno.get("modo_fds", "alterna")
        pos_fds = pos_fds_por_turno.get(turno_id, 1)

        if modelo == "grupo":
            equipe = equipe_do_dia(data, ancora)
            bases = [encontrar_pessoa(dados, equipe, turno_id, p) for p in range(1, n_pos + 1)]
        else:  # "individual"
            pessoas = [p["nome"] for p in dados["equipe"] if p["turno"] == turno_id]
            ciclo = dados["dias_trabalho"] + dados["dias_folga"]
            nome = _pessoa_individual(pessoas, ciclo, dados["dias_trabalho"], data, ancora)
            bases = [nome or ""] * n_pos

        valores = [aplicar_substituicoes(dados, b, data_iso) if b else "" for b in bases]

        if fim_de_semana and modelo == "grupo":
            if modo_fds == "unico":
                # so uma posicao (a escolhida por pos_fds) cobre sabado E
                # domingo, e ela sempre aparece no slot 0 -- padrao do
                # turno 1022 do CENTRAL, confirmado contra a planilha validada.
                escolhida = pos_fds - 1
                valores[0], bases[0] = valores[escolhida], bases[escolhida]
                for i in range(1, n_pos):
                    valores[i] = ""
                    bases[i] = ""
            elif modo_fds == "parceiro_ativo":
                # dados["folgas_legais"][mes_iso][pessoa] = [dia1, dia2] --
                # as duas datas de folga daquela pessoa no mes. No dia de
                # folga de alguem, o PARCEIRO FIXO dela (mesma dupla dos
                # dias de semana) cobre sozinho o fim de semana inteiro --
                # padrao real da NORTE (Lei 11.901/2009), validado 16/16
                # contra as escalas reais de junho+julho/2026.
                pessoa_de_folga = _pessoa_de_folga_legal(dados, data)
                parceiros = _mapa_parceiros(dados)
                nome = parceiros.get(pessoa_de_folga) if pessoa_de_folga else None
                # so aparece no turno onde essa dupla esta cadastrada --
                # os demais turnos parceiro_ativo ficam vazios nesse dia
                # (celula unica fundida sabado+domingo na escala real).
                pertence_a_este_turno = any(
                    p["nome"] == nome and p["turno"] == turno_id for p in dados["equipe"]
                )
                if nome and pertence_a_este_turno:
                    valores[0] = aplicar_substituicoes(dados, nome, data_iso)
                    bases[0] = nome
                else:
                    valores[0] = ""
                    bases[0] = ""
                for i in range(1, n_pos):
                    valores[i] = ""
                    bases[i] = ""
            else:  # "alterna"
                # cada posicao so aparece no dia que lhe cabe (pos indice
                # par -> sabado, impar -> domingo) -- generaliza o padrao
                # do turno 0719 do CENTRAL (pos1 some no domingo, pos2 some
                # no sabado) para N posicoes.
                for i in range(n_pos):
                    pertence_ao_sabado = (i % 2 == 0)
                    if pertence_ao_sabado != (dow == 6):
                        valores[i] = ""
                        bases[i] = ""

        resultado[turno_id] = {
            "valores": valores,
            "bases": bases,
            "pos_fds": pos_fds if (fim_de_semana and modo_fds == "unico" and modelo == "grupo") else None,
        }
    return resultado


def computar_mes_generico(dados, ano, mes, overrides_fds=None):
    """Generaliza regra_rodizio.computar_mes para N turnos e para o modelo
    'individual'. overrides_fds: {turno_id: {dia: pos_fds}}."""
    overrides_fds = overrides_fds or {}
    ancora = datetime.date.fromisoformat(dados["ancora"])
    total_dias = calendar.monthrange(ano, mes)[1]

    padrao_por_turno = {
        turno["id"]: posicoes_fim_de_semana(ano, mes, ancora)
        for turno in dados["turnos"]
    }

    resultado = []
    for d in range(1, total_dias + 1):
        data = datetime.date(ano, mes, d)
        pos_fds_por_turno = {}
        for turno in dados["turnos"]:
            turno_id = turno["id"]
            override_turno = overrides_fds.get(turno_id, {})
            pos_fds_por_turno[turno_id] = override_turno.get(
                str(d), padrao_por_turno[turno_id].get(d, 1)
            )
        info = computar_dia_generico(dados, data, pos_fds_por_turno)
        resultado.append({"dia": d, "data": data.isoformat(), "turnos": info})
    return resultado


def _dias_trabalhados_do_ano_generico(dados, ano):
    """Equivalente a regra_rodizio._dias_trabalhados_do_ano, mas sem
    assumir slots fixos -- varre TODOS os turnos/posições que o posto tem,
    quaisquer que sejam."""
    por_pessoa = {p["nome"]: [] for p in dados["equipe"]}
    for mes in range(1, 13):
        overrides = dados.get("overrides_fds", {})
        for d in computar_mes_generico(dados, ano, mes, overrides):
            data = datetime.date.fromisoformat(d["data"])
            for turno in dados["turnos"]:
                for nome in d["turnos"][turno["id"]]["valores"]:
                    if nome:
                        por_pessoa.setdefault(nome, []).append(data)
    return por_pessoa


def folgoes_automaticos_ano_generico(dados, nome, ano, a_partir_de=None):
    """Equivalente a regra_rodizio.folgoes_automaticos_ano, genérico pra
    qualquer posto: detecta folgão sempre que o intervalo entre dois dias
    trabalhados seguidos é maior que 2 (o normal do rodízio 12x36)."""
    datas = sorted(_dias_trabalhados_do_ano_generico(dados, ano).get(nome, []))
    folgoes = [a + datetime.timedelta(days=1) for a, b in zip(datas, datas[1:]) if (b - a).days > 2]
    if a_partir_de is not None:
        folgoes = [f for f in folgoes if f >= a_partir_de]
    return len(folgoes)


def dias_trabalhados_mes_generico(dados, ano, mes, overrides_fds=None):
    """Equivalente a regra_rodizio.dias_trabalhados_mes, genérico pra
    qualquer posto: conta quantos dias no mês cada pessoa aparece escalada
    em qualquer turno/posição."""
    dias = computar_mes_generico(dados, ano, mes, overrides_fds)
    contagem = {p["nome"]: 0 for p in dados["equipe"]}
    for d in dias:
        for turno in dados["turnos"]:
            for nome in d["turnos"][turno["id"]]["valores"]:
                if nome:
                    contagem[nome] = contagem.get(nome, 0) + 1
    return contagem


def novo_posto(nome, empresa, ancora_iso, turnos, modelo_rotacao="grupo",
                dias_trabalho=None, dias_folga=None, equipe=None, observacoes=""):
    """Cria a estrutura de dados de um posto novo, isolada de qualquer
    outro posto -- cada posto é um dict independente, sem estado
    compartilhado (nenhuma lista ou referência é reaproveitada de outro
    posto).

    turnos: [{"id": "0719", "n_posicoes": 2, "modo_fds": "alterna"|"unico"}, ...]
    modelo_rotacao: "grupo" (CENTRAL) ou "individual" (NORTE)
    dias_trabalho/dias_folga: obrigatórios só no modelo "individual"
    equipe: [{"nome", "equipe", "turno", "pos"}, ...] (modelo "grupo")
         ou [{"nome", "turno"}, ...] em ordem de fila (modelo "individual")
    """
    posto = {
        "posto_nome": nome,
        "empresa": empresa,
        "ancora": ancora_iso,
        "modelo_rotacao": modelo_rotacao,
        "turnos": [dict(t) for t in turnos],
        "equipe": [dict(p) for p in (equipe or [])],
        "folgas": [],
        "ferias": [],
        "overrides_fds": {},
        "observacoes": observacoes,
    }
    if modelo_rotacao == "individual":
        posto["dias_trabalho"] = dias_trabalho
        posto["dias_folga"] = dias_folga
    return posto
