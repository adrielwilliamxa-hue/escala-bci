# -*- coding: utf-8 -*-
"""Lock de arquivo pra proteger o padrão ler-modificar-gravar dos JSONs de
dados (dados.json e postos/*.json) contra corrupção por escrita concorrente
-- duas requisições HTTP simultâneas no mesmo arquivo, ou o dev server em
modo debug com dois processos. Não migra pra banco de dados, só serializa
o acesso ao arquivo. Depende de `filelock` (pip install filelock)."""
import os

from filelock import FileLock

_TIMEOUT_SEGUNDOS = 10


def lock_para(caminho_dados):
    """Retorna um FileLock ligado a `caminho_dados` -- usar como context
    manager envolvendo TODA a seção ler+modificar+gravar, não só a
    gravação, senão duas requisições podem ler o mesmo estado velho e uma
    sobrescrever a mudança da outra."""
    return FileLock(caminho_dados + ".lock", timeout=_TIMEOUT_SEGUNDOS)
