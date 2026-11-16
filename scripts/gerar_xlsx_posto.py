# -*- coding: utf-8 -*-
"""Exportador de planilha (.xlsx) de LEITURA para qualquer posto cadastrado
-- uma aba por mes, sem formulas nem validacao manual (diferente de
gerar_planilha.py, que monta a planilha mestre editavel do CENTRAL e nao e
usada pelo site). Fonte dos dados: scripts/motor.py, o mesmo motor usado
pelo gerar_word.py e pelo site."""
import calendar
import os

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

import motor as motor_mod

MES_NOMES = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho",
             "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

HEADER_FILL = PatternFill("solid", fgColor="D9E1F2")
HEADER_FONT = Font(bold=True)
TITLE_FONT = Font(bold=True, size=14)


def gerar_xlsx_ano_posto(posto, ano, out_dir):
    """Gera um .xlsx com uma aba por mes do ano, cada aba com uma linha por
    dia e uma coluna por (turno, posicao)."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    colunas = []
    for turno in posto["turnos"]:
        for p in range(1, turno["n_posicoes"] + 1):
            colunas.append(f"{turno['id']} pos{p}")

    for mes in range(1, 13):
        ws = wb.create_sheet(MES_NOMES[mes][:31])
        ws["A1"] = f"{posto['posto_nome']} — {MES_NOMES[mes]} de {ano}"
        ws["A1"].font = TITLE_FONT

        ws.cell(row=3, column=1, value="Dia").font = HEADER_FONT
        ws.cell(row=3, column=2, value="Data").font = HEADER_FONT
        for c, nome_col in enumerate(colunas):
            cell = ws.cell(row=3, column=3 + c, value=nome_col)
            cell.font = HEADER_FONT
            cell.fill = HEADER_FILL

        overrides_fds = posto.get("overrides_fds", {})
        dias = motor_mod.computar_mes_generico(posto, ano, mes, overrides_fds)
        for r, d in enumerate(dias):
            row = 4 + r
            ws.cell(row=row, column=1, value=d["dia"])
            ws.cell(row=row, column=2, value=d["data"])
            col = 3
            for turno in posto["turnos"]:
                for valor in d["turnos"][turno["id"]]["valores"]:
                    ws.cell(row=row, column=col, value=valor)
                    col += 1

        ws.column_dimensions["A"].width = 6
        ws.column_dimensions["B"].width = 12
        for i in range(len(colunas)):
            ws.column_dimensions[openpyxl.utils.get_column_letter(3 + i)].width = 16

    os.makedirs(out_dir, exist_ok=True)
    nome_arquivo = f"Escala {posto['posto_nome']} {ano}.xlsx"
    out_path = os.path.join(out_dir, nome_arquivo)
    wb.save(out_path)
    return out_path
