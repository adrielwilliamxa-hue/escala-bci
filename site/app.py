# -*- coding: utf-8 -*-
import os
import shutil
import socket
import sys
import datetime

from flask import Flask, render_template, request, jsonify, send_file

FROZEN = getattr(sys, "frozen", False)

if FROZEN:
    # Rodando como "Escala BCI.exe" (PyInstaller): templates/static vem do
    # bundle extraido; dados.json e "Word gerados" moram ao lado do exe,
    # pra sobreviverem entre execucoes e irem junto quando copiar o arquivo.
    BUNDLE_DIR = sys._MEIPASS
    APP_DIR = os.path.dirname(sys.executable)
    DADOS_PATH = os.path.join(APP_DIR, "dados.json")
    app = Flask(
        __name__,
        template_folder=os.path.join(BUNDLE_DIR, "templates"),
        static_folder=os.path.join(BUNDLE_DIR, "static"),
    )
    if not os.path.exists(DADOS_PATH):
        shutil.copy(os.path.join(BUNDLE_DIR, "seed", "dados.json"), DADOS_PATH)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_DIR = os.path.dirname(BASE_DIR)
    sys.path.insert(0, os.path.join(PROJECT_DIR, "scripts"))
    DADOS_PATH = os.path.join(BASE_DIR, "dados.json")
    app = Flask(__name__)
    if not os.path.exists(DADOS_PATH):
        # primeira execucao depois de clonar: comeca com os dados ficticios
        shutil.copy(os.path.join(PROJECT_DIR, "dados.example.json"), DADOS_PATH)

import regra_rodizio as rr  # noqa: E402
import gerar_word  # noqa: E402
import motor  # noqa: E402
import postos as postos_db  # noqa: E402
import gerar_xlsx_posto  # noqa: E402
import storage_lock  # noqa: E402

if FROZEN:
    WORD_OUT_DIR = os.path.join(APP_DIR, "Word gerados")
    postos_db.configurar_dir(os.path.join(APP_DIR, "postos"))
else:
    WORD_OUT_DIR = os.path.join(PROJECT_DIR, "Word gerados")

MESES_SIDEBAR = rr.MES_NOMES[1:]
MESES_GRID = rr.MES_NOMES[1:]


def com_lock_dados(func):
    """Decorator pras rotas /api/* -- serializa ler+modificar+gravar do
    dados.json, evitando que duas requisições concorrentes se pisem."""
    import functools

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with storage_lock.lock_para(DADOS_PATH):
            return func(*args, **kwargs)
    return wrapper


def com_lock_posto(func):
    """Decorator pras rotas de escrita de posto -- serializa ler+modificar
    +gravar do postos/<slug>.json daquele posto especificamente. Flask
    injeta parâmetros de rota (<slug>) como kwargs, então pega dos dois
    lugares possíveis."""
    import functools

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        slug = kwargs.get("slug") or (args[0] if args else None)
        caminho = os.path.join(postos_db.POSTOS_DIR, f"{slug}.json")
        with storage_lock.lock_para(caminho):
            return func(*args, **kwargs)
    return wrapper


def _hoje():
    return datetime.date.today()


def _formatar_evento_quando(data_iso):
    ano, mes, dia = data_iso.split("-")
    return f"{dia} {rr.MES_NOMES_MIN[int(mes)][:3]}"


ANOS_DISPONIVEIS = [2026, 2027]


@app.route("/")
def dashboard():
    dados = rr.carregar_dados(DADOS_PATH)
    hoje = _hoje()
    hoje_iso = hoje.isoformat()
    ano = request.args.get("ano", type=int, default=hoje.year)
    if ano not in ANOS_DISPONIVEIS:
        ano = hoje.year

    equipe_bravo = [p for p in dados["equipe"] if p["equipe"] == "Bravo"]
    equipe_alfa = [p for p in dados["equipe"] if p["equipe"] == "Alfa"]
    inicio_contagem = hoje if ano == hoje.year else datetime.date(ano, 1, 1)
    folgas_por_pessoa = [
        {"nome": p["nome"], "registradas": rr.folgoes_automaticos_ano(dados, p["nome"], ano, inicio_contagem)}
        for p in dados["equipe"]
    ]
    dias_trabalhados_por_mes = {
        nome: rr.dias_trabalhados_mes(
            dados, ano, rr.MES_NOMES.index(nome),
            dados.get("overrides_fds", {}).get(nome, {}),
        )
        for nome in MESES_GRID
    }
    dias_trabalhados_por_pessoa = [
        {
            "nome": p["nome"],
            "por_mes": [dias_trabalhados_por_mes[nome].get(p["nome"], 0) for nome in MESES_GRID],
        }
        for p in dados["equipe"]
    ]
    meses_grid = [
        (nome, rr.status_mes(dados, ano, rr.MES_NOMES.index(nome), hoje))
        for nome in MESES_GRID
    ]
    eventos = [e for e in rr.listar_eventos(dados) if e["data"] >= hoje_iso]
    for e in eventos:
        e["quando"] = _formatar_evento_quando(e["data"])

    return render_template(
        "dashboard.html",
        active="dashboard",
        ano=ano,
        anos_disponiveis=ANOS_DISPONIVEIS,
        hoje_texto=rr.formatar_data_extenso(hoje),
        meses_sidebar=MESES_SIDEBAR,
        mes_atual=rr.MES_NOMES[hoje.month] if ano == hoje.year else None,
        equipe_bravo=equipe_bravo,
        equipe_alfa=equipe_alfa,
        certificados=dados["certificados"],
        total_brigadistas=len(dados["equipe"]),
        ferias_ativas=sum(
            1 for f in dados["ferias"]
            if f["inicio"] <= hoje_iso <= f["fim"]
        ),
        folgas_por_pessoa=folgas_por_pessoa,
        meses_grid=meses_grid,
        meses_nomes=MESES_GRID,
        dias_trabalhados_por_pessoa=dias_trabalhados_por_pessoa,
        eventos=eventos,
    )


@app.route("/mes/<nome>")
def mes(nome):
    if nome not in rr.MES_NOMES:
        return "Mês não encontrado", 404
    dados = rr.carregar_dados(DADOS_PATH)
    hoje = _hoje()
    ano = request.args.get("ano", type=int, default=hoje.year)
    if ano not in ANOS_DISPONIVEIS:
        ano = hoje.year
    mes_idx = rr.MES_NOMES.index(nome)
    overrides = dados.get("overrides_fds", {}).get(nome, {})
    dias = rr.computar_mes(dados, ano, mes_idx, overrides)
    ancora = datetime.date.fromisoformat(dados["ancora"])
    for d in dias:
        d["equipe"] = rr.equipe_do_dia(datetime.date.fromisoformat(d["data"]), ancora)
    semanas = rr.agrupar_em_semanas(ano, mes_idx, dias)
    ferias_ativas = rr.ferias_ativas_no_mes(dados, ano, mes_idx)

    folga_dias = {f["data"] for f in dados["folgas"]}
    prefixo_mes = f"{ano}-{mes_idx:02d}"
    eventos_mes = [e for e in rr.listar_eventos(dados) if e["data"].startswith(prefixo_mes)]
    for e in eventos_mes:
        e["quando"] = _formatar_evento_quando(e["data"])

    return render_template(
        "mes.html",
        active=nome,
        ano=ano,
        anos_disponiveis=ANOS_DISPONIVEIS,
        hoje_texto=rr.formatar_data_extenso(hoje),
        hoje_iso=hoje.isoformat(),
        meses_sidebar=MESES_SIDEBAR,
        nome_mes=nome,
        semanas=semanas,
        folga_dias=folga_dias,
        eventos_mes=eventos_mes,
        ferias_ativas=ferias_ativas,
        equipe=dados["equipe"],
        certificados=dados["certificados"],
    )


@app.route("/api/dia", methods=["POST"])
@com_lock_dados
def api_dia():
    body = request.get_json()
    dados = rr.carregar_dados(DADOS_PATH)
    dados.setdefault("folgas", []).append({
        "pessoa": body["pessoa"], "data": body["data"], "substituto": body["substituto"],
    })
    rr.salvar_dados(DADOS_PATH, dados)
    return jsonify({"ok": True})


@app.route("/api/ferias", methods=["POST"])
@com_lock_dados
def api_ferias():
    body = request.get_json()
    inicio_iso = datetime.datetime.strptime(body["inicio"], "%d/%m/%Y").date().isoformat()
    fim_iso = rr.calcular_data_fim_ferias(inicio_iso, body["duracao"])
    dados = rr.carregar_dados(DADOS_PATH)
    dados.setdefault("ferias", []).append({
        "pessoa": body["pessoa"], "inicio": inicio_iso, "fim": fim_iso, "substituto": body["substituto"],
    })
    rr.salvar_dados(DADOS_PATH, dados)
    return jsonify({"ok": True})


@app.route("/api/ferias/editar-substituto", methods=["POST"])
@com_lock_dados
def api_ferias_editar_substituto():
    body = request.get_json()
    dados = rr.carregar_dados(DADOS_PATH)
    for f in dados["ferias"]:
        if f["id"] == body["id"]:
            f["substituto"] = body["substituto"]
    rr.salvar_dados(DADOS_PATH, dados)
    return jsonify({"ok": True})


@app.route("/api/fds", methods=["POST"])
@com_lock_dados
def api_fds():
    body = request.get_json()
    dados = rr.carregar_dados(DADOS_PATH)
    dados.setdefault("overrides_fds", {}).setdefault(body["nome_mes"], {})[str(body["dia"])] = int(body["pos_fds"])
    rr.salvar_dados(DADOS_PATH, dados)
    return jsonify({"ok": True})


@app.route("/api/renomear", methods=["POST"])
@com_lock_dados
def api_renomear():
    body = request.get_json()
    dados = rr.carregar_dados(DADOS_PATH)
    for p in dados["equipe"]:
        if p["nome"] == body["nome_antigo"]:
            p["nome"] = body["nome_novo"]
            nome_completo = body.get("nome_completo", "").strip()
            if nome_completo:
                p["nome_completo"] = nome_completo
    rr.salvar_dados(DADOS_PATH, dados)
    return jsonify({"ok": True})


@app.route("/api/certificados", methods=["POST"])
@com_lock_dados
def api_certificados():
    body = request.get_json()
    dados = rr.carregar_dados(DADOS_PATH)
    dados["certificados"] = body["certificados"]
    rr.salvar_dados(DADOS_PATH, dados)
    return jsonify({"ok": True})


@app.route("/api/ferias/remover", methods=["POST"])
@com_lock_dados
def api_ferias_remover():
    body = request.get_json()
    dados = rr.carregar_dados(DADOS_PATH)
    dados["ferias"] = [f for f in dados["ferias"] if f["id"] != body["id"]]
    rr.salvar_dados(DADOS_PATH, dados)
    return jsonify({"ok": True})


@app.route("/api/folga/remover", methods=["POST"])
@com_lock_dados
def api_folga_remover():
    body = request.get_json()
    dados = rr.carregar_dados(DADOS_PATH)
    dados["folgas"] = [f for f in dados["folgas"] if f["id"] != body["id"]]
    rr.salvar_dados(DADOS_PATH, dados)
    return jsonify({"ok": True})


@app.route("/gerar-word/<nome>")
def gerar_word_rota(nome):
    if nome not in rr.MES_NOMES:
        return "Mês não encontrado", 404
    dados = rr.carregar_dados(DADOS_PATH)
    hoje = _hoje()
    ano = request.args.get("ano", type=int, default=hoje.year)
    if ano not in ANOS_DISPONIVEIS:
        ano = hoje.year
    mes_idx = rr.MES_NOMES.index(nome)
    overrides = dados.get("overrides_fds", {}).get(nome, {})
    out_path = gerar_word.gerar_docx_mes_de_dados(
        dados, ano, mes_idx, doc_num=mes_idx, local="POSTO CENTRAL",
        emissao=f"Brasília, {rr.formatar_data_extenso(hoje)}.", overrides_fds=overrides,
    )
    return send_file(out_path, as_attachment=True)


MODELOS_FDS_VALIDOS = ("alterna", "unico", "parceiro_ativo")


def _posto_form_para_dados(form, slug_existente=None):
    """Converte o formulario de cadastro/edicao de posto em um dict no
    formato que scripts/motor.py consome -- nenhum campo e travado no
    codigo, tudo vem do formulario."""
    turnos = []
    for t in form.get("turnos", []):
        turnos.append({
            "id": t["id"].strip(),
            "n_posicoes": int(t["n_posicoes"]),
            "modo_fds": t["modo_fds"] if t["modo_fds"] in MODELOS_FDS_VALIDOS else "alterna",
        })
    dados = {
        "posto_nome": form["posto_nome"].strip(),
        "empresa": form.get("empresa", "").strip(),
        "local": form.get("local", "").strip(),
        "ancora": form["ancora"],
        "modelo_rotacao": form.get("modelo_rotacao", "grupo"),
        "turnos": turnos,
        "equipe": form.get("equipe", []),
        "folgas": form.get("folgas", []),
        "ferias": form.get("ferias", []),
        "overrides_fds": form.get("overrides_fds", {}),
        "folgas_legais": form.get("folgas_legais", {}),
        "certificados": form.get("certificados", []),
        "observacoes": form.get("observacoes", ""),
    }
    if dados["modelo_rotacao"] == "individual":
        dados["dias_trabalho"] = int(form["dias_trabalho"])
        dados["dias_folga"] = int(form["dias_folga"])
    return dados


def _validar_posto(dados):
    """Confere que o cadastro tem gente suficiente pra cobrir toda posicao
    de todo turno antes de salvar -- sem isso, o motor levanta ValueError
    só na hora de gerar a escala, tarde demais pra dar um retorno útil."""
    if dados["modelo_rotacao"] == "grupo":
        equipes = sorted({p["equipe"] for p in dados["equipe"] if p.get("equipe")})
        if len(equipes) != 2:
            return f"Modelo 'grupo' precisa de exatamente 2 equipes cadastradas (encontradas: {equipes or 'nenhuma'})."
        for turno in dados["turnos"]:
            for pos in range(1, turno["n_posicoes"] + 1):
                cadastrados = [p for p in dados["equipe"]
                                if p.get("turno") == turno["id"] and p.get("pos") == pos]
                nomes_equipes = {p["equipe"] for p in cadastrados}
                faltando = set(equipes) - nomes_equipes
                if faltando:
                    return (f"Turno '{turno['id']}' posição {pos}: falta brigadista da equipe "
                             f"{', '.join(sorted(faltando))}.")
    else:  # individual
        for turno in dados["turnos"]:
            pessoas_turno = [p for p in dados["equipe"] if p.get("turno") == turno["id"]]
            if not pessoas_turno:
                return f"Turno '{turno['id']}': nenhum brigadista cadastrado nesse turno."
    return None


@app.route("/postos")
def postos_lista():
    lista = postos_db.listar_postos()
    return render_template("postos_lista.html", active="postos", postos=lista,
                            anos_disponiveis=ANOS_DISPONIVEIS, ano=_hoje().year,
                            hoje_texto=rr.formatar_data_extenso(_hoje()), meses_sidebar=MESES_SIDEBAR)


@app.route("/postos/novo", methods=["GET", "POST"])
def posto_novo():
    if request.method == "POST":
        body = request.get_json()
        dados = _posto_form_para_dados(body)
        erro = _validar_posto(dados)
        if erro:
            return jsonify({"ok": False, "erro": erro}), 400
        # posto ainda não existe -- lock no arquivo final que o slug vai
        # gerar, calculado do mesmo jeito que postos_db.salvar_posto faz.
        caminho_provavel = os.path.join(postos_db.POSTOS_DIR, postos_db._slugify(dados["posto_nome"]) + ".json")
        with storage_lock.lock_para(caminho_provavel):
            slug = postos_db.salvar_posto(dados)
        return jsonify({"ok": True, "slug": slug})
    return render_template("posto_editar.html", active="postos", posto=None,
                            anos_disponiveis=ANOS_DISPONIVEIS, ano=_hoje().year,
                            hoje_texto=rr.formatar_data_extenso(_hoje()), meses_sidebar=MESES_SIDEBAR)


@app.route("/postos/<slug>/editar", methods=["GET", "POST"])
@com_lock_posto
def posto_editar(slug):
    if not postos_db.existe_posto(slug):
        return "Posto não encontrado", 404
    if request.method == "POST":
        body = request.get_json()
        dados = _posto_form_para_dados(body)
        erro = _validar_posto(dados)
        if erro:
            return jsonify({"ok": False, "erro": erro}), 400
        postos_db.salvar_posto(dados, slug=slug)
        return jsonify({"ok": True, "slug": slug})
    posto = postos_db.carregar_posto(slug)
    return render_template("posto_editar.html", active="postos", posto=posto,
                            anos_disponiveis=ANOS_DISPONIVEIS, ano=_hoje().year,
                            hoje_texto=rr.formatar_data_extenso(_hoje()), meses_sidebar=MESES_SIDEBAR)


@app.route("/postos/<slug>/excluir", methods=["POST"])
@com_lock_posto
def posto_excluir(slug):
    postos_db.excluir_posto(slug)
    return jsonify({"ok": True})


def _agrupar_equipe_do_posto(posto):
    """Agrupa a equipe do posto pra exibição no painel: no modelo 'grupo',
    por rótulo de equipe (Alfa/Bravo ou quaisquer 2 nomes cadastrados); no
    modelo 'individual', num único grupo na ordem da fila."""
    if posto["modelo_rotacao"] == "individual":
        return {"Fila de rodízio": posto["equipe"]}
    grupos = {}
    for p in posto["equipe"]:
        grupos.setdefault(p.get("equipe", "Sem equipe"), []).append(p)
    return grupos


def _status_mes_generico(posto, ano, mes, hoje):
    """Equivalente a rr.status_mes -- já é genérico (só usa folgas/férias
    do dict do posto), reaproveitado direto sem duplicar lógica."""
    return rr.status_mes(posto, ano, mes, hoje)


@app.route("/postos/<slug>")
def posto_dashboard(slug):
    if not postos_db.existe_posto(slug):
        return "Posto não encontrado", 404
    posto = postos_db.carregar_posto(slug)
    hoje = _hoje()
    hoje_iso = hoje.isoformat()
    ano = request.args.get("ano", type=int, default=hoje.year)
    if ano not in ANOS_DISPONIVEIS:
        ano = hoje.year

    grupos = _agrupar_equipe_do_posto(posto)
    inicio_contagem = hoje if ano == hoje.year else datetime.date(ano, 1, 1)
    folgas_por_pessoa = [
        {"nome": p["nome"], "registradas": motor.folgoes_automaticos_ano_generico(posto, p["nome"], ano, inicio_contagem)}
        for p in posto["equipe"]
    ]
    dias_trabalhados_por_mes = {
        mes: motor.dias_trabalhados_mes_generico(posto, ano, mes, posto.get("overrides_fds", {}))
        for mes in range(1, 13)
    }
    dias_trabalhados_por_pessoa = [
        {"nome": p["nome"], "por_mes": [dias_trabalhados_por_mes[mes].get(p["nome"], 0) for mes in range(1, 13)]}
        for p in posto["equipe"]
    ]
    meses_grid = [(rr.MES_NOMES[mes], _status_mes_generico(posto, ano, mes, hoje)) for mes in range(1, 13)]
    eventos = [e for e in rr.listar_eventos(posto) if e["data"] >= hoje_iso]
    for e in eventos:
        e["quando"] = _formatar_evento_quando(e["data"])

    return render_template(
        "posto_dashboard.html", active="postos", posto=posto, ano=ano,
        anos_disponiveis=ANOS_DISPONIVEIS, hoje_texto=rr.formatar_data_extenso(hoje),
        meses_sidebar=MESES_SIDEBAR, mes_atual=rr.MES_NOMES[hoje.month] if ano == hoje.year else None,
        grupos=grupos, total_brigadistas=len(posto["equipe"]),
        ferias_ativas=sum(1 for f in posto["ferias"] if f["inicio"] <= hoje_iso <= f["fim"]),
        folgas_por_pessoa=folgas_por_pessoa, meses_grid=meses_grid, meses_nomes=MESES_GRID,
        dias_trabalhados_por_pessoa=dias_trabalhados_por_pessoa, eventos=eventos,
    )


def _rotulo_turno_exibicao(turno_id):
    """'0719' -> '07h–19h'; qualquer outro id de 4 dígitos vira o mesmo
    padrão, ids que não seguem esse formato aparecem como estão."""
    if len(turno_id) == 4 and turno_id.isdigit():
        return f"{turno_id[:2]}h–{turno_id[2:]}h"
    return turno_id


@app.route("/postos/<slug>/mes/<int:ano>/<int:mes>")
def posto_mes(slug, ano, mes):
    if not postos_db.existe_posto(slug):
        return "Posto não encontrado", 404
    posto = postos_db.carregar_posto(slug)
    hoje = _hoje()
    overrides = posto.get("overrides_fds", {})
    dias = motor.computar_mes_generico(posto, ano, mes, overrides)
    semanas = rr.agrupar_em_semanas(ano, mes, dias)
    ferias_ativas = rr.ferias_ativas_no_mes(posto, ano, mes)
    prefixo_mes = f"{ano}-{mes:02d}"
    eventos_mes = [e for e in rr.listar_eventos(posto) if e["data"].startswith(prefixo_mes)]
    for e in eventos_mes:
        e["quando"] = _formatar_evento_quando(e["data"])
    turnos_exibicao = [(t["id"], _rotulo_turno_exibicao(t["id"])) for t in posto["turnos"]]
    return render_template(
        "posto_mes.html", active="postos", posto=posto, ano=ano, mes=mes,
        mes_nome=rr.MES_NOMES[mes], turnos_exibicao=turnos_exibicao, semanas=semanas,
        ferias_ativas=ferias_ativas, eventos_mes=eventos_mes,
        anos_disponiveis=ANOS_DISPONIVEIS, hoje_iso=hoje.isoformat(),
        hoje_texto=rr.formatar_data_extenso(hoje), meses_sidebar=MESES_SIDEBAR,
    )


@app.route("/postos/<slug>/gerar-word/<int:ano>/<int:mes>")
def posto_gerar_word(slug, ano, mes):
    if not postos_db.existe_posto(slug):
        return "Posto não encontrado", 404
    posto = postos_db.carregar_posto(slug)
    hoje = _hoje()
    out_path = gerar_word.gerar_docx_mes_posto(
        posto, ano, mes, doc_num=mes, emissao=f"Brasília, {rr.formatar_data_extenso(hoje)}.",
    )
    return send_file(out_path, as_attachment=True)


@app.route("/postos/<slug>/gerar-xlsx/<int:ano>")
def posto_gerar_xlsx(slug, ano):
    if not postos_db.existe_posto(slug):
        return "Posto não encontrado", 404
    posto = postos_db.carregar_posto(slug)
    out_path = gerar_xlsx_posto.gerar_xlsx_ano_posto(posto, ano, out_dir=WORD_OUT_DIR)
    return send_file(out_path, as_attachment=True)


def _escolher_porta():
    """Tenta a 5000; se estiver ocupada (outra instancia, zumbi, outro app),
    pede uma porta livre qualquer ao sistema em vez de morrer em silencio."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 5000))
        s.close()
        return 5000
    except OSError:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        porta = s.getsockname()[1]
        s.close()
        return porta


def _abrir_navegador_quando_pronto(porta):
    import time
    import urllib.request
    import webbrowser
    url = f"http://127.0.0.1:{porta}"
    for _ in range(50):
        try:
            urllib.request.urlopen(url, timeout=1)
            break
        except Exception:
            time.sleep(0.2)
    webbrowser.open(url)


if __name__ == "__main__":
    if FROZEN:
        import threading
        porta = _escolher_porta()
        print("=" * 56)
        print(f"  Site da Escala BCI no ar: http://127.0.0.1:{porta}")
        print("  O navegador vai abrir sozinho em instantes.")
        print()
        print("  FECHE ESTA JANELA quando terminar de usar o site.")
        print("=" * 56)
        threading.Thread(
            target=_abrir_navegador_quando_pronto, args=(porta,), daemon=True
        ).start()
        app.run(debug=False, port=porta)
    else:
        app.run(debug=True, port=5000)
