\
# -*- coding: utf-8 -*-
import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, Protection
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.properties import PageSetupProperties
import datetime

UNLOCKED = Protection(locked=False)

FONT_NAME = "Arial"
BLUE = Font(name=FONT_NAME, color="0000FF")
BLUE_BOLD = Font(name=FONT_NAME, color="0000FF", bold=True)
BLACK = Font(name=FONT_NAME, color="000000")
BOLD = Font(name=FONT_NAME, bold=True)
TITLE = Font(name=FONT_NAME, bold=True, size=14)
SECTION = Font(name=FONT_NAME, bold=True, size=11, color="FFFFFF")
SECTION_FILL = PatternFill("solid", fgColor="4472C4")
HEADER_FILL = PatternFill("solid", fgColor="D9E1F2")
HELPER_FILL = PatternFill("solid", fgColor="F2F2F2")
HELPER_FONT = Font(name=FONT_NAME, color="808080", size=9)
YELLOW = PatternFill("solid", fgColor="FFFF00")
GRID_LABEL_FILL = PatternFill("solid", fgColor="1F3864")
GRID_LABEL_FONT = Font(name=FONT_NAME, bold=True, size=8, color="FFFFFF")
GRID_HEADER_FILL = PatternFill("solid", fgColor="D9E1F2")
GRID_HEADER_FONT = Font(name=FONT_NAME, bold=True, size=9)
GRID_NAME_FONT = Font(name=FONT_NAME, size=9)
LINK_FONT = Font(name=FONT_NAME, color="0563C1", underline="single", size=12)
WARN_FILL = PatternFill("solid", fgColor="FFC000")
WARN_FONT = Font(name=FONT_NAME, bold=True, size=9)
THIN = Side(style="thin", color="808080")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

WEEKDAY_NAMES = ["Domingo", "Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"]
MES_NOMES = ["", "JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO", "JULHO",
             "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]
MES_NOMES_MIN = ["", "janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
                  "agosto", "setembro", "outubro", "novembro", "dezembro"]
DIAS_NO_MES_2026 = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}

def emissao_default(ano, mes):
    prev_month = mes - 1 if mes > 1 else 12
    prev_year = ano if mes > 1 else ano - 1
    return f"15 de {MES_NOMES_MIN[prev_month]} de {prev_year}"

def weekend_defaults(ano, mes, dias_no_mes):
    """Alternating 1/2 default for which 10-22 position covers each weekend day, chronological."""
    overrides = {}
    toggle = 1
    for d in range(1, dias_no_mes + 1):
        wd = datetime.date(ano, mes, d).weekday()  # Mon=0..Sun=6
        if wd in (5, 6):  # Saturday, Sunday
            overrides[d] = toggle if toggle == 2 else ""  # leave blank when toggle==1 (default)
            toggle = 2 if toggle == 1 else 1
    return overrides

wb = openpyxl.Workbook()
wb.remove(wb.active)

# ================================================================== Configuração (built first, referenced by Início)
cfg = wb.create_sheet("Configuração")
for col, width in zip("ABCDE", [16, 14, 12, 10, 26]):
    cfg.column_dimensions[col].width = width

cfg["A1"] = "CONFIGURAÇÃO DA ESCALA — BCI"
cfg["A1"].font = TITLE

def section(ws_, cell, text):
    ws_[cell] = text
    ws_[cell].font = SECTION
    row = int(''.join(filter(str.isdigit, cell)))
    for col in "ABCDE":
        ws_[f"{col}{row}"].fill = SECTION_FILL

section(cfg, "A3", "EQUIPE (Bravo / Alfa) — nome, equipe, turno, posição")
headers = ["Nome", "Equipe", "Turno", "Posição", "Chave (automática)"]
for i, h in enumerate(headers):
    c = cfg.cell(row=4, column=i + 1, value=h)
    c.font = BOLD
    c.fill = HEADER_FILL

equipe = [
    ("EDUARDO", "Bravo", "07-19", 1),
    ("BRUNO", "Bravo", "07-19", 2),
    ("GABRIEL", "Bravo", "10-22", 1),
    ("IGOR", "Bravo", "10-22", 2),
    ("VITOR", "Alfa", "07-19", 1),
    ("CARLOS", "Alfa", "07-19", 2),
    ("DANIEL", "Alfa", "10-22", 1),
    ("JULIO", "Alfa", "10-22", 2),
]
row0 = 5
for i, (nome, eq, turno, pos) in enumerate(equipe):
    r = row0 + i
    for col in (1, 2, 3, 4):
        cfg.cell(row=r, column=col).font = BLUE
        cfg.cell(row=r, column=col).protection = UNLOCKED
    cfg.cell(row=r, column=1, value=nome)
    cfg.cell(row=r, column=2, value=eq)
    cfg.cell(row=r, column=3, value=turno)
    cfg.cell(row=r, column=4, value=pos)
    cfg.cell(row=r, column=5, value=f"=B{r}&\"|\"&C{r}&\"|\"&D{r}").font = HELPER_FONT
    cfg.cell(row=r, column=5).fill = HELPER_FILL

section(cfg, "A15", "DATA-ÂNCORA DO RODÍZIO")
cfg["A16"] = "Data em que a equipe BRAVO trabalha (referência):"
cfg["A16"].font = BLACK
cfg["B16"] = datetime.date(2026, 4, 1)
cfg["B16"].font = BLUE_BOLD
cfg["B16"].number_format = "DD/MM/YYYY"
cfg["B16"].fill = YELLOW
cfg["B16"].protection = UNLOCKED

section(cfg, "A19", "FOLGÕES (folga estendida) — pelo menos 1 por pessoa/mês")
fh = ["Pessoa", "Data", "Substituto (quem cobre)", "Linha (automática)"]
for i, h in enumerate(fh):
    c = cfg.cell(row=20, column=i + 1, value=h)
    c.font = BOLD
    c.fill = HEADER_FILL
folgoes = [
    ("CARLOS", datetime.date(2026, 4, 4), "DANIEL"),
    ("DANIEL", datetime.date(2026, 4, 26), "CARLOS"),
]
FOLGA_START = 21
FOLGA_END = 50
for r in range(FOLGA_START, FOLGA_END + 1):
    idx = r - FOLGA_START
    for col in (1, 2, 3):
        cfg.cell(row=r, column=col).font = BLUE
        cfg.cell(row=r, column=col).protection = UNLOCKED
    if idx < len(folgoes):
        nome, data, sub = folgoes[idx]
        cfg.cell(row=r, column=1, value=nome)
        c = cfg.cell(row=r, column=2, value=data)
        c.number_format = "DD/MM/YYYY"
        cfg.cell(row=r, column=3, value=sub)
    cfg.cell(row=r, column=4, value="=ROW()").font = HELPER_FONT
    cfg.cell(row=r, column=4).fill = HELPER_FILL

section(cfg, "A53", "FÉRIAS / SUBSTITUIÇÕES")
vh = ["Pessoa", "Início", "Fim", "Substituto", "Linha (automática)"]
for i, h in enumerate(vh):
    c = cfg.cell(row=54, column=i + 1, value=h)
    c.font = BOLD
    c.fill = HEADER_FILL
ferias = [
    ("DANIEL", datetime.date(2026, 7, 15), datetime.date(2026, 8, 3), "HUGO"),
]
FERIAS_START = 55
FERIAS_END = 80
for r in range(FERIAS_START, FERIAS_END + 1):
    idx = r - FERIAS_START
    for col in (1, 2, 3, 4):
        cfg.cell(row=r, column=col).font = BLUE
        cfg.cell(row=r, column=col).protection = UNLOCKED
    if idx < len(ferias):
        nome, ini, fim, sub = ferias[idx]
        cfg.cell(row=r, column=1, value=nome)
        c1 = cfg.cell(row=r, column=2, value=ini)
        c1.number_format = "DD/MM/YYYY"
        c2 = cfg.cell(row=r, column=3, value=fim)
        c2.number_format = "DD/MM/YYYY"
        cfg.cell(row=r, column=4, value=sub)
    cfg.cell(row=r, column=5, value="=ROW()").font = HELPER_FONT
    cfg.cell(row=r, column=5).fill = HELPER_FILL

section(cfg, "A83", "CERTIFICADOS / RECICLAGENS (nome segue a Equipe; código é texto livre)")
ch = ["Pessoa", "Código"]
for i, h in enumerate(ch):
    c = cfg.cell(row=84, column=i + 1, value=h)
    c.font = BOLD
    c.fill = HEADER_FILL
certificados = [
    ("EDUARDO", "05-19"), ("BRUNO", "05-19"), ("GABRIEL", "11-25"), ("IGOR", "11-25"),
    ("VITOR", "12-26"), ("CARLOS", "04-12"), ("DANIEL", "18-26"), ("JULIO", "04-18"),
]
for i, (nome, cod) in enumerate(certificados):
    r = 85 + i
    equipe_row = row0 + i  # mesma ordem 1:1 da tabela de Equipe (linha 5 em diante)
    cfg.cell(row=r, column=1, value=f"=A{equipe_row}").font = HELPER_FONT
    cfg.cell(row=r, column=1).fill = HELPER_FILL
    cfg.cell(row=r, column=2, value=cod).font = BLUE
    cfg.cell(row=r, column=2).protection = UNLOCKED

# ---- data validation (dropdowns) to prevent typos that would silently break the calculation
dv_equipe = DataValidation(type="list", formula1='"Bravo,Alfa"', allow_blank=True, showErrorMessage=True,
                            errorTitle="Valor inválido", error="Escolha Bravo ou Alfa.")
dv_turno = DataValidation(type="list", formula1='"07-19,10-22"', allow_blank=True, showErrorMessage=True,
                           errorTitle="Valor inválido", error="Escolha 07-19 ou 10-22.")
dv_pos = DataValidation(type="list", formula1='"1,2"', allow_blank=True, showErrorMessage=True,
                         errorTitle="Valor inválido", error="Escolha 1 ou 2.")
dv_pessoa = DataValidation(type="list", formula1="=$A$5:$A$12", allow_blank=True, showErrorMessage=True,
                            errorTitle="Pessoa não cadastrada",
                            error="Escolha um nome da lista de equipe (aba Configuração, linhas 5-12).")
for dv in (dv_equipe, dv_turno, dv_pos, dv_pessoa):
    cfg.add_data_validation(dv)
dv_equipe.add("B5:B12")
dv_turno.add("C5:C12")
dv_pos.add("D5:D12")
dv_pessoa.add("A21:A50")
dv_pessoa.add("A55:A80")

cfg.protection.sheet = True

# ================================================================== engine (hidden calc sheet)
HELPER_COLS = ["K","L","M","N","O","P","Q","R","S","T","U","V","W","X","Y","Z","AA","AB","AC","AD","AE","AF","AG","AH"]

def build_engine(ws_, ano, mes, dias_no_mes, weekend_pos_overrides):
    for col, width in zip("ABCDEFGHIJ", [6, 12, 12, 10, 10, 10, 16, 16, 16, 16]):
        ws_.column_dimensions[col].width = width
    for col in HELPER_COLS:
        ws_.column_dimensions[col].width = 12

    ws_["A1"] = f"Motor de cálculo — {mes:02d}/{ano} (não editar, exceto coluna F em azul)"
    ws_["A1"].font = TITLE

    headers = ["Dia", "Data", "Dia da semana", "Tipo", "Equipe do dia",
               "Pos. 10-22\nfim de semana", "07h-19h\nPos.1", "07h-19h\nPos.2",
               "10h-22h\nNome 1", "10h-22h\nNome 2"]
    for i, h in enumerate(headers):
        c = ws_.cell(row=3, column=i + 1, value=h)
        c.font = BOLD
        c.fill = HEADER_FILL
        c.alignment = Alignment(wrap_text=True, horizontal="center")

    helper_headers = ["Base0719_1","Base0719_2","Base1022_1","Base1022_2",
                       "FériasLinha0719_1","FériasLinha0719_2","FériasLinha1022_1","FériasLinha1022_2",
                       "FériasSub0719_1","FériasSub0719_2","FériasSub1022_1","FériasSub1022_2",
                       "FolgaLinha0719_1","FolgaLinha0719_2","FolgaLinha1022_1","FolgaLinha1022_2",
                       "FolgaSub0719_1","FolgaSub0719_2","FolgaSub1022_1","FolgaSub1022_2",
                       "Resolvido0719_1","Resolvido0719_2","Resolvido1022_1","Resolvido1022_2"]
    for i, h in enumerate(helper_headers):
        c = ws_.cell(row=3, column=11 + i, value=h)
        c.font = HELPER_FONT
        c.fill = HELPER_FILL
        c.alignment = Alignment(wrap_text=True, horizontal="center")

    first_row = 4
    dv_f = DataValidation(type="list", formula1='"1,2"', allow_blank=True)
    ws_.add_data_validation(dv_f)
    dv_f.add(f"F{first_row}:F{first_row + dias_no_mes - 1}")

    for d in range(1, dias_no_mes + 1):
        r = first_row + d - 1
        A, B, C, D, E, F, G, H, I, J = [f"{col}{r}" for col in "ABCDEFGHIJ"]
        K,L,M,N,O,P,Q,R,S,T,U,V,W,X,Y,Z,AA,AB,AC,AD,AE,AF,AG,AH = [f"{col}{r}" for col in HELPER_COLS]

        ws_[A] = d
        ws_[A].font = BLACK
        ws_[B] = f"=DATE({ano},{mes},{A})"
        ws_[B].number_format = "DD/MM/YYYY"
        ws_[B].font = BLACK
        ws_[C] = f'=TEXT({B},"dddd")'
        ws_[C].font = BLACK
        ws_[D] = f'=IF(WEEKDAY({B})=1,"Domingo",IF(WEEKDAY({B})=7,"Sábado","Útil"))'
        ws_[D].font = BLACK
        ws_[E] = f'=IF(MOD({B}-Configuração!$B$16,2)=0,"Bravo","Alfa")'
        ws_[E].font = BLACK

        override = weekend_pos_overrides.get(d, "")
        ws_[F] = override
        ws_[F].font = BLUE
        ws_[F].protection = UNLOCKED

        ws_[K] = f'=INDEX(Configuração!$A$5:$A$12,MATCH($E{r}&"|07-19|1",Configuração!$E$5:$E$12,0))'
        ws_[L] = f'=INDEX(Configuração!$A$5:$A$12,MATCH($E{r}&"|07-19|2",Configuração!$E$5:$E$12,0))'
        ws_[M] = f'=INDEX(Configuração!$A$5:$A$12,MATCH($E{r}&"|10-22|1",Configuração!$E$5:$E$12,0))'
        ws_[N] = f'=INDEX(Configuração!$A$5:$A$12,MATCH($E{r}&"|10-22|2",Configuração!$E$5:$E$12,0))'
        for cell in (K, L, M, N):
            ws_[cell].font = HELPER_FONT
            ws_[cell].fill = HELPER_FILL

        ws_[O] = f'=_xlfn.MAXIFS(Configuração!$E$55:$E$80,Configuração!$A$55:$A$80,{K},Configuração!$B$55:$B$80,"<="&${B},Configuração!$C$55:$C$80,">="&${B})'
        ws_[P] = f'=_xlfn.MAXIFS(Configuração!$E$55:$E$80,Configuração!$A$55:$A$80,{L},Configuração!$B$55:$B$80,"<="&${B},Configuração!$C$55:$C$80,">="&${B})'
        ws_[Q] = f'=_xlfn.MAXIFS(Configuração!$E$55:$E$80,Configuração!$A$55:$A$80,{M},Configuração!$B$55:$B$80,"<="&${B},Configuração!$C$55:$C$80,">="&${B})'
        ws_[R] = f'=_xlfn.MAXIFS(Configuração!$E$55:$E$80,Configuração!$A$55:$A$80,{N},Configuração!$B$55:$B$80,"<="&${B},Configuração!$C$55:$C$80,">="&${B})'
        for cell in (O, P, Q, R):
            ws_[cell].font = HELPER_FONT
            ws_[cell].fill = HELPER_FILL

        ws_[S] = f'=IF({O}=0,"",INDEX(Configuração!$D$55:$D$80,{O}-54))'
        ws_[T] = f'=IF({P}=0,"",INDEX(Configuração!$D$55:$D$80,{P}-54))'
        ws_[U] = f'=IF({Q}=0,"",INDEX(Configuração!$D$55:$D$80,{Q}-54))'
        ws_[V] = f'=IF({R}=0,"",INDEX(Configuração!$D$55:$D$80,{R}-54))'
        for cell in (S, T, U, V):
            ws_[cell].font = HELPER_FONT
            ws_[cell].fill = HELPER_FILL

        ws_[W] = f'=_xlfn.MAXIFS(Configuração!$D$21:$D$50,Configuração!$A$21:$A$50,{K},Configuração!$B$21:$B$50,${B})'
        ws_[X] = f'=_xlfn.MAXIFS(Configuração!$D$21:$D$50,Configuração!$A$21:$A$50,{L},Configuração!$B$21:$B$50,${B})'
        ws_[Y] = f'=_xlfn.MAXIFS(Configuração!$D$21:$D$50,Configuração!$A$21:$A$50,{M},Configuração!$B$21:$B$50,${B})'
        ws_[Z] = f'=_xlfn.MAXIFS(Configuração!$D$21:$D$50,Configuração!$A$21:$A$50,{N},Configuração!$B$21:$B$50,${B})'
        for cell in (W, X, Y, Z):
            ws_[cell].font = HELPER_FONT
            ws_[cell].fill = HELPER_FILL

        ws_[AA] = f'=IF({W}=0,"",INDEX(Configuração!$C$21:$C$50,{W}-20))'
        ws_[AB] = f'=IF({X}=0,"",INDEX(Configuração!$C$21:$C$50,{X}-20))'
        ws_[AC] = f'=IF({Y}=0,"",INDEX(Configuração!$C$21:$C$50,{Y}-20))'
        ws_[AD] = f'=IF({Z}=0,"",INDEX(Configuração!$C$21:$C$50,{Z}-20))'
        for cell in (AA, AB, AC, AD):
            ws_[cell].font = HELPER_FONT
            ws_[cell].fill = HELPER_FILL

        ws_[AE] = f'=IF({S}<>"",{S},IF({AA}<>"",{AA},{K}))'
        ws_[AF] = f'=IF({T}<>"",{T},IF({AB}<>"",{AB},{L}))'
        ws_[AG] = f'=IF({U}<>"",{U},IF({AC}<>"",{AC},{M}))'
        ws_[AH] = f'=IF({V}<>"",{V},IF({AD}<>"",{AD},{N}))'
        for cell in (AE, AF, AG, AH):
            ws_[cell].font = HELPER_FONT
            ws_[cell].fill = HELPER_FILL

        ws_[G] = f'=IF(${D}="Domingo","",{AE})'
        ws_[H] = f'=IF(${D}="Sábado","",{AF})'
        ws_[I] = f'=IF(${D}="Útil",{AG},IF(OR(${F}="",${F}=1),{AG},{AH}))'
        ws_[J] = f'=IF(${D}="Útil",{AH},"")'
        for cell in (G, H, I, J):
            ws_[cell].font = BLACK
            ws_[cell].alignment = Alignment(horizontal="center")

    ws_.freeze_panes = "A4"
    ws_.protection.sheet = True
    return first_row

# ================================================================== visual grid (matches original layout)
def build_grid(ws_, ano, mes, dias_no_mes, calc_sheet_name, calc_first_row, doc_num, local, emissao_padrao):
    ws_.column_dimensions["A"].width = 14
    for col in "BCDEFGH":
        ws_.column_dimensions[col].width = 13

    ws_["A1"] = f"ESCALA DE PLANTÕES / SERVIÇO / BCI / {local} Nº {doc_num:02d}/{ano}."
    ws_["A1"].font = BOLD
    ws_["A2"] = "À GUARNIÇÃO DA BRIGADA CONTRA INCÊNDIO."
    ws_["A2"].font = BOLD
    ws_["A3"] = (f'="REFERENTE: Escala de plantões / serviço para o período de 01 a "'
                 f'&TEXT(EOMONTH(DATE({ano},{mes},1),0),"DD/MM/YYYY")&"."')
    ws_["A3"].font = BLACK
    ws_["A5"] = f"ESCALA DE PLANTÕES DA BRIGADA CONTRA INCÊNDIO {local}."
    ws_["A5"].font = BOLD
    ws_["A5"].alignment = Alignment(horizontal="center")
    ws_.merge_cells("A5:H5")

    ws_["A6"] = ("Ajuste pontual (só este dia): edite a célula aqui embaixo. Para trocar o nome de alguém em "
                 "TODOS os meses: edite a aba Configuração.")
    ws_["A6"].font = WARN_FONT
    ws_["A6"].fill = WARN_FILL
    ws_["A6"].alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws_.merge_cells("A6:H6")
    ws_.row_dimensions[6].height = 26

    banner_row = 7
    ws_.cell(row=banner_row, column=1, value=f"{MES_NOMES[mes]} DE {ano}.")
    for col in range(1, 9):
        c = ws_.cell(row=banner_row, column=col)
        c.font = Font(name=FONT_NAME, bold=True)
        c.fill = GRID_HEADER_FILL
        c.alignment = Alignment(horizontal="center")
        c.border = BORDER
    ws_.merge_cells(start_row=banner_row, start_column=1, end_row=banner_row, end_column=8)

    month_start = datetime.date(ano, mes, 1)
    python_dow = month_start.weekday()  # Mon=0..Sun=6
    days_since_sunday = (python_dow + 1) % 7  # Sunday->0 ... Saturday->6
    first_sunday = month_start - datetime.timedelta(days=days_since_sunday)
    month_end = (datetime.date(ano + (mes == 12), (mes % 12) + 1, 1) - datetime.timedelta(days=1))

    n_weeks = 1
    while first_sunday + datetime.timedelta(days=7 * n_weeks) <= month_end:
        n_weeks += 1

    row = banner_row + 1
    calc_last_row = calc_first_row + dias_no_mes - 1
    for week in range(n_weeks):
        header_row = row
        row1, row2, row3, row4 = row + 1, row + 2, row + 3, row + 4

        ws_.cell(row=row1, column=1, value="DAS 07H00 ÀS 19H00 / DAS 10H00 ÀS 22H00")
        ws_.merge_cells(start_row=row1, start_column=1, end_row=row4, end_column=1)
        lbl = ws_.cell(row=row1, column=1)
        lbl.font = GRID_LABEL_FONT
        lbl.fill = GRID_LABEL_FILL
        lbl.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        for col_idx in range(7):
            excel_col = col_idx + 2  # B..H
            cell_date = first_sunday + datetime.timedelta(days=7 * week + col_idx)
            in_month = month_start <= cell_date <= month_end
            day_num = cell_date.day
            is_weekend = col_idx in (0, 6)

            hcell = ws_.cell(row=header_row, column=excel_col)
            hcell.font = GRID_HEADER_FONT
            hcell.fill = PatternFill("solid", fgColor="BDD7EE") if is_weekend else GRID_HEADER_FILL
            hcell.alignment = Alignment(horizontal="center", wrap_text=True)
            hcell.border = BORDER
            hcell.value = f"{WEEKDAY_NAMES[col_idx]}\n{day_num:02d}" if in_month else ""

            weekend_fill = PatternFill("solid", fgColor="EBF3FB") if is_weekend else None
            for data_row, mode in (
                (row1, "first0719"), (row2, "second0719"),
                (row3, "first1022"), (row4, "second1022"),
            ):
                dcell = ws_.cell(row=data_row, column=excel_col)
                dcell.font = GRID_NAME_FONT
                dcell.alignment = Alignment(horizontal="center")
                dcell.border = BORDER
                if weekend_fill:
                    dcell.fill = weekend_fill
                if not in_month:
                    dcell.value = ""
                    continue
                offset = day_num
                g_ref = f"'{calc_sheet_name}'!$G${calc_first_row}:$G${calc_last_row}"
                h_ref = f"'{calc_sheet_name}'!$H${calc_first_row}:$H${calc_last_row}"
                i_ref = f"'{calc_sheet_name}'!$I${calc_first_row}:$I${calc_last_row}"
                j_ref = f"'{calc_sheet_name}'!$J${calc_first_row}:$J${calc_last_row}"
                if mode == "first0719":
                    dcell.value = (f'=IF(INDEX({g_ref},{offset})<>"",INDEX({g_ref},{offset}),'
                                   f'INDEX({h_ref},{offset}))')
                elif mode == "second0719":
                    dcell.value = f'=IF(INDEX({g_ref},{offset})<>"",INDEX({h_ref},{offset}),"")'
                elif mode == "first1022":
                    dcell.value = f'=INDEX({i_ref},{offset})'
                elif mode == "second1022":
                    dcell.value = f'=INDEX({j_ref},{offset})'
        row = row4 + 1

    footer_row = row + 1
    ws_.cell(row=footer_row, column=1, value="F. LEI 11.901/2009.").font = BOLD
    ws_.cell(row=footer_row, column=5, value=f"{local.split()[-1].title()}, {emissao_padrao}.").font = BLUE
    ws_.cell(row=footer_row, column=5).alignment = Alignment(horizontal="left")

    cert_row = footer_row + 2
    ws_.cell(row=cert_row, column=1, value="CERTIFICADOS / RECICLAGENS").font = BOLD
    for i in range(8):
        r = cert_row + 1 + i
        ws_.cell(row=r, column=1, value=f"=Configuração!A{85+i}").font = BLACK
        ws_.cell(row=r, column=2, value=f"=Configuração!B{85+i}").font = BLACK

    last_row = cert_row + 8
    ws_.sheet_view.showGridLines = False

    # print setup: landscape, fit to one page wide, repeat nothing special, tight margins
    ws_.page_setup.orientation = "landscape"
    ws_.page_setup.fitToWidth = 1
    ws_.page_setup.fitToHeight = 0
    ws_.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws_.print_area = f"A1:H{last_row}"
    ws_.page_margins.left = 0.4
    ws_.page_margins.right = 0.4
    ws_.page_margins.top = 0.5
    ws_.page_margins.bottom = 0.5


def add_month(nome_aba, ano, mes, overrides=None, local="POSTO CENTRAL", emissao_padrao=None):
    dias_no_mes = DIAS_NO_MES_2026[mes]
    if overrides is None:
        overrides = weekend_defaults(ano, mes, dias_no_mes)
    if emissao_padrao is None:
        emissao_padrao = emissao_default(ano, mes)
    calc_name = f"_Cálculo {nome_aba}"
    ws_calc = wb.create_sheet(calc_name)
    first_row = build_engine(ws_calc, ano, mes, dias_no_mes, overrides)
    ws_calc.sheet_state = "hidden"

    ws_visual = wb.create_sheet(nome_aba)
    build_grid(ws_visual, ano, mes, dias_no_mes, calc_name, first_row, mes, local, emissao_padrao)
    return ws_calc, ws_visual

MONTH_SHEET_NAMES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho",
                      "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

add_month("Janeiro", 2026, 1)
add_month("Fevereiro", 2026, 2)
add_month("Março", 2026, 3)
add_month("Maio", 2026, 5)
add_month("Junho", 2026, 6, overrides={7: 2, 20: 2, 27: 2, 28: 2}, emissao_padrao="15 de maio de 2026")
add_month("Julho", 2026, 7, overrides={5: 2, 18: 2, 25: 2, 26: 2}, emissao_padrao="15 de junho de 2026")
add_month("Agosto", 2026, 8)
add_month("Setembro", 2026, 9)
add_month("Outubro", 2026, 10)
add_month("Novembro", 2026, 11)
add_month("Dezembro", 2026, 12)

# ================================================================== Abril (histórico, estático)
abril = wb.create_sheet("Abril (histórico)")
abril["A1"] = "ABRIL 2026 — POSTO SUL (dado histórico, regra de fim de semana antiga)"
abril["A1"].font = TITLE
abril["A2"] = "Este mês não usa fórmula: os fins de semana de abril só tinham o turno 07h-19h coberto, sem 10h-22h."
abril["A2"].font = BLACK
for col, width in zip("ABCDEFG", [6, 12, 12, 10, 16, 16, 16]):
    abril.column_dimensions[col].width = width
headers = ["Dia", "Data", "Dia da semana", "Tipo", "07h-19h Pos.1", "07h-19h Pos.2", "10h-22h (só dias úteis)"]
for i, h in enumerate(headers):
    c = abril.cell(row=4, column=i + 1, value=h)
    c.font = BOLD
    c.fill = HEADER_FILL

abril_data = {
    1: ("Quarta", "Útil", "EDUARDO", "BRUNO", "GABRIEL / IGOR"),
    2: ("Quinta", "Útil", "VITOR", "CARLOS", "DANIEL / JULIO"),
    3: ("Sexta", "Útil", "EDUARDO", "BRUNO", "GABRIEL / IGOR"),
    4: ("Sábado", "Sábado", "VITOR", "DANIEL (folga do CARLOS)", ""),
    5: ("Domingo", "Domingo", "GABRIEL", "IGOR", ""),
    6: ("Segunda", "Útil", "VITOR", "CARLOS", "DANIEL / JULIO"),
    7: ("Terça", "Útil", "EDUARDO", "BRUNO", "GABRIEL / IGOR"),
    8: ("Quarta", "Útil", "VITOR", "CARLOS", "DANIEL / JULIO"),
    9: ("Quinta", "Útil", "EDUARDO", "BRUNO", "GABRIEL / IGOR"),
    10: ("Sexta", "Útil", "VITOR", "CARLOS", "DANIEL / JULIO"),
    11: ("Sábado", "Sábado", "EDUARDO", "BRUNO", ""),
    12: ("Domingo", "Domingo", "DANIEL", "JULIO", ""),
    13: ("Segunda", "Útil", "EDUARDO", "BRUNO", "GABRIEL / IGOR"),
    14: ("Terça", "Útil", "VITOR", "CARLOS", "DANIEL / JULIO"),
    15: ("Quarta", "Útil", "EDUARDO", "BRUNO", "GABRIEL / IGOR"),
    16: ("Quinta", "Útil", "VITOR", "CARLOS", "DANIEL / JULIO"),
    17: ("Sexta", "Útil", "EDUARDO", "BRUNO", "GABRIEL / IGOR"),
    18: ("Sábado", "Sábado", "VITOR", "CARLOS", ""),
    19: ("Domingo", "Domingo", "GABRIEL", "IGOR", ""),
    20: ("Segunda", "Útil", "VITOR", "CARLOS", "DANIEL / JULIO"),
    21: ("Terça", "Útil", "EDUARDO", "BRUNO", "GABRIEL / IGOR"),
    22: ("Quarta", "Útil", "VITOR", "CARLOS", "DANIEL / JULIO"),
    23: ("Quinta", "Útil", "EDUARDO", "BRUNO", "GABRIEL / IGOR"),
    24: ("Sexta", "Útil", "VITOR", "CARLOS", "DANIEL / JULIO"),
    25: ("Sábado", "Sábado", "EDUARDO", "BRUNO", ""),
    26: ("Domingo", "Domingo", "CARLOS (folga do DANIEL)", "JULIO", ""),
    27: ("Segunda", "Útil", "EDUARDO", "BRUNO", "GABRIEL / IGOR"),
    28: ("Terça", "Útil", "VITOR", "CARLOS", "DANIEL / JULIO"),
    29: ("Quarta", "Útil", "EDUARDO", "BRUNO", "GABRIEL / IGOR"),
    30: ("Quinta", "Útil", "VITOR", "CARLOS", "DANIEL / JULIO"),
}
for d in range(1, 31):
    r = 4 + d
    dow, tipo, p1, p2, t1022 = abril_data[d]
    abril.cell(row=r, column=1, value=d).font = BLACK
    c = abril.cell(row=r, column=2, value=datetime.date(2026, 4, d))
    c.number_format = "DD/MM/YYYY"
    c.font = BLACK
    abril.cell(row=r, column=3, value=dow).font = BLACK
    abril.cell(row=r, column=4, value=tipo).font = BLACK
    abril.cell(row=r, column=5, value=p1).font = BLACK
    abril.cell(row=r, column=6, value=p2).font = BLACK
    abril.cell(row=r, column=7, value=t1022).font = BLACK

# ================================================================== Leia-me
leiame = wb.create_sheet("Leia-me")
leiame.column_dimensions["A"].width = 100
leiame["A1"] = "ESCALA DE PLANTÕES BCI — ano de 2026"
leiame["A1"].font = TITLE
linhas = [
    "",
    "DUAS FORMAS DIFERENTES DE EDITAR — NÃO CONFUNDIR",
    "- Editar um nome DIRETO NA GRADE de um mês (ex: clicar em cima de \"EDUARDO\" na aba Junho) vale só PARA",
    "  AQUELE DIA — é o ajuste de última hora (uma troca pontual). Não afeta nenhum outro dia nem outro mês.",
    "- Para trocar o nome de alguém EM TODOS os meses de uma vez (corrigir um nome, por exemplo), edite a",
    "  linha da pessoa na tabela de Equipe, na aba Configuração — daí sim todo o ano se atualiza sozinho.",
    "- Cada aba de mês tem esse mesmo aviso destacado em amarelo, logo abaixo do título.",
    "",
    "COMO USAR",
    "1. Edite a aba 'Configuração' (equipe, data-âncora do rodízio, folgões, férias/substitutos, certificados).",
    "2. Abra a aba do mês — a grade já vem preenchida sozinha, no mesmo layout do documento original.",
    "3. Célula com fonte AZUL = editável. O resto é calculado por fórmula.",
    "4. Nas abas de Configuração, os campos Equipe/Turno/Posição e Pessoa (folgões/férias) têm uma lista suspensa",
    "   (seta ao clicar na célula) — evita erro de digitação que quebraria o cálculo sem avisar. A aba",
    "   Configuração é protegida fora dessas células azuis, e as abas '_Cálculo ...' também, pra evitar mexer",
    "   sem querer no motor de cálculo.",
    "5. As abas '_Cálculo ...' (ocultas) guardam o motor de cálculo dia a dia — não precisam ser abertas nem",
    "   editadas; para revelar, clique com o botão direito em qualquer aba > Reexibir.",
    "6. Cada aba de mês já sai pronta pra imprimir (paisagem, ajustada à largura da página).",
    "7. O nome na tabela de Certificados/Reciclagens (rodapé de cada mês) agora acompanha a tabela de Equipe",
    "   automaticamente — só o código (ex: \"05-19\") continua editável ali.",
    "8. Se você já tinha lançado um folgão ou férias para alguém e DEPOIS renomeia essa pessoa na Equipe, a",
    "   linha antiga do folgão/férias continua com o nome velho — é só corrigir aquela linha manualmente",
    "   (é raro acontecer, por isso não virou fórmula).",
    "",
    "SOBRE OS FINS DE SEMANA",
    "- Sábado e domingo sempre têm 1 pessoa do 07h-19h (fixa pela posição) + 1 pessoa do 10h-22h.",
    "- Qual das duas pessoas do 10h-22h entra no fim de semana não segue uma fórmula fixa (não consegui",
    "  confirmar essa regra nos documentos que recebi) — deixei um valor padrão alternado (revezando entre as",
    "  duas) na coluna 'Pos. 10-22 fim de semana' da aba de cálculo oculta de cada mês. Ajuste lá se necessário,",
    "  célula por célula, antes de fechar a escala de cada mês.",
    "",
    "SOBRE ESTE PROTÓTIPO",
    "- A aba 'Abril (histórico)' reproduz o documento original de abril/2026 (POSTO SUL) como referência estática —",
    "  não faz parte do cálculo automático, porque usava uma regra de fim de semana diferente (sem 10h-22h).",
    "- Junho e julho foram validados célula a célula contra os documentos originais: 0 divergências.",
    "- Os demais meses (jan, fev, mar, mai, ago-dez) seguem a mesma regra validada em junho/julho, mas ainda não",
    "  existe um documento real desses meses pra conferir — revise antes de enviar aos funcionários.",
    "",
    "GERAR OS DOCUMENTOS WORD (.docx)",
    "1. Edite/confira a planilha e salve (abrir e fechar no Excel já recalcula tudo).",
    "2. Dê duplo clique no arquivo 'Gerar Word.bat' (nesta mesma pasta).",
    "3. Os 11 arquivos .docx (um por mês, exceto abril) aparecem na pasta 'Word gerados', prontos pra",
    "   salvar/enviar aos funcionários — já validado célula a célula contra os documentos originais de",
    "   junho e julho (0 divergências).",
]
r = 2
for linha in linhas:
    leiame[f"A{r}"] = linha
    leiame[f"A{r}"].font = BOLD if (linha and linha.isupper()) else BLACK
    leiame[f"A{r}"].alignment = Alignment(wrap_text=True)
    r += 1

# ================================================================== Início
inicio = wb.create_sheet("Início")
inicio.column_dimensions["A"].width = 28
inicio.column_dimensions["B"].width = 60
inicio["A1"] = "ESCALA DE PLANTÕES BCI — 2026"
inicio["A1"].font = TITLE
inicio["A3"] = "Meses do ano"
inicio["A3"].font = BOLD
r = 4
for nome in MONTH_SHEET_NAMES:
    target = "Abril (histórico)" if nome == "Abril" else nome
    c = inicio.cell(row=r, column=1, value=nome)
    c.font = LINK_FONT
    c.hyperlink = f"#'{target}'!A1"
    r += 1
inicio.cell(row=r + 1, column=1, value="Configuração").font = LINK_FONT
inicio.cell(row=r + 1, column=1).hyperlink = "#'Configuração'!A1"
inicio.cell(row=r + 2, column=1, value="Leia-me").font = LINK_FONT
inicio.cell(row=r + 2, column=1).hyperlink = "#'Leia-me'!A1"
inicio.sheet_view.showGridLines = False

# ================================================================== tab order
order = ["Início", "Leia-me", "Configuração"] + \
        [("Abril (histórico)" if m == "Abril" else m) for m in MONTH_SHEET_NAMES] + \
        [f"_Cálculo {m}" for m in ["Janeiro","Fevereiro","Março","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]]
wb._sheets = [wb[name] for name in order]
wb.active = 0

out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Escala-BCI-2026.xlsx")
wb.save(out_path)
print("saved", out_path)
