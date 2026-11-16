# -*- mode: python ; coding: utf-8 -*-
# Empacota o site da Escala BCI num unico "Escala BCI.exe" (PyInstaller).
# Reconstruir: duplo-clique em "Construir Exe.bat" (ou: python -m PyInstaller escala-bci.spec --noconfirm)

a = Analysis(
    ["site/app.py"],
    pathex=["scripts"],
    binaries=[],
    datas=[
        ("site/templates", "templates"),
        ("site/static", "static"),
        # semente (dados ficticios de demonstracao): copiada pro lado do exe na 1a execucao
        ("dados.example.json", "seed"),
        # logo Escala BCI usada no cabecalho dos Word gerados
        ("scripts/assets", "assets"),
    ],
    hiddenimports=["regra_rodizio", "gerar_word", "motor", "postos", "gerar_xlsx_posto"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Escala BCI Multi-Postos",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="scripts/assets/icone-escala-bci.ico",
)
