# -*- coding: utf-8 -*-
"""Motor de cálculo do rodízio BCI — fonte única de verdade, usada pelo site
e pelo gerador de Word. Meses sempre 1-12 (janeiro=1)."""
import calendar
import datetime
import json
import uuid

WEEKDAY_NAMES = ["Domingo", "Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"]
MES_NOMES = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho",
             "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
MES_NOMES_MIN = ["", "janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
                 "agosto", "setembro", "outubro", "novembro", "dezembro"]


def carregar_dados(caminho):
    with open(caminho, encoding="utf-8") as f:
        dados = json.load(f)
    precisa_salvar = False
    for lista in (dados.get("ferias", []), dados.get("folgas", [])):
        for item in lista:
            if not item.get("id"):
                item["id"] = uuid.uuid4().hex[:8]
                precisa_salvar = True
    if precisa_salvar:
        salvar_dados(caminho, dados)
    return dados


def salvar_dados(caminho, dados):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def _dow(data):
    """Converte para Domingo=0..Sábado=6 (Python's weekday() é Segunda=0..Domingo=6)."""
    return (data.weekday() + 1) % 7


def nome_dia_semana(dow):
    if dow == 0:
        return "domingo"
    if dow == 6:
        return "sábado"
    return f"{WEEKDAY_NAMES[dow].lower()}-feira"


def formatar_data_extenso(data):
    return f"{nome_dia_semana(_dow(data))}, {data.day:02d} de {MES_NOMES_MIN[data.month]} de {data.year}"


def encontrar_pessoa(dados, equipe, turno, pos):
    for p in dados["equipe"]:
        if p["equipe"] == equipe and p["turno"] == turno and p["pos"] == pos:
            return p["nome"]
    raise ValueError(f"Ninguém cadastrado para {equipe}/{turno}/pos{pos}")


def aplicar_substituicoes(dados, nome, data_iso):
    for f in dados["ferias"]:
        if f["pessoa"] == nome and f["inicio"] <= data_iso <= f["fim"]:
            return f["substituto"]
    for g in dados["folgas"]:
        if g["pessoa"] == nome and g["data"] == data_iso:
            return g["substituto"]
    return nome


def equipe_do_dia(data, ancora):
    diff_dias = (data - ancora).days
    return "Bravo" if diff_dias % 2 == 0 else "Alfa"


def _indice_fds(data, ancora):
    """Índice contínuo (par=sábado, ímpar=domingo) de um dia de fim de semana,
    contado em dias corridos desde a âncora -- nunca reconta por mês, então a
    paridade sábado/domingo nunca se perde na virada do mês ou do ano."""
    return (data - ancora).days // 7 * 2 + (0 if _dow(data) == 6 else 1)


def posicoes_fim_de_semana(ano, mes, ancora=None):
    """Alterna 1/2 pra decidir qual posição do turno 10h-22h cobre cada sábado/domingo,
    quando não há override manual em dados['overrides_fds']. Usa dias corridos desde
    a âncora (nunca reseta a cada mês), pra preservar o ciclo contínuo."""
    if ancora is None:
        # sem ancora (uso avulso/testes): alterna 1,2,1,2... a partir do
        # primeiro dia de fim de semana do proprio mes.
        ancora = datetime.date(ano, mes, 1)

    resultado = {}
    total_dias = calendar.monthrange(ano, mes)[1]
    for d in range(1, total_dias + 1):
        data = datetime.date(ano, mes, d)
        dow = _dow(data)
        if dow == 0 or dow == 6:
            resultado[d] = 2 if _indice_fds(data, ancora) % 2 == 0 else 1
    return resultado


_TURNOS_CENTRAL = [
    {"id": "0719", "n_posicoes": 2, "modo_fds": "alterna"},
    {"id": "1022", "n_posicoes": 2, "modo_fds": "unico"},
]


def _dados_central_para_motor(dados):
    """dados.json do CENTRAL não tem a chave 'turnos' (formato antigo,
    anterior ao Motor Universal) -- injeta a estrutura fixa de 2 turnos
    (0719 alterna, 1022 unico) que sempre foi implícita nesse posto, sem
    alterar o dict original."""
    dados_motor = dict(dados)
    dados_motor["turnos"] = _TURNOS_CENTRAL
    dados_motor["modelo_rotacao"] = "grupo"
    return dados_motor


def computar_dia(dados, data, pos_fds):
    """Wrapper fino sobre motor.computar_dia_generico -- mantém o shape de
    saída antigo (pos_0719_1..pos_1022_2, base_*, pos_fds) pra não quebrar
    os templates/chamadores existentes. Nenhum cálculo daqui pra baixo:
    scripts/motor.py é a única fonte da matemática do rodízio."""
    import motor

    dados_motor = _dados_central_para_motor(dados)
    resultado = motor.computar_dia_generico(dados_motor, data, {"0719": pos_fds, "1022": pos_fds})
    t0719, t1022 = resultado["0719"], resultado["1022"]
    dow = _dow(data)

    return {
        "pos_0719_1": t0719["valores"][0], "pos_0719_2": t0719["valores"][1],
        "pos_1022_1": t1022["valores"][0], "pos_1022_2": t1022["valores"][1],
        # nome da escala fixa (antes de aplicar_substituicoes) -- usado como
        # chave estavel pra editar o dia mesmo quando ja tem um substituto
        # exibido (ex: reeditar um dia dentro de uma ferias em andamento)
        "base_0719_1": t0719["bases"][0], "base_0719_2": t0719["bases"][1],
        "base_1022_1": t1022["bases"][0], "base_1022_2": t1022["bases"][1],
        # qual posicao (1 ou 2) do cadastro esta cobrindo o 10h-22h neste fds
        # -- None em dia de semana, onde as duas posicoes trabalham juntas
        "pos_fds": pos_fds if dow in (0, 6) else None,
    }


def computar_mes(dados, ano, mes, overrides_fds=None):
    """Wrapper fino sobre motor.computar_mes_generico -- mesmo shape de
    saída antigo (lista de dicts com pos_0719_1 etc.), pra manter
    compatibilidade com mes.html e as rotas /api/*."""
    import motor

    overrides_fds = overrides_fds or {}
    dados_motor = _dados_central_para_motor(dados)
    overrides_motor = {"0719": overrides_fds, "1022": overrides_fds}
    dias_motor = motor.computar_mes_generico(dados_motor, ano, mes, overrides_motor)

    resultado = []
    for d in dias_motor:
        t0719, t1022 = d["turnos"]["0719"], d["turnos"]["1022"]
        resultado.append({
            "dia": d["dia"], "data": d["data"],
            "pos_0719_1": t0719["valores"][0], "pos_0719_2": t0719["valores"][1],
            "pos_1022_1": t1022["valores"][0], "pos_1022_2": t1022["valores"][1],
            "base_0719_1": t0719["bases"][0], "base_0719_2": t0719["bases"][1],
            "base_1022_1": t1022["bases"][0], "base_1022_2": t1022["bases"][1],
            "pos_fds": t1022["pos_fds"],
        })
    return resultado


def agrupar_em_semanas(ano, mes, dias_computados):
    primeiro_dia = datetime.date(ano, mes, 1)
    ultimo_dia = datetime.date(ano, mes, calendar.monthrange(ano, mes)[1])
    primeiro_domingo = primeiro_dia - datetime.timedelta(days=_dow(primeiro_dia))

    n_semanas = 1
    while primeiro_domingo + datetime.timedelta(days=7 * n_semanas) <= ultimo_dia:
        n_semanas += 1

    por_data = {d["data"]: d for d in dias_computados}
    semanas = []
    for semana in range(n_semanas):
        linha = []
        for col in range(7):
            data_cursor = primeiro_domingo + datetime.timedelta(days=7 * semana + col)
            if primeiro_dia <= data_cursor <= ultimo_dia:
                linha.append({"numero": data_cursor.day, "info": por_data[data_cursor.isoformat()]})
            else:
                linha.append(None)
        semanas.append(linha)
    return semanas


def calcular_data_fim_ferias(inicio_iso, duracao):
    inicio = datetime.date.fromisoformat(inicio_iso)
    if duracao == "20":
        fim = inicio + datetime.timedelta(days=19)
    else:  # "mes"
        mes_seguinte = inicio.month + 1
        ano_seguinte = inicio.year
        if mes_seguinte > 12:
            mes_seguinte = 1
            ano_seguinte += 1
        ultimo_dia_mes_seguinte = calendar.monthrange(ano_seguinte, mes_seguinte)[1]
        dia = min(inicio.day, ultimo_dia_mes_seguinte)
        fim = datetime.date(ano_seguinte, mes_seguinte, dia) - datetime.timedelta(days=1)
    return fim.isoformat()


def folgas_restantes(dados, nome, hoje):
    hoje_iso = hoje.isoformat()
    fim_ano_iso = f"{hoje.year}-12-31"
    ja_lancados = sum(
        1 for f in dados["folgas"]
        if f["pessoa"] == nome and hoje_iso <= f["data"] <= fim_ano_iso
    )
    meses_restantes = 12 - hoje.month + 1
    return max(0, meses_restantes - ja_lancados)


def listar_eventos(dados):
    eventos = []
    for f in dados["folgas"]:
        eventos.append({"id": f["id"], "tipo": "folga", "data": f["data"], "texto": f"{f['pessoa']} folgão",
                         "badge_txt": f"{f['substituto']} cobre", "badge_cls": "folga"})
    for f in dados["ferias"]:
        eventos.append({"id": f["id"], "tipo": "ferias", "data": f["inicio"], "texto": f"{f['pessoa']} inicia férias",
                         "badge_txt": f"{f['substituto']} cobre", "badge_cls": "ferias"})
        volta = datetime.date.fromisoformat(f["fim"]) + datetime.timedelta(days=1)
        eventos.append({"id": "", "tipo": "", "data": volta.isoformat(), "texto": f"{f['pessoa']} volta de férias",
                         "badge_txt": "", "badge_cls": ""})
    eventos.sort(key=lambda e: e["data"])
    return eventos


def folgoes_automaticos_ano(dados, nome, ano, a_partir_de=None):
    """Wrapper fino sobre motor.folgoes_automaticos_ano_generico -- injeta
    a estrutura fixa de turnos do CENTRAL, mesma matemática usada por
    qualquer outro posto."""
    import motor

    return motor.folgoes_automaticos_ano_generico(_dados_central_para_motor(dados), nome, ano, a_partir_de)


def dias_trabalhados_mes(dados, ano, mes, overrides_fds=None):
    """Wrapper fino sobre motor.dias_trabalhados_mes_generico -- injeta a
    estrutura fixa de turnos do CENTRAL, mesma matemática usada por qualquer
    outro posto. overrides_fds aqui é {dia: pos_fds} (formato antigo,
    por mês); o motor genérico espera {turno_id: {dia: pos_fds}}."""
    import motor

    overrides_fds = overrides_fds or {}
    overrides_motor = {"0719": overrides_fds, "1022": overrides_fds}
    return motor.dias_trabalhados_mes_generico(_dados_central_para_motor(dados), ano, mes, overrides_motor)


def status_mes(dados, ano, mes, hoje):
    inicio_mes = datetime.date(ano, mes, 1)
    fim_mes = datetime.date(ano, mes, calendar.monthrange(ano, mes)[1])
    is_passado = (ano, mes) < (hoje.year, hoje.month)
    folgas_no_mes = sum(
        1 for f in dados["folgas"]
        if inicio_mes <= datetime.date.fromisoformat(f["data"]) <= fim_mes
    )
    ferias_ativa = next(
        (f for f in dados["ferias"]
         if datetime.date.fromisoformat(f["inicio"]) <= fim_mes
         and datetime.date.fromisoformat(f["fim"]) >= inicio_mes),
        None,
    )
    if is_passado:
        return {"flag": False, "texto": "sem eventos"}
    if ferias_ativa:
        comecou_antes = datetime.date.fromisoformat(ferias_ativa["inicio"]) < inicio_mes
        return {"flag": True, "texto": "férias (cont.)" if comecou_antes else "em férias"}
    if folgas_no_mes > 0:
        plural = "folgão" if folgas_no_mes == 1 else "folgões"
        return {"flag": True, "texto": f"{folgas_no_mes} {plural}"}
    return {"flag": False, "texto": "sem eventos"}


def ferias_ativas_no_mes(dados, ano, mes):
    """Retorna as férias cujo intervalo [inicio, fim] cruza o mês informado,
    já com o nome completo (se cadastrado) e a duração em dias -- usado pelo
    bloco 'COBERTURA DE FÉRIAS / FÉRIAS' no site, no PDF impresso e no Word."""
    inicio_mes = datetime.date(ano, mes, 1)
    fim_mes = datetime.date(ano, mes, calendar.monthrange(ano, mes)[1])
    nomes_completos = {p["nome"]: p.get("nome_completo", "") for p in dados["equipe"]}
    resultado = []
    for f in dados["ferias"]:
        f_inicio = datetime.date.fromisoformat(f["inicio"])
        f_fim = datetime.date.fromisoformat(f["fim"])
        if f_inicio <= fim_mes and f_fim >= inicio_mes:
            duracao_dias = (f_fim - f_inicio).days + 1
            resultado.append({
                "id": f["id"],
                "pessoa_completa": nomes_completos.get(f["pessoa"]) or f["pessoa"],
                "substituto": f["substituto"],
                "inicio": f["inicio"],
                "fim": f["fim"],
                "duracao_dias": duracao_dias,
            })
    return resultado
