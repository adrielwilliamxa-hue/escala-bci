# -*- coding: utf-8 -*-
"""
Gera os documentos Word (.docx) da escala de plantoes BCI, no mesmo layout
dos documentos originais, a partir dos valores ja calculados na planilha
Escala-BCI-2026.xlsx.

Uso:
    python gerar_word.py Junho        (gera so o mes indicado)
    python gerar_word.py todos        (gera os 12 meses)

Importante: abra e feche a planilha no Excel normalmente antes de rodar
este script, para garantir que as formulas foram recalculadas e salvas.
"""
import sys
import os
import datetime
import openpyxl
import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_ORIENT
from docx.shared import Pt, Inches, Cm

import regra_rodizio

if getattr(sys, "frozen", False):
    # Dentro do "Escala BCI.exe": __file__ aponta pra pasta temporaria do
    # PyInstaller (apagada ao fechar) -- os Word devem nascer ao lado do exe.
    BASE_DIR = os.path.dirname(sys.executable)
    ASSETS_DIR = os.path.join(sys._MEIPASS, "assets")
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
WORKBOOK_PATH = os.path.join(BASE_DIR, "Escala-BCI-2026.xlsx")
OUT_DIR = os.path.join(BASE_DIR, "Word gerados")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.jpg")

WEEKDAY_NAMES = ["Domingo", "Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"]
MES_NOMES = ["", "JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO", "JULHO",
             "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]
DIAS_NO_MES_2026 = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}
MONTH_SHEET_NAMES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho",
                      "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]


def set_cell_borders(table):
    table.style = "Table Grid"


def _fixar_largura_tabela(table, largura_total_twips):
    """Forca w:tblW type=dxa com a largura total exata -- sem isso, mesmo
    definindo a largura de cada coluna, o Word/LibreOffice mantem w:tblW
    type=auto e recalcula a tabela pelo conteudo, encolhendo colunas ate
    quebrar o texto letra por letra e estourar para varias paginas."""
    from docx.oxml.ns import qn
    tblPr = table._tbl.tblPr
    tblW = tblPr.find(qn("w:tblW"))
    if tblW is None:
        from docx.oxml import OxmlElement
        tblW = OxmlElement("w:tblW")
        tblPr.append(tblW)
    tblW.set(qn("w:type"), "dxa")
    tblW.set(qn("w:w"), str(largura_total_twips))


def _sombrear_celula(cell, cor_hex):
    """Aplica sombreamento solido a uma celula -- usado pra reproduzir as
    cores de destaque do documento original (azul no titulo/cabecalhos,
    preto no rotulo de turno, amarelo no bloco de ferias)."""
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), cor_hex)
    cell._tc.get_or_add_tcPr().append(shd)


def _cor_texto(run, cor_hex):
    run.font.color.rgb = docx.shared.RGBColor.from_string(cor_hex)


def _separador_de_tabelas(doc):
    """Paragrafo minusculo entre duas tabelas consecutivas. Sem ele, tabelas
    adjacentes sao fundidas numa so pelo renderizador (grades de 8, 1 e 2
    colunas misturadas), colapsando todas as colunas ao minimo -- foi o bug
    que espremia a escala inteira numa faixa estreita letra por letra."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    run = p.add_run(" ")
    run.font.size = Pt(2)
    return p


def _borda_inferior_celula(cell, cor_hex, tamanho=8):
    """Aplica uma borda inferior mais grossa a uma celula -- usado pra separar
    visualmente os dois pares de posicoes (turno 07-19h e turno 10-22h) dentro
    do mesmo dia, deixando claro qual nome pertence a qual horario."""
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(tamanho))
    bottom.set(qn("w:space"), "0")
    bottom.set(qn("w:color"), cor_hex)
    tcBorders.append(bottom)
    tcPr.append(tcBorders)


def add_bold_paragraph(doc, text, center=False):
    p = doc.add_paragraph()
    if center:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    run.bold = True
    return p


def week_layout(ano, mes, dias_no_mes):
    month_start = datetime.date(ano, mes, 1)
    python_dow = month_start.weekday()  # Mon=0..Sun=6
    days_since_sunday = (python_dow + 1) % 7
    first_sunday = month_start - datetime.timedelta(days=days_since_sunday)
    month_end = datetime.date(ano + (mes == 12), (mes % 12) + 1, 1) - datetime.timedelta(days=1)
    n_weeks = 1
    while first_sunday + datetime.timedelta(days=7 * n_weeks) <= month_end:
        n_weeks += 1
    return first_sunday, month_start, month_end, n_weeks


def read_calc_values(wb, calc_sheet_name, dias_no_mes):
    ws = wb[calc_sheet_name]
    first_row = 4
    values = {}
    for d in range(1, dias_no_mes + 1):
        r = first_row + d - 1
        g = ws.cell(row=r, column=7).value or ""
        h = ws.cell(row=r, column=8).value or ""
        i_ = ws.cell(row=r, column=9).value or ""
        j = ws.cell(row=r, column=10).value or ""
        values[d] = (g, h, i_, j)
    return values


def read_emissao(wb, nome_aba, n_weeks):
    ws = wb[nome_aba]
    footer_row = 9 + 5 * n_weeks
    return ws.cell(row=footer_row, column=5).value or ""


def read_certificados(wb):
    ws = wb["Configuração"]
    certs = []
    for i in range(8):
        r = 85 + i
        nome = ws.cell(row=r, column=1).value
        cod = ws.cell(row=r, column=2).value
        if nome:
            certs.append((nome, cod or ""))
    return certs


def montar_docx(values, certificados, ano, mes, doc_num, local, emissao, ferias_ativas=None,
                 linhas_turno=None):
    """Monta o docx da escala do mes a partir de valores ja calculados.
    Compartilhada por gerar_docx_mes (fonte: Excel), gerar_docx_mes_de_dados
    (fonte: dados.json/regra_rodizio, posto CENTRAL) e gerar_docx_mes_posto
    (fonte: motor.py, qualquer posto) -- a logica de montagem e identica,
    so muda de onde vem `values`, `certificados` e a forma da grade.

    linhas_turno: lista de (rotulo, n_posicoes) descrevendo os turnos do
    posto, na ordem em que devem aparecer -- default (None) usa o layout
    fixo original do CENTRAL (2 turnos, 2 posicoes cada, 4 linhas de dados).
    `values[dia]` deve ter exatamente sum(n_posicoes) itens, na mesma
    ordem dos turnos em `linhas_turno`.
    """
    if linhas_turno is None:
        linhas_turno = [("DAS 07H00\nÀS 19H00", 2), ("DAS 10H00\nÀS 22H00", 2)]
    n_linhas_dados = sum(n for _, n in linhas_turno)

    dias_no_mes = DIAS_NO_MES_2026[mes]
    first_sunday, month_start, month_end, n_weeks = week_layout(ano, mes, dias_no_mes)

    doc = docx.Document()
    doc.styles["Normal"].font.name = "Arial"
    doc.styles["Normal"].font.size = Pt(10)

    secao = doc.sections[0]
    secao.orientation = WD_ORIENT.LANDSCAPE
    secao.page_width, secao.page_height = secao.page_height, secao.page_width
    secao.top_margin = Cm(0.5)
    secao.bottom_margin = Cm(0.5)
    secao.left_margin = Cm(1)
    secao.right_margin = Cm(1)
    secao.header_distance = Cm(0.3)
    secao.footer_distance = Cm(0.3)

    footer_p = secao.footer.paragraphs[0]
    footer_p.text = f"Brasília, {datetime.date.today().strftime('%d/%m/%Y')}."
    footer_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for run in footer_p.runs:
        run.font.size = Pt(8)

    if os.path.exists(LOGO_PATH):
        logo_p = doc.add_paragraph()
        logo_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        logo_p.paragraph_format.space_after = Pt(2)
        logo_p.add_run().add_picture(LOGO_PATH, width=Inches(1))

    for texto, negrito in [
        (f"ESCALA DE PLANTÕES / SERVIÇO / BCI / {local} Nº {doc_num:02d}/{ano}.", True),
        ("À GUARNIÇÃO DA BRIGADA CONTRA INCÊNDIO.", True),
        (f"REFERENTE: Escala de plantões / serviço para o período de 01 a {month_end.strftime('%d/%m/%Y')}.", False),
        (f"ESCALA DE PLANTÕES DA BRIGADA CONTRA INCÊNDIO {local}.", True),
    ]:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(2)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(texto)
        run.bold = negrito
        run.font.size = Pt(8)

    # A grade usa o layout automatico do Word (sem larguras fixas): com
    # tblLayout=fixed + celulas mescladas (banner e rotulos de turno), o
    # renderizador colapsa as colunas ao minimo e quebra os nomes letra a
    # letra -- foi exatamente o bug do Nº 11-2026. O layout automatico
    # distribui as 8 colunas pela pagina em paisagem corretamente.
    rows_per_week = 1 + n_linhas_dados
    table = doc.add_table(rows=1 + n_weeks * rows_per_week, cols=8)
    set_cell_borders(table)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    banner_cell = table.cell(0, 0)
    for c in range(1, 8):
        banner_cell = banner_cell.merge(table.cell(0, c))
    banner_cell.text = f"{MES_NOMES[mes]} DE {ano}."
    banner_cell.paragraphs[0].runs[0].bold = True
    banner_cell.paragraphs[0].runs[0].font.size = Pt(12)
    banner_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    _sombrear_celula(banner_cell, "BDD7EE")

    for week in range(n_weeks):
        header_row_idx = 1 + week * rows_per_week
        data_row_idx = [header_row_idx + 1 + i for i in range(n_linhas_dados)]

        # rotulo de turno mesclado nas linhas que pertencem a ele (ex.: 2
        # linhas por turno no CENTRAL, 1 linha por turno na NORTE)
        linha_cursor = 0
        for i, (rotulo, n_pos) in enumerate(linhas_turno):
            linhas_do_turno = data_row_idx[linha_cursor:linha_cursor + n_pos]
            label_cell = table.cell(linhas_do_turno[0], 0)
            for r in linhas_do_turno[1:]:
                label_cell = label_cell.merge(table.cell(r, 0))
            label_cell.text = rotulo
            for p in label_cell.paragraphs:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in p.runs:
                    run.bold = True
                    run.font.size = Pt(8)
                    _cor_texto(run, "FFFFFF")
            _sombrear_celula(label_cell, "000000")
            if i == 0:
                _borda_inferior_celula(label_cell, "FFFFFF", tamanho=12)
            linha_cursor += n_pos

        for col_idx in range(7):
            excel_col = col_idx + 1  # table col 1..7 (col 0 is label)
            cell_date = first_sunday + datetime.timedelta(days=7 * week + col_idx)
            in_month = month_start <= cell_date <= month_end
            day_num = cell_date.day

            hcell = table.cell(header_row_idx, excel_col)
            hcell.text = f"{WEEKDAY_NAMES[col_idx]}\n{day_num:02d}" if in_month else ""
            for p in hcell.paragraphs:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                for run in p.runs:
                    run.bold = True
                    run.font.size = Pt(7)
            _sombrear_celula(hcell, "BDD7EE" if in_month else "9FE0EF")

            valores_dia = values[day_num] if in_month else [""] * n_linhas_dados
            ultima_linha_primeiro_turno = linhas_turno[0][1] - 1
            for offset, text in enumerate(valores_dia):
                dcell = table.cell(data_row_idx[offset], excel_col)
                dcell.text = str(text)
                for p in dcell.paragraphs:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p.paragraph_format.space_before = Pt(0)
                    p.paragraph_format.space_after = Pt(0)
                    for run in p.runs:
                        run.font.size = Pt(8)
                if not in_month:
                    _sombrear_celula(dcell, "9FE0EF")
                if offset == ultima_linha_primeiro_turno and len(linhas_turno) > 1:
                    _borda_inferior_celula(dcell, "000000", tamanho=12)

    RODAPE_LARGURA = Inches(2)

    _separador_de_tabelas(doc)
    lei_table = doc.add_table(rows=1, cols=1)
    lei_table.autofit = False
    lei_table.columns[0].width = RODAPE_LARGURA
    _fixar_largura_tabela(lei_table, 2880)
    set_cell_borders(lei_table)
    lei_cell = lei_table.cell(0, 0)
    lei_cell.width = RODAPE_LARGURA
    lei_cell.text = "F. LEI 11.901/2009."
    lei_cell.paragraphs[0].runs[0].bold = True
    lei_cell.paragraphs[0].runs[0].font.size = Pt(7)
    lei_cell.paragraphs[0].paragraph_format.space_before = Pt(0)
    lei_cell.paragraphs[0].paragraph_format.space_after = Pt(0)

    if ferias_ativas:
        _separador_de_tabelas(doc)
        ferias_table = doc.add_table(rows=len(ferias_ativas) * 2, cols=1)
        ferias_table.autofit = False
        ferias_table.columns[0].width = RODAPE_LARGURA
        _fixar_largura_tabela(ferias_table, 2880)
        set_cell_borders(ferias_table)
        for i, f in enumerate(ferias_ativas):
            inicio = datetime.date.fromisoformat(f["inicio"])
            fim = datetime.date.fromisoformat(f["fim"])
            cobertura_cell = ferias_table.cell(i * 2, 0)
            cobertura_cell.width = RODAPE_LARGURA
            cobertura_p = cobertura_cell.paragraphs[0]
            cobertura_p.paragraph_format.space_before = Pt(0)
            cobertura_p.paragraph_format.space_after = Pt(0)
            cobertura_p.add_run("COBERTURA DE FÉRIAS: ").bold = True
            cobertura_p.add_run(f["substituto"])
            for run in cobertura_p.runs:
                run.font.size = Pt(7)
            _sombrear_celula(cobertura_cell, "FFFF00")
            ferias_cell = ferias_table.cell(i * 2 + 1, 0)
            ferias_cell.width = RODAPE_LARGURA
            ferias_p = ferias_cell.paragraphs[0]
            ferias_p.paragraph_format.space_before = Pt(0)
            ferias_p.paragraph_format.space_after = Pt(0)
            ferias_p.add_run("FÉRIAS: ").bold = True
            ferias_p.add_run(
                f"{f['pessoa_completa']} {inicio.strftime('%d/%m/%y')} A {fim.strftime('%d/%m/%y')}. "
                f"({f['duracao_dias']} DIAS)."
            )
            for run in ferias_p.runs:
                run.font.size = Pt(7)

    _separador_de_tabelas(doc)
    cert_table = doc.add_table(rows=len(certificados), cols=2)
    cert_table.autofit = False
    largura_nome = Inches(1.2)
    largura_codigo = Inches(0.8)
    cert_table.columns[0].width = largura_nome
    cert_table.columns[1].width = largura_codigo
    _fixar_largura_tabela(cert_table, 2880)
    set_cell_borders(cert_table)
    for i, (nome, cod) in enumerate(certificados):
        nome_cell = cert_table.cell(i, 0)
        nome_cell.width = largura_nome
        nome_cell.text = str(nome)
        run = nome_cell.paragraphs[0].runs[0]
        run.bold = True
        run.font.size = Pt(7)
        _cor_texto(run, "FF0000")
        nome_cell.paragraphs[0].paragraph_format.space_before = Pt(0)
        nome_cell.paragraphs[0].paragraph_format.space_after = Pt(0)
        codigo_cell = cert_table.cell(i, 1)
        codigo_cell.width = largura_codigo
        codigo_cell.text = str(cod)
        codigo_cell.paragraphs[0].runs[0].font.size = Pt(7)
        codigo_cell.paragraphs[0].paragraph_format.space_before = Pt(0)
        codigo_cell.paragraphs[0].paragraph_format.space_after = Pt(0)

    os.makedirs(OUT_DIR, exist_ok=True)
    filename = f"ESCALA DE PLANTÕES - SERVIÇO BCI - {local} Nº {doc_num:02d}-{ano}.docx"
    out_path = os.path.join(OUT_DIR, filename)
    doc.save(out_path)
    return out_path


def gerar_docx_mes(wb, nome_aba, ano, mes, doc_num, local):
    """Wrapper fino: le os valores calculados do Excel e chama montar_docx."""
    dias_no_mes = DIAS_NO_MES_2026[mes]
    calc_sheet_name = f"_Cálculo {nome_aba}"
    values = read_calc_values(wb, calc_sheet_name, dias_no_mes)
    _, _, _, n_weeks = week_layout(ano, mes, dias_no_mes)
    emissao = read_emissao(wb, nome_aba, n_weeks)
    certificados = read_certificados(wb)
    return montar_docx(values, certificados, ano, mes, doc_num, local, emissao)


def valores_de_regra_rodizio(dados, ano, mes, overrides_fds):
    """Equivalente a read_calc_values, mas lendo do motor de calculo (dados.json)
    em vez de uma planilha Excel ja calculada."""
    dias = regra_rodizio.computar_mes(dados, ano, mes, overrides_fds)
    values = {}
    for d in dias:
        values[d["dia"]] = (d["pos_0719_1"], d["pos_0719_2"], d["pos_1022_1"], d["pos_1022_2"])
    return values


def gerar_docx_mes_de_dados(dados, ano, mes, doc_num, local, emissao="", overrides_fds=None):
    """Wrapper fino: le os valores de dados.json/regra_rodizio e chama montar_docx --
    mesma montagem que gerar_docx_mes, so muda a fonte dos valores."""
    values = valores_de_regra_rodizio(dados, ano, mes, overrides_fds or {})
    certificados = [(c["pessoa"], c["codigo"]) for c in dados.get("certificados", [])]
    ferias_ativas = regra_rodizio.ferias_ativas_no_mes(dados, ano, mes)
    return montar_docx(values, certificados, ano, mes, doc_num, local, emissao, ferias_ativas=ferias_ativas)


def _rotulo_turno(turno_id):
    """'0719' -> 'DAS 07H00\nÀS 19H00'; qualquer id de 4 digitos vira o mesmo
    padrao, outros ids aparecem como estao (maiusculo)."""
    if len(turno_id) == 4 and turno_id.isdigit():
        return f"DAS {turno_id[:2]}H00\nÀS {turno_id[2:]}H00"
    return turno_id.upper()


def gerar_docx_mes_posto(posto, ano, mes, doc_num, emissao=""):
    """Gera o docx do mes pra QUALQUER posto cadastrado (scripts/postos.py),
    usando o Motor Universal (scripts/motor.py) -- nenhuma logica especifica
    de posto aqui, so projeta a saida do motor no mesmo layout visual do
    CENTRAL, com a grade adaptada ao numero real de turnos/posicoes do posto."""
    import calendar
    import motor as motor_mod

    linhas_turno = [(_rotulo_turno(t["id"]), t["n_posicoes"]) for t in posto["turnos"]]
    overrides_fds = posto.get("overrides_fds", {})
    dias = motor_mod.computar_mes_generico(posto, ano, mes, overrides_fds)

    values = {}
    for d in dias:
        linha = []
        for turno in posto["turnos"]:
            linha.extend(d["turnos"][turno["id"]]["valores"])
        values[d["dia"]] = linha

    certificados = [(c["pessoa"], c.get("codigo", "")) for c in posto.get("certificados", [])]
    mes_inicio = datetime.date(ano, mes, 1)
    mes_fim = datetime.date(ano, mes, calendar.monthrange(ano, mes)[1])
    ferias_ativas = []
    for f in posto.get("ferias", []):
        inicio = datetime.date.fromisoformat(f["inicio"])
        fim = datetime.date.fromisoformat(f["fim"])
        if inicio <= mes_fim and fim >= mes_inicio:
            ferias_ativas.append({
                "pessoa_completa": f.get("pessoa_completa") or f["pessoa"],
                "substituto": f["substituto"],
                "inicio": f["inicio"], "fim": f["fim"],
                "duracao_dias": (fim - inicio).days + 1,
            })

    return montar_docx(
        values, certificados, ano, mes, doc_num, posto["posto_nome"], emissao,
        ferias_ativas=ferias_ativas, linhas_turno=linhas_turno,
    )


def main():
    if len(sys.argv) < 2:
        print("Uso: python gerar_word.py <Mês|todos>")
        sys.exit(1)
    alvo = sys.argv[1].strip().lower()

    wb = openpyxl.load_workbook(WORKBOOK_PATH, data_only=True)

    if alvo == "todos":
        meses_a_gerar = MONTH_SHEET_NAMES
    else:
        meses_a_gerar = [m for m in MONTH_SHEET_NAMES if m.lower() == alvo]
        if not meses_a_gerar:
            print(f"Mês '{sys.argv[1]}' não reconhecido. Use um de: {', '.join(MONTH_SHEET_NAMES)} ou 'todos'.")
            sys.exit(1)

    for nome in meses_a_gerar:
        if nome == "Abril":
            print("Abril usa regra histórica (sem motor de cálculo) — gerar Word desse mês não está automatizado. Pulando.")
            continue
        mes_num = MONTH_SHEET_NAMES.index(nome) + 1
        out_path = gerar_docx_mes(wb, nome, 2026, mes_num, doc_num=mes_num, local="POSTO CENTRAL")
        print(f"Gerado: {out_path}")


if __name__ == "__main__":
    main()
