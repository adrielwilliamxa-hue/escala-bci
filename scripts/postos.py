# -*- coding: utf-8 -*-
"""Persistência de postos de trabalho -- cada posto é um arquivo JSON
isolado em postos/<slug>.json, sem nenhum estado compartilhado entre
postos. CRUD simples (listar/ler/salvar/excluir); o cálculo da escala em
si é sempre feito por scripts/motor.py, nunca aqui."""
import json
import os
import re
import uuid

POSTOS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "postos")


def configurar_dir(caminho):
    """Troca onde os postos são lidos/gravados -- usado pelo app.py quando
    rodando empacotado (.exe), onde __file__ aponta pra pasta temporária do
    PyInstaller em vez de um lugar persistente ao lado do executável."""
    global POSTOS_DIR
    POSTOS_DIR = caminho


def _slugify(nome):
    slug = re.sub(r"[^a-z0-9]+", "-", nome.lower()).strip("-")
    return slug or uuid.uuid4().hex[:8]


def _caminho(slug):
    return os.path.join(POSTOS_DIR, f"{slug}.json")


def listar_postos():
    os.makedirs(POSTOS_DIR, exist_ok=True)
    postos = []
    for nome_arquivo in sorted(os.listdir(POSTOS_DIR)):
        if nome_arquivo.endswith(".json"):
            slug = nome_arquivo[:-5]
            postos.append(carregar_posto(slug))
    return postos


def carregar_posto(slug):
    with open(_caminho(slug), encoding="utf-8") as f:
        dados = json.load(f)
    precisa_salvar = False
    for lista in (dados.get("ferias", []), dados.get("folgas", [])):
        for item in lista:
            if not item.get("id"):
                item["id"] = uuid.uuid4().hex[:8]
                precisa_salvar = True
    if precisa_salvar:
        salvar_posto(dados, slug=slug)
    dados["slug"] = slug
    return dados


def existe_posto(slug):
    return os.path.exists(_caminho(slug))


def salvar_posto(dados, slug=None):
    """Salva o posto; se `slug` não vier, gera um novo a partir do nome
    (posto novo). Retorna o slug usado."""
    os.makedirs(POSTOS_DIR, exist_ok=True)
    if slug is None:
        base = _slugify(dados["posto_nome"])
        slug = base
        i = 2
        while existe_posto(slug):
            slug = f"{base}-{i}"
            i += 1
    dados_para_salvar = {k: v for k, v in dados.items() if k != "slug"}
    with open(_caminho(slug), "w", encoding="utf-8") as f:
        json.dump(dados_para_salvar, f, ensure_ascii=False, indent=2)
    return slug


def excluir_posto(slug):
    caminho = _caminho(slug)
    if os.path.exists(caminho):
        os.remove(caminho)
