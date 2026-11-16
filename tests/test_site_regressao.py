# -*- coding: utf-8 -*-
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import regra_rodizio as rr

DADOS = rr.carregar_dados(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dados.example.json"))

# escala de cada dia (pos_0719_1, pos_0719_2, pos_1022_1, pos_1022_2). Fins de
# semana seguem a alternância automática simples (1,2,1,2...), confirmada como
# regra correta contra o documento original de agosto/2026 -- os overrides
# manuais de Junho/Julho que existiam antes eram dado errado, removidos de
# dados.json.
JUNHO_ESPERADO = {
    1: ("VITOR", "CARLOS", "DANIEL", "JULIO"),
    2: ("EDUARDO", "BRUNO", "GABRIEL", "IGOR"),
    3: ("VITOR", "CARLOS", "DANIEL", "JULIO"),
    4: ("EDUARDO", "BRUNO", "GABRIEL", "IGOR"),
    5: ("VITOR", "CARLOS", "DANIEL", "JULIO"),
    6: ("EDUARDO", "", "IGOR", ""),
    7: ("", "CARLOS", "DANIEL", ""),
    8: ("EDUARDO", "BRUNO", "GABRIEL", "IGOR"),
    9: ("VITOR", "CARLOS", "DANIEL", "JULIO"),
    10: ("EDUARDO", "BRUNO", "GABRIEL", "IGOR"),
    11: ("VITOR", "CARLOS", "DANIEL", "JULIO"),
    12: ("EDUARDO", "BRUNO", "GABRIEL", "IGOR"),
    13: ("VITOR", "", "JULIO", ""),
    14: ("", "BRUNO", "GABRIEL", ""),
    15: ("VITOR", "CARLOS", "DANIEL", "JULIO"),
    16: ("EDUARDO", "BRUNO", "GABRIEL", "IGOR"),
    17: ("VITOR", "CARLOS", "DANIEL", "JULIO"),
    18: ("EDUARDO", "BRUNO", "GABRIEL", "IGOR"),
    19: ("VITOR", "CARLOS", "DANIEL", "JULIO"),
    20: ("EDUARDO", "", "IGOR", ""),
    21: ("", "CARLOS", "DANIEL", ""),
    22: ("EDUARDO", "BRUNO", "GABRIEL", "IGOR"),
    23: ("VITOR", "CARLOS", "DANIEL", "JULIO"),
    24: ("EDUARDO", "BRUNO", "GABRIEL", "IGOR"),
    25: ("VITOR", "CARLOS", "DANIEL", "JULIO"),
    26: ("EDUARDO", "BRUNO", "GABRIEL", "IGOR"),
    27: ("VITOR", "", "JULIO", ""),
    28: ("", "BRUNO", "GABRIEL", ""),
    29: ("VITOR", "CARLOS", "DANIEL", "JULIO"),
    30: ("EDUARDO", "BRUNO", "GABRIEL", "IGOR"),
}

JULHO_ESPERADO = {
    1: ("VITOR", "CARLOS", "DANIEL", "JULIO"),
    2: ("EDUARDO", "BRUNO", "GABRIEL", "IGOR"),
    3: ("VITOR", "CARLOS", "DANIEL", "JULIO"),
    4: ("EDUARDO", "", "IGOR", ""),
    5: ("", "CARLOS", "DANIEL", ""),
    6: ("EDUARDO", "BRUNO", "GABRIEL", "IGOR"),
    7: ("VITOR", "CARLOS", "DANIEL", "JULIO"),
    8: ("EDUARDO", "BRUNO", "GABRIEL", "IGOR"),
    9: ("VITOR", "CARLOS", "DANIEL", "JULIO"),
    10: ("EDUARDO", "BRUNO", "GABRIEL", "IGOR"),
    11: ("VITOR", "", "JULIO", ""),
    12: ("", "BRUNO", "GABRIEL", ""),
    13: ("VITOR", "CARLOS", "DANIEL", "JULIO"),
    14: ("EDUARDO", "BRUNO", "GABRIEL", "IGOR"),
    15: ("VITOR", "CARLOS", "HUGO", "JULIO"),
    16: ("EDUARDO", "BRUNO", "GABRIEL", "IGOR"),
    17: ("VITOR", "CARLOS", "HUGO", "JULIO"),
    18: ("EDUARDO", "", "IGOR", ""),
    19: ("", "CARLOS", "HUGO", ""),
    20: ("EDUARDO", "BRUNO", "GABRIEL", "IGOR"),
    21: ("VITOR", "CARLOS", "HUGO", "JULIO"),
    22: ("EDUARDO", "BRUNO", "GABRIEL", "IGOR"),
    23: ("VITOR", "CARLOS", "HUGO", "JULIO"),
    24: ("EDUARDO", "BRUNO", "GABRIEL", "IGOR"),
    25: ("VITOR", "", "JULIO", ""),
    26: ("", "BRUNO", "GABRIEL", ""),
    27: ("VITOR", "CARLOS", "HUGO", "JULIO"),
    28: ("EDUARDO", "BRUNO", "GABRIEL", "IGOR"),
    29: ("VITOR", "CARLOS", "HUGO", "JULIO"),
    30: ("EDUARDO", "BRUNO", "GABRIEL", "IGOR"),
    31: ("VITOR", "CARLOS", "HUGO", "JULIO"),
}


def _tupla_do_dia(dia_calculado):
    return (dia_calculado["pos_0719_1"], dia_calculado["pos_0719_2"],
            dia_calculado["pos_1022_1"], dia_calculado["pos_1022_2"])


def test_junho_bate_com_documento_original_dia_a_dia():
    dias = rr.computar_mes(DADOS, 2026, 6)
    for dia in dias:
        esperado = JUNHO_ESPERADO[dia["dia"]]
        calculado = _tupla_do_dia(dia)
        assert calculado == esperado, f"Junho dia {dia['dia']}: esperado {esperado}, calculado {calculado}"


def test_julho_bate_com_documento_original_dia_a_dia():
    dias = rr.computar_mes(DADOS, 2026, 7)
    for dia in dias:
        esperado = JULHO_ESPERADO[dia["dia"]]
        calculado = _tupla_do_dia(dia)
        assert calculado == esperado, f"Julho dia {dia['dia']}: esperado {esperado}, calculado {calculado}"


def test_julho_15_em_diante_mostra_hugo_no_lugar_de_daniel():
    dias = rr.computar_mes(DADOS, 2026, 7)
    for dia in dias:
        if dia["dia"] < 15:
            continue
        pessoas = {v for v in _tupla_do_dia(dia) if v}
        assert "DANIEL" not in pessoas, f"Julho dia {dia['dia']}: DANIEL não deveria aparecer (está de férias)"
