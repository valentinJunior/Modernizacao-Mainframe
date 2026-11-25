#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inventario_mainframe.py

Le os fontes legados (JCL, COBOL e copybooks) de uma pasta e monta um
inventario estruturado em JSON e Markdown.

Duas camadas, de proposito separadas:
  1. FATOS  - parser proprio, deterministico: steps, DDs, datasets, CALLs,
              COPYs, layouts, posicoes e tamanhos. Rodou duas vezes, sai igual.
  2. IA     - modelo local no Ollama, so para interpretar: resumo de negocio,
              regras e riscos. Nenhum fonte sai da maquina.

Se o Ollama nao estiver no ar, o inventario de fatos sai do mesmo jeito.

Uso:
    python3 inventario_mainframe.py --fontes legado --saida saida
    python3 inventario_mainframe.py --fontes legado --sem-ia
    python3 inventario_mainframe.py --modelo qwen2.5:14b

Autor : Jair Valentin
Data  : 2026-11
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

VERSAO = "1.0"
OLLAMA_URL_PADRAO = "http://localhost:11434"
MODELO_PADRAO = "qwen2.5:7b"
LIMITE_FONTE_IA = 15000  # caracteres do fonte enviados ao modelo

EXTENSOES = {
    ".jcl": "jcl",
    ".cbl": "cobol",
    ".cob": "cobol",
    ".cpy": "copybook",
}

PGMS_SORT = {"SORT", "ICEMAN", "SYNCSORT", "DFSORT"}
PGMS_TSO = {"IKJEFT01", "IKJEFT1A", "IKJEFT1B"}
UTILITARIOS = {
    "ICETOOL": "ICETOOL (DFSORT)",
    "IDCAMS": "IDCAMS (VSAM / catalogo)",
    "IEBGENER": "Copia sequencial (IEBGENER)",
    "IEBCOPY": "Copia de PDS (IEBCOPY)",
    "IEFBR14": "Alocacao / delecao (IEFBR14)",
    "DSNUTILB": "Utilitario DB2 (DSNUTILB)",
    "ADRDSSU": "Backup / restore (DFSMSdss)",
}
VERBOS_SORT = {
    "INCLUDE", "OMIT", "SORT", "MERGE", "SUM", "INREC", "OUTREC", "OUTFIL",
    "OPTION", "RECORD", "END", "ALTSEQ", "JOINKEYS", "REFORMAT", "JOIN",
}
DDS_BIBLIOTECA = {"STEPLIB", "JOBLIB", "SYSPROC", "SYSEXEC"}
RE_DATA_ISO = r"\d{4}-\d{2}-\d{2}"
ORDEM_SEVERIDADE = {"alta": 0, "media": 1, "baixa": 2, "info": 3}


# =============================================================================
# Utilitarios gerais
# =============================================================================

def log(msg):
    print(f"[inventario] {msg}", file=sys.stderr)


def caminho_relativo(p):
    try:
        return os.path.relpath(p)
    except ValueError:
        return str(p)


def achado(severidade, componente, descricao):
    return {"severidade": severidade, "componente": componente,
            "descricao": descricao}


def separar_operandos(texto):
    """Separa por virgula respeitando parenteses e apostrofos."""
    partes, atual, nivel, aspas = [], "", 0, False
    for c in texto:
        if c == "'":
            aspas = not aspas
        elif not aspas:
            if c == "(":
                nivel += 1
            elif c == ")":
                nivel -= 1
            elif c == "," and nivel == 0:
                partes.append(atual)
                atual = ""
                continue
        atual += c
    if atual:
        partes.append(atual)
    return partes


def campo_operandos(texto):
    """Pega o campo de operandos: vai ate o primeiro espaco fora de aspas.
    O que vem depois e comentario (vale para JCL e para SYSIN do SORT)."""
    aspas = False
    for i, c in enumerate(texto):
        if c == "'":
            aspas = not aspas
        elif c == " " and not aspas:
            return texto[:i]
    return texto


def interpretar_operandos(texto):
    """'PGM=X,PARM='A',COND=(4,LT)' -> (posicionais, {chave: valor})."""
    posicionais, chaves = [], {}
    for parte in separar_operandos(texto):
        parte = parte.strip()
        if not parte:
            continue
        if "=" in parte and not parte.startswith("'") and not parte.startswith("("):
            k, v = parte.split("=", 1)
            chaves[k.upper()] = v
        else:
            posicionais.append(parte)
    return posicionais, chaves


def tirar_aspas(v):
    if v and len(v) >= 2 and v[0] == "'" and v[-1] == "'":
        return v[1:-1]
    return v


def tirar_parenteses(v):
    if v and v.startswith("(") and v.endswith(")"):
        return v[1:-1]
    return v


RE_CHAVE_CAB = re.compile(r"^([A-Z][A-Z .\-]{1,13}?)\s*:\s*(.*)$")
RE_HISTORICO = re.compile(r"^\s*(\d{4}-\d{2}-\d{2})\s+(\S+)\s+(.+)$")
RE_REGRA = re.compile(r"^\s*(RN\d+)\s*-\s*(.+)$")
RE_CODIGO = re.compile(r"^\s*(\d{2}(?:\s+A\s+\d{2})?)\s+-\s+(.+)$")


def ler_cabecalho(comentarios):
    """Le blocos do tipo 'CHAVE : valor' (com continuacao indentada)
    que a gente usa no cabecalho de JCL, programa e copybook."""
    cab, chave = {}, None
    for txt in comentarios:
        bruto = txt.rstrip()
        limpo = bruto.strip()
        if not limpo or set(limpo) <= set("-=*"):
            chave = None
            continue
        recuo = len(bruto) - len(bruto.lstrip())
        m = RE_CHAVE_CAB.match(limpo)
        if m and recuo <= 2:
            chave = re.sub(r"[^a-z0-9]+", "_", m.group(1).strip().lower()).strip("_")
            cab[chave] = m.group(2).strip()
        elif chave and recuo > 2:
            cab[chave] = (cab[chave] + " " + limpo).strip()
        else:
            chave = None
    return cab


def ler_listas_documentadas(comentarios):
    """Historico de alteracoes, regras RNxx e codigos 'NN - descricao'."""
    historico, regras, codigos = [], [], []
    regra_atual = None
    for txt in comentarios:
        limpo = txt.strip()
        m = RE_HISTORICO.match(txt)
        if m:
            historico.append({"data": m.group(1), "autor": m.group(2),
                              "descricao": m.group(3).strip()})
            regra_atual = None
            continue
        m = RE_REGRA.match(txt)
        if m:
            regra_atual = {"id": m.group(1), "descricao": m.group(2).strip()}
            regras.append(regra_atual)
            continue
        m = RE_CODIGO.match(txt)
        if m:
            codigos.append({"codigo": m.group(1), "descricao": m.group(2).strip()})
            regra_atual = None
            continue
        if regra_atual and limpo and not set(limpo) <= set("-=*"):
            regra_atual["descricao"] += " " + limpo
        else:
            regra_atual = None
    return historico, regras, codigos


# =============================================================================
# COBOL - leitura do formato fixo
# =============================================================================

def ler_fonte_cobol(texto):
    """Separa linhas de codigo (colunas 8-72) e de comentario (indicador * ou /)."""
    codigo, comentarios = [], []
    for n, bruto in enumerate(texto.splitlines(), 1):
        linha = bruto.ljust(8)
        indicador = linha[6]
        area = linha[7:72]
        if indicador in "*/":
            comentarios.append((n, area))
        elif indicador in "dD":
            continue  # linha de debug
        else:
            codigo.append((n, area))
    return codigo, comentarios


def texto_plano(codigo):
    corpo = " ".join(area for _, area in codigo)
    return re.sub(r"\s+", " ", corpo).upper()


# =============================================================================
# Copybook - layout, posicoes e tamanhos
# =============================================================================

RE_ITEM = re.compile(r"^(\d{1,2})\s+([A-Z0-9][A-Z0-9-]*)\s*(.*)$")
RE_PIC = re.compile(r"\bPIC(?:TURE)?\s+(?:IS\s+)?(\S+)")
RE_USO = re.compile(r"\b(COMP-3|COMP-4|COMP-5|COMP-1|COMP-2|COMPUTATIONAL-3|"
                    r"COMP|BINARY|PACKED-DECIMAL)\b")
RE_OCCURS = re.compile(r"\bOCCURS\s+(?:(\d+)\s+TO\s+)?(\d+)")
RE_REDEFINES = re.compile(r"\bREDEFINES\s+([A-Z0-9-]+)")


def expandir_pic(pic):
    return re.sub(r"(.)\((\d+)\)", lambda m: m.group(1) * int(m.group(2)), pic)


def tamanho_pic(pic, uso):
    p = expandir_pic(pic.upper())
    digitos = p.count("9")
    if uso in ("COMP-3", "COMPUTATIONAL-3", "PACKED-DECIMAL"):
        return digitos // 2 + 1
    if uso in ("COMP", "COMP-4", "COMP-5", "BINARY"):
        return 2 if digitos <= 4 else 4 if digitos <= 9 else 8
    if uso == "COMP-1":
        return 4
    if uso == "COMP-2":
        return 8
    return len(p.replace("S", "").replace("V", ""))


def formato_campo(pic, uso):
    if not pic:
        return "grupo"
    if uso in ("COMP-3", "COMPUTATIONAL-3", "PACKED-DECIMAL"):
        return f"PD {pic}"
    if uso in ("COMP", "COMP-4", "COMP-5", "BINARY"):
        return f"BI {pic}"
    p = pic.upper()
    if "X" in p or "A" in p:
        return f"CH {pic}"
    if re.fullmatch(r"S?[9()\dV]+", p):
        return f"ZD {pic}"
    return f"EDITADO {pic}"


def montar_arvore(sentencas):
    raizes, pilha, ultimo = [], [], None
    for s in sentencas:
        m = RE_ITEM.match(s)
        if not m:
            continue
        nivel, nome, resto = int(m.group(1)), m.group(2), m.group(3)
        if nivel == 88:
            if ultimo is not None:
                valor = re.sub(r"^VALUES?\s+(?:ARE\s+|IS\s+)?", "", resto).strip()
                ultimo["condicoes"].append({"nome": nome, "valor": valor})
            continue
        if nivel == 66:
            continue
        pic = RE_PIC.search(resto)
        uso = RE_USO.search(resto)
        occ = RE_OCCURS.search(resto)
        red = RE_REDEFINES.search(resto)
        item = {
            "nivel": nivel, "nome": nome,
            "pic": pic.group(1) if pic else None,
            "uso": uso.group(1) if uso else None,
            "occurs": int(occ.group(2)) if occ else None,
            "occurs_variavel": bool(occ and occ.group(1)),
            "redefines": red.group(1) if red else None,
            "condicoes": [], "filhos": [],
        }
        while pilha and pilha[-1]["nivel"] >= nivel:
            pilha.pop()
        (pilha[-1]["filhos"] if pilha else raizes).append(item)
        pilha.append(item)
        ultimo = item
    return raizes


def calcular_tamanho(item):
    if item["filhos"]:
        base = sum(calcular_tamanho(f) for f in item["filhos"] if not f["redefines"])
    elif item["pic"]:
        base = tamanho_pic(item["pic"], item["uso"])
    else:
        base = 0
    item["tamanho"] = base
    item["tamanho_total"] = base * (item["occurs"] or 1)
    return item["tamanho_total"]


def calcular_posicoes(item, inicio):
    item["pos"] = inicio
    atual = inicio
    irmaos = {}
    for f in item["filhos"]:
        if f["redefines"] and f["redefines"] in irmaos:
            calcular_posicoes(f, irmaos[f["redefines"]])
        else:
            calcular_posicoes(f, atual)
            atual += f["tamanho_total"]
        irmaos[f["nome"]] = f["pos"]


def achatar(item, saida):
    saida.append({
        "nivel": item["nivel"], "nome": item["nome"], "pos": item["pos"],
        "tamanho": item["tamanho_total"],
        "formato": formato_campo(item["pic"], item["uso"]),
        "pic": item["pic"], "uso": item["uso"] or ("DISPLAY" if item["pic"] else None),
        "occurs": item["occurs"], "redefines": item["redefines"],
        "condicoes": item["condicoes"],
    })
    for f in item["filhos"]:
        achatar(f, saida)


def analisar_copybook(caminho):
    texto = caminho.read_text(encoding="latin-1")
    codigo, comentarios = ler_fonte_cobol(texto)
    plano = texto_plano(codigo)
    sentencas = [s.strip() for s in re.split(r"\.(?=\s|$)", plano) if s.strip()]

    raizes = montar_arvore(sentencas)
    campos, tamanho = [], 0
    for r in raizes:
        calcular_tamanho(r)
        calcular_posicoes(r, 1)
        achatar(r, campos)
        tamanho = max(tamanho, r["tamanho_total"])

    txt_coment = [t for _, t in comentarios]
    cab = ler_cabecalho(txt_coment)
    _, _, codigos = ler_listas_documentadas(txt_coment)
    lrecl = re.search(r"LRECL\s*:\s*(\d+)", " ".join(txt_coment))

    return {
        "nome": caminho.stem.upper(),
        "arquivo": caminho_relativo(caminho),
        "descricao": cab.get("descricao", ""),
        "registros": [r["nome"] for r in raizes],
        "tamanho_calculado": tamanho,
        "lrecl_documentado": int(lrecl.group(1)) if lrecl else None,
        "quantidade_campos": sum(1 for c in campos if c["pic"]),
        "campos": campos,
        "codigos_documentados": codigos,
        "usado_por": [],
    }


# =============================================================================
# Programa COBOL
# =============================================================================

PALAVRAS_FIM_CALL = {"ON", "END-CALL", "NOT", "OVERFLOW", "EXCEPTION", "IF",
                     "MOVE", "PERFORM", "DISPLAY", "ELSE", "END-IF", "GOBACK"}


def secao_de(posicao, marcos):
    atual = "IDENTIFICATION"
    for nome, pos in marcos:
        if pos != -1 and posicao >= pos:
            atual = nome
    return atual


def analisar_cobol(caminho):
    texto = caminho.read_text(encoding="latin-1")
    codigo, comentarios = ler_fonte_cobol(texto)
    plano = texto_plano(codigo)
    linhas = texto.splitlines()

    def buscar(padrao):
        m = re.search(padrao, plano)
        return m.group(1).strip() if m else None

    programa = buscar(r"PROGRAM-ID\.\s*([A-Z0-9-]+)") or caminho.stem.upper()

    # cabecalho = comentarios antes da ENVIRONMENT DIVISION
    linha_env = next((n for n, a in codigo if "ENVIRONMENT DIVISION" in a.upper()), 10**9)
    cab = ler_cabecalho([t for n, t in comentarios if n < linha_env])
    historico, regras, codigos = ler_listas_documentadas([t for _, t in comentarios])

    marcos = [
        ("FILE", plano.find("FILE SECTION")),
        ("WORKING-STORAGE", plano.find("WORKING-STORAGE SECTION")),
        ("LINKAGE", plano.find("LINKAGE SECTION")),
        ("PROCEDURE", plano.find("PROCEDURE DIVISION")),
    ]

    # --- arquivos (SELECT / FD) ---------------------------------------------
    arquivos = []
    for m in re.finditer(r"SELECT (?:OPTIONAL )?([A-Z0-9-]+) ASSIGN (?:TO )?([A-Z0-9-]+)(.*?)\.", plano):
        assign = m.group(2)
        ddname = assign.split("-")[-1] if re.match(r"^(UT|DA|S)-", assign) else assign
        resto = m.group(3)
        org = re.search(r"ORGANIZATION (?:IS )?(\w+)", resto)
        status = re.search(r"FILE STATUS (?:IS )?([A-Z0-9-]+)", resto)
        arquivos.append({
            "arquivo_logico": m.group(1), "ddname": ddname,
            "organizacao": org.group(1) if org else "SEQUENTIAL",
            "file_status": status.group(1) if status else None,
            "copybook": None, "modo_abertura": [],
        })
    por_logico = {a["arquivo_logico"]: a for a in arquivos}

    ini_fs, fim_fs = marcos[0][1], marcos[1][1]
    if ini_fs != -1:
        trecho = plano[ini_fs:fim_fs if fim_fs != -1 else None]
        for bloco in re.split(r"\bFD\s+", trecho)[1:]:
            nome_fd = bloco.split()[0].rstrip(".")
            cp = re.search(r"\bCOPY\s+([A-Z0-9-]+)", bloco)
            if nome_fd in por_logico and cp:
                por_logico[nome_fd]["copybook"] = cp.group(1)

    for m in re.finditer(r"\bOPEN ((?:(?:INPUT|OUTPUT|I-O|EXTEND) (?:[A-Z0-9-]+ ?)+)+)", plano):
        modo = None
        for tok in m.group(1).split():
            if tok in ("INPUT", "OUTPUT", "I-O", "EXTEND"):
                modo = tok
            elif tok in por_logico and modo:
                if modo not in por_logico[tok]["modo_abertura"]:
                    por_logico[tok]["modo_abertura"].append(modo)
            else:
                break

    # --- COPY ---------------------------------------------------------------
    copys = []
    for m in re.finditer(r"\bCOPY\s+([A-Z0-9-]+)", plano):
        copys.append({"copybook": m.group(1), "secao": secao_de(m.start(), marcos)})

    # --- CALL ---------------------------------------------------------------
    chamadas = []
    for m in re.finditer(r"(?<![A-Z0-9-])CALL ('?)([A-Z0-9-]+)\1", plano):
        dinamico = m.group(1) == ""
        alvo = m.group(2)
        variavel = None
        if dinamico:
            variavel = alvo
            v = re.search(rf"\b{re.escape(alvo)} PIC [^ ]+ VALUE '([^']+)'", plano)
            alvo = v.group(1).strip() if v else None
        parametros = []
        depois = plano[m.end():].split()
        if depois and depois[0] == "USING":
            for bruto in depois[1:]:
                tok = bruto.rstrip(".,")
                if tok in PALAVRAS_FIM_CALL or not tok:
                    break
                if tok not in ("BY", "REFERENCE", "CONTENT", "VALUE"):
                    parametros.append(tok)
                if bruto.endswith("."):
                    break
        chamadas.append({"programa": alvo, "dinamico": dinamico,
                         "variavel": variavel, "parametros": parametros})

    # --- PROCEDURE ----------------------------------------------------------
    using = re.search(r"PROCEDURE DIVISION(?: USING ([A-Z0-9- ]+?))?\s*\.", plano)
    parametros_entrada = using.group(1).split() if using and using.group(1) else []

    paragrafos, dentro = [], False
    for _, area in codigo:
        if "PROCEDURE DIVISION" in area.upper():
            dentro = True
            continue
        if dentro and area[:1] not in (" ", ""):
            m = re.match(r"^([A-Z0-9][A-Z0-9-]*)(?: SECTION)?\.\s*$", area.strip().upper())
            if m:
                paragrafos.append(m.group(1))
    performs = set(re.findall(r"(?<![A-Z0-9-])PERFORM ([A-Z0-9][A-Z0-9-]*)", plano))
    nao_referenciados = [p for p in paragrafos[1:] if p not in performs]

    return_codes = sorted({int(x) for x in re.findall(r"MOVE (\d+) TO RETURN-CODE", plano)})

    tabelas_sql = sorted({t for bloco in re.findall(r"EXEC SQL(.*?)END-EXEC", plano)
                          for t in re.findall(r"\b(?:FROM|JOIN|INTO|UPDATE)\s+([A-Z0-9_.]+)", bloco)})
    comandos_cics = sorted(set(re.findall(r"EXEC CICS (\w+)", plano)))

    tabelas_internas = [
        {"nome": m.group(1), "maximo": int(m.group(3)), "variavel": bool(m.group(2))}
        for m in re.finditer(r"\d\d ([A-Z0-9-]+) OCCURS (?:(\d+) TO )?(\d+)", plano)
    ]

    total = len(linhas)
    n_coment = len(comentarios)
    n_codigo = sum(1 for _, a in codigo if a.strip())

    tem_linkage = marcos[2][1] != -1
    tipo = "subrotina" if (parametros_entrada and tem_linkage and not arquivos) else "batch"

    return {
        "programa": programa,
        "arquivo": caminho_relativo(caminho),
        "tipo": tipo,
        "autor": buscar(r"AUTHOR\.\s*([^.]+)\."),
        "data_criacao": buscar(r"DATE-WRITTEN\.\s*([^ ]+?)\.(?:\s|$)"),
        "objetivo": cab.get("objetivo", ""),
        "cabecalho": cab,
        "historico": historico,
        "regras_documentadas": regras,
        "codigos_documentados": codigos,
        "arquivos": arquivos,
        "copybooks": copys,
        "chamadas": chamadas,
        "chamado_por": [],
        "executado_em": [],
        "parametros_entrada": parametros_entrada,
        "paragrafos": paragrafos,
        "paragrafos_nao_referenciados": nao_referenciados,
        "return_codes": return_codes,
        "tabelas_sql": tabelas_sql,
        "comandos_cics": comandos_cics,
        "tabelas_internas": tabelas_internas,
        "termino": [t for t in ("GOBACK", "STOP RUN") if t in plano],
        "metricas": {"linhas_total": total, "linhas_codigo": n_codigo,
                     "linhas_comentario": n_coment,
                     "percentual_comentario": round(100 * n_coment / total, 1) if total else 0},
        "_plano": plano,  # usado nas verificacoes, removido antes de gravar
        "_sem_literais": re.sub(r"'[^']*'", "''", plano),
    }


# =============================================================================
# JCL
# =============================================================================

def ler_comandos_jcl(texto):
    """Monta as instrucoes logicas do JCL (juntando continuacoes)
    e pendura os dados instream na DD que os recebe."""
    instrucoes, comentarios = [], []
    pendente, instream = None, None

    for n, bruto in enumerate(texto.splitlines(), 1):
        linha = bruto.rstrip()

        if instream is not None:
            if linha.startswith("/*"):
                instream = None
                continue
            if linha.startswith("//"):
                instream = None
            else:
                instream["dados"].append(linha)
                continue

        if linha.startswith("//*"):
            comentarios.append((n, linha[3:]))
            continue
        if not linha.startswith("//"):
            continue

        conteudo = linha[2:71]
        if not conteudo.strip():
            continue  # '//' = fim do job

        if pendente and pendente["continua"]:
            pendente["operandos"] += campo_operandos(conteudo.strip())
            pendente["continua"] = pendente["operandos"].endswith(",")
        else:
            nome = "" if conteudo.startswith(" ") else conteudo.split()[0]
            resto = conteudo[len(nome):].strip().split(None, 1)
            pendente = {
                "linha": n, "nome": nome,
                "op": resto[0].upper() if resto else "",
                "operandos": campo_operandos(resto[1].strip()) if len(resto) > 1 else "",
                "dados": [],
            }
            pendente["continua"] = pendente["operandos"].endswith(",")
            instrucoes.append(pendente)

        if (not pendente["continua"] and pendente["op"] == "DD"
                and re.match(r"^(\*|DATA)(,|$)", pendente["operandos"])):
            instream = pendente

    return instrucoes, comentarios


def interpretar_dd(instr):
    pos, kw = interpretar_operandos(instr["operandos"])
    dd = {"ddname": instr["nome"], "linha": instr["linha"]}

    dsn = kw.get("DSN") or kw.get("DSNAME")
    if dsn:
        m = re.match(r"^([^()]+)(?:\(([^)]+)\))?$", dsn)
        base, extra = m.group(1), m.group(2)
        dd["dsn"] = base
        if extra and re.fullmatch(r"[+-]?\d+", extra):
            dd["geracao_gdg"] = extra
        elif extra:
            dd["membro"] = extra

    if "DISP" in kw:
        dd["disp"] = [d or "" for d in tirar_parenteses(kw["DISP"]).split(",")]
    if "SYSOUT" in kw:
        dd["sysout"] = kw["SYSOUT"]

    dcb = {}
    if "DCB" in kw:
        _, dcb = interpretar_operandos(tirar_parenteses(kw["DCB"]))
    for k in ("RECFM", "LRECL", "BLKSIZE"):
        if k in kw:
            dcb[k] = kw[k]
    if dcb.get("LRECL"):
        dd["lrecl"] = int(dcb["LRECL"]) if dcb["LRECL"].isdigit() else dcb["LRECL"]
    if dcb.get("RECFM"):
        dd["recfm"] = dcb["RECFM"]

    if "*" in pos or "DATA" in pos:
        dd["instream"] = instr["dados"]
    if "DUMMY" in pos:
        dd["dummy"] = True
    return dd


def interpretar_sort(dados):
    comandos, atual = [], None
    for linha in dados:
        txt = linha[:71].rstrip()
        if not txt.strip() or txt.lstrip().startswith("*"):
            continue
        if atual and atual["operandos"].endswith(","):
            atual["operandos"] += campo_operandos(txt.strip())
            continue
        partes = txt.strip().split(None, 1)
        verbo = partes[0].upper()
        if verbo not in VERBOS_SORT:
            continue
        atual = {"comando": verbo,
                 "operandos": campo_operandos(partes[1].strip()) if len(partes) > 1 else ""}
        comandos.append(atual)

    resumo = {"filtro": None, "chaves": [], "sumarizacao": None,
              "reformata_registro": False, "gera_relatorio": False}
    for c in comandos:
        op = c["operandos"]
        if c["comando"] in ("INCLUDE", "OMIT"):
            resumo["filtro"] = f"{c['comando']} {op}"
        elif c["comando"] == "SORT":
            m = re.search(r"FIELDS=\(([^)]*)\)", op)
            if m:
                v = m.group(1).split(",")
                for i in range(0, len(v) - 3, 4):
                    resumo["chaves"].append({"pos": int(v[i]), "tamanho": int(v[i + 1]),
                                             "formato": v[i + 2],
                                             "ordem": "ascendente" if v[i + 3] == "A" else "descendente"})
        elif c["comando"] == "SUM":
            resumo["sumarizacao"] = op
        elif c["comando"] in ("INREC", "OUTREC"):
            resumo["reformata_registro"] = True
        elif c["comando"] == "OUTFIL":
            if re.search(r"\b(BUILD|OUTREC)=", op):
                resumo["reformata_registro"] = True
            if re.search(r"\b(HEADER\d|TRAILER\d|SECTIONS)=", op):
                resumo["gera_relatorio"] = True
    return comandos, resumo


def tabelas_do_sql(sql):
    return sorted(set(re.findall(r"\b(?:FROM|JOIN|INTO|UPDATE)\s+([A-Z0-9_#$@]+(?:\.[A-Z0-9_#$@]+)?)",
                                 sql.upper())))


def classificar_step(step):
    pgm = (step["pgm"] or "").upper()
    dds = {d["ddname"]: d for d in step["dds"] if d["ddname"]}

    if pgm in PGMS_TSO:
        systsin = " ".join(dds.get("SYSTSIN", {}).get("instream", []))
        m = re.search(r"RUN\s+PROGRAM\((\w+)\)", systsin, re.I)
        plano_db2 = re.search(r"PLAN\((\w+)\)", systsin, re.I)
        subsistema = re.search(r"DSN\s+SYSTEM\((\w+)\)", systsin, re.I)
        step["db2"] = {"subsistema": subsistema.group(1) if subsistema else None,
                       "plano": plano_db2.group(1) if plano_db2 else None}
        real = m.group(1).upper() if m else None
        if real == "DSNTIAUL":
            sql = " ".join(l.strip() for l in dds.get("SYSIN", {}).get("instream", []))
            step["tipo"] = "UNLOAD DB2 (DSNTIAUL)"
            step["sql"] = sql
            step["tabelas_db2"] = tabelas_do_sql(sql)
        elif real:
            step["tipo"] = "Programa DB2 (via IKJEFT01)"
            step["programa"] = real
        else:
            step["tipo"] = "TSO batch"
    elif pgm in PGMS_SORT:
        step["tipo"] = "SORT"
        comandos, resumo = interpretar_sort(dds.get("SYSIN", {}).get("instream", []))
        step["sort"] = {"comandos": comandos, **resumo}
    elif pgm in UTILITARIOS:
        step["tipo"] = UTILITARIOS[pgm]
    elif pgm:
        step["tipo"] = "Programa aplicativo"
        step["programa"] = pgm
    else:
        step["tipo"] = f"PROC {step.get('proc')}"


def analisar_jcl(caminho):
    texto = caminho.read_text(encoding="latin-1")
    instrucoes, comentarios = ler_comandos_jcl(texto)

    job = {"nome": None, "arquivo": caminho_relativo(caminho), "contabil": None,
           "descricao": None, "parametros": {}, "cabecalho": {}, "steps": []}
    primeira_exec = next((i["linha"] for i in instrucoes if i["op"] == "EXEC"), 10**9)
    job["cabecalho"] = ler_cabecalho([t for n, t in comentarios if n < primeira_exec])

    descr_steps = {}
    for _, t in comentarios:
        m = re.match(r"^\s*(\w+)\s+-\s+(.+)$", t)
        if m and m.group(1).upper().startswith("STEP") and m.group(1) not in descr_steps:
            descr_steps[m.group(1)] = re.sub(r"\s+", " ", m.group(2).strip())

    step, ultima_linha = None, 0
    for instr in instrucoes:
        if instr["op"] == "JOB":
            pos, kw = interpretar_operandos(instr["operandos"])
            job["nome"] = instr["nome"]
            job["contabil"] = pos[0] if pos else None
            job["descricao"] = tirar_aspas(pos[1]) if len(pos) > 1 else None
            job["parametros"] = kw
        elif instr["op"] == "EXEC":
            pos, kw = interpretar_operandos(instr["operandos"])
            notas = [t.strip() for n, t in comentarios
                     if ultima_linha < n < instr["linha"] and t.strip()
                     and not set(t.strip()) <= set("-=*")]
            step = {
                "nome": instr["nome"],
                "pgm": kw.get("PGM"),
                "proc": kw.get("PROC") or (pos[0] if pos else None),
                "parm": tirar_aspas(kw.get("PARM")) if kw.get("PARM") else None,
                "cond": kw.get("COND"),
                "descricao": descr_steps.get(instr["nome"]),
                "comentarios": notas,
                "programa": None,
                "dds": [],
            }
            job["steps"].append(step)
            ultima_linha = instr["linha"]
        elif instr["op"] == "DD" and step is not None:
            dd = interpretar_dd(instr)
            if not dd["ddname"] and step["dds"]:
                step["dds"][-1].setdefault("concatenados", []).append(dd)
            else:
                step["dds"].append(dd)
            ultima_linha = instr["linha"]

    for s in job["steps"]:
        classificar_step(s)
    return job


# =============================================================================
# Referencia cruzada e achados
# =============================================================================

def todos_dds(step):
    for dd in step["dds"]:
        yield dd
        for c in dd.get("concatenados", []):
            yield c


def montar_referencias(jobs, programas, copybooks):
    achados = []
    por_programa = {p["programa"]: p for p in programas}
    por_copy = {c["nome"]: c for c in copybooks}
    datasets = {}

    # --- programa x copybook ------------------------------------------------
    for p in programas:
        for cp in p["copybooks"]:
            if cp["copybook"] in por_copy:
                usado = por_copy[cp["copybook"]]["usado_por"]
                if p["programa"] not in usado:
                    usado.append(p["programa"])
            else:
                achados.append(achado("media", p["programa"],
                                      f"COPY {cp['copybook']} sem fonte na pasta de copybooks."))

    # --- programa x subrotina -----------------------------------------------
    for p in programas:
        for ch in p["chamadas"]:
            alvo = ch["programa"]
            if alvo is None:
                achados.append(achado("media", p["programa"],
                                      f"CALL dinamico pela variavel {ch['variavel']} sem VALUE fixo; "
                                      "o programa chamado so e conhecido em tempo de execucao."))
            elif alvo in por_programa:
                por_programa[alvo]["chamado_por"].append(p["programa"])
                por_programa[alvo]["tipo"] = "subrotina"
            else:
                achados.append(achado("media", p["programa"],
                                      f"CALL para {alvo} sem fonte na pasta."))

    # --- job x programa x dataset -------------------------------------------
    for job in jobs:
        for st in job["steps"]:
            ref = f"{job['nome']}.{st['nome']}"
            for dd in todos_dds(st):
                if not dd.get("dsn") or dd["ddname"] in DDS_BIBLIOTECA:
                    continue
                ds = datasets.setdefault(dd["dsn"], {
                    "dsn": dd["dsn"], "gdg": "geracao_gdg" in dd, "lrecl": None,
                    "recfm": None, "layout": None, "criado_por": [], "lido_por": [],
                })
                disp = (dd.get("disp") or ["SHR"])[0] or "NEW"
                (ds["criado_por"] if disp in ("NEW", "MOD") else ds["lido_por"]).append(
                    {"step": ref, "ddname": dd["ddname"], "disp": disp})
                ds["lrecl"] = ds["lrecl"] or dd.get("lrecl")
                ds["recfm"] = ds["recfm"] or dd.get("recfm")

            nome_pgm = st.get("programa")
            if not nome_pgm:
                continue
            if nome_pgm not in por_programa:
                achados.append(achado("alta", ref, f"Programa {nome_pgm} executado no job sem fonte na pasta."))
                continue
            prog = por_programa[nome_pgm]
            prog["executado_em"].append(ref)
            st["fonte_programa"] = prog["arquivo"]
            dds_step = {d["ddname"]: d for d in st["dds"] if d["ddname"]}
            mapa = []
            for arq in prog["arquivos"]:
                dd = dds_step.get(arq["ddname"])
                if dd is None:
                    achados.append(achado("alta", ref,
                                          f"{nome_pgm} exige a DD {arq['ddname']} "
                                          f"({arq['arquivo_logico']}) e ela nao existe no step."))
                    continue
                cp = por_copy.get(arq["copybook"]) if arq["copybook"] else None
                item = {"ddname": arq["ddname"], "arquivo_logico": arq["arquivo_logico"],
                        "dsn": dd.get("dsn"), "copybook": arq["copybook"],
                        "modo": arq["modo_abertura"],
                        "lrecl_jcl": dd.get("lrecl"),
                        "tamanho_copybook": cp["tamanho_calculado"] if cp else None}
                mapa.append(item)
                if dd.get("dsn") and arq["copybook"]:
                    datasets[dd["dsn"]]["layout"] = arq["copybook"]
                if cp and dd.get("lrecl") and dd["lrecl"] != cp["tamanho_calculado"]:
                    achados.append(achado("alta", ref,
                                          f"DD {arq['ddname']}: LRECL {dd['lrecl']} no JCL, mas o "
                                          f"copybook {cp['nome']} soma {cp['tamanho_calculado']} bytes."))
            st["mapeamento_arquivos"] = mapa

    # --- layout atravessando SORT sem reformatacao --------------------------
    mudou = True
    while mudou:
        mudou = False
        for job in jobs:
            for st in job["steps"]:
                if st["tipo"] != "SORT" or st["sort"]["reformata_registro"]:
                    continue
                dds_step = {d["ddname"]: d for d in st["dds"]}
                ent = dds_step.get("SORTIN", {}).get("dsn")
                sai = dds_step.get("SORTOUT", {}).get("dsn")
                if not ent or not sai:
                    continue
                le, ls = datasets[ent]["layout"], datasets[sai]["layout"]
                if le and not ls:
                    datasets[sai]["layout"] = le
                    mudou = True
                elif ls and not le:
                    datasets[ent]["layout"] = ls
                    mudou = True

    return sorted(datasets.values(), key=lambda d: d["dsn"]), achados


def verificar_regras(jobs, programas, copybooks):
    achados = []

    for job in jobs:
        ocorrencias = []  # (step, onde, datas)
        for st in job["steps"]:
            ref = f"{job['nome']}.{st['nome']}"
            datas = re.findall(RE_DATA_ISO, st.get("parm") or "")
            if datas:
                ocorrencias.append((ref, "PARM", datas))
                achados.append(achado("alta", ref,
                                      f"Data fixa no PARM ('{st['parm']}'). Deveria vir do agendador "
                                      "(ex.: %%ODATE no Control-M)."))
            for dd in todos_dds(st):
                datas = sorted({d for l in dd.get("instream", []) for d in re.findall(RE_DATA_ISO, l)})
                if datas:
                    ocorrencias.append((ref, f"DD {dd['ddname']}", datas))
                    achados.append(achado("alta", ref,
                                          f"Data fixa no instream da DD {dd['ddname']}: {', '.join(datas)}."))
        if len(ocorrencias) > 1:
            todas = sorted({d for _, _, ds in ocorrencias for d in ds})
            onde = ", ".join(f"{r.split('.')[-1]} ({o})" for r, o, _ in ocorrencias)
            if len(todas) == 1:
                texto = (f"A mesma data ({todas[0]}) esta digitada em {len(ocorrencias)} lugares: {onde}. "
                         "Um reprocessamento pode acabar usando datas diferentes entre os steps.")
            else:
                texto = f"Datas diferentes fixadas no job ({', '.join(todas)}): {onde}."
            achados.append(achado("alta", job["nome"], texto))

    for p in programas:
        nome, plano = p["programa"], p["_plano"]
        for arq in p["arquivos"]:
            if not arq["file_status"]:
                achados.append(achado("media", nome, f"SELECT {arq['arquivo_logico']} sem FILE STATUS."))
        for t in p["tabelas_internas"]:
            achados.append(achado("media", nome,
                                  f"Tabela interna {t['nome']} limitada a {t['maximo']} ocorrencias; "
                                  "o crescimento do volume pode interromper o processamento."))
        fixos = re.findall(r"WHEN '[^']*' MOVE -?[\d.]+ TO", plano)
        if len(fixos) >= 4:
            achados.append(achado("alta", nome,
                                  f"Tabela de valores fixa no codigo ({len(fixos)} WHEN com valores "
                                  "literais). Alterar exige manutencao e nova implantacao."))
        if "**" in p["_sem_literais"]:
            achados.append(achado("media", nome,
                                  "Usa exponenciacao (**). Validar precisao e arredondamento "
                                  "em qualquer migracao de plataforma."))
        if p["tipo"] == "subrotina" and "STOP RUN" in plano:
            achados.append(achado("alta", nome, "Sub-rotina com STOP RUN encerra a unidade de execucao inteira."))
        for par in p["paragrafos_nao_referenciados"]:
            achados.append(achado("baixa", nome, f"Paragrafo {par} nao e chamado por PERFORM (possivel codigo morto)."))

    for c in copybooks:
        if c["lrecl_documentado"] and c["lrecl_documentado"] != c["tamanho_calculado"]:
            achados.append(achado("alta", c["nome"],
                                  f"Comentario diz LRECL {c['lrecl_documentado']}, "
                                  f"mas os campos somam {c['tamanho_calculado']} bytes."))
        if not c["usado_por"]:
            achados.append(achado("info", c["nome"], "Copybook nao e referenciado por nenhum programa da pasta."))

    return achados


# =============================================================================
# IA local (Ollama)
# =============================================================================

PROMPT_SISTEMA = """Voce e um analista mainframe senior do setor bancario (COBOL, JCL, DB2, DFSORT).
Sua tarefa e interpretar um componente legado para um inventario tecnico.
Use apenas o que esta no fonte e nos fatos extraidos. Nao invente tabelas, programas, campos ou valores.
Responda em portugues do Brasil, somente com um objeto JSON valido."""

PROMPT_USUARIO = """Componente: {nome} ({tipo})

Fatos extraidos pelo parser (confiaveis):
{fatos}

Codigo-fonte:
```
{fonte}
```

Devolva um JSON com exatamente estas chaves:
- "resumo_negocio": 2 a 3 frases para um executivo nao tecnico, sem jargao de TI.
- "funcao_tecnica": 1 a 2 frases para um analista de sistemas.
- "regras_negocio": lista com ate 6 regras de negocio, uma frase cada.
- "riscos": lista com ate 5 riscos ou pontos de atencao encontrados no codigo, uma frase cada."""


class ClienteOllama:
    def __init__(self, url, modelo, timeout=600):
        self.url = url.rstrip("/")
        self.modelo = modelo
        self.timeout = timeout

    def _requisicao(self, caminho, corpo=None):
        dados = json.dumps(corpo).encode("utf-8") if corpo is not None else None
        req = urllib.request.Request(self.url + caminho, data=dados,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def disponivel(self):
        try:
            tags = self._requisicao("/api/tags")
        except (urllib.error.URLError, OSError, ValueError) as e:
            log(f"Ollama indisponivel em {self.url}: {e}")
            return False
        nomes = {m["name"] for m in tags.get("models", [])}
        if self.modelo not in nomes and f"{self.modelo}:latest" not in nomes:
            log(f"Modelo {self.modelo} nao encontrado no Ollama. Instalados: {', '.join(sorted(nomes))}")
            return False
        return True

    def gerar_json(self, sistema, usuario):
        corpo = {
            "model": self.modelo,
            "messages": [{"role": "system", "content": sistema},
                         {"role": "user", "content": usuario}],
            "stream": False,
            "format": "json",
            "options": {"temperature": 0, "num_ctx": 16384},
        }
        resp = self._requisicao("/api/chat", corpo)
        return json.loads(resp["message"]["content"])


def para_lista(valor):
    """Modelos pequenos as vezes devolvem dict ou texto onde era lista."""
    if valor is None:
        return []
    if isinstance(valor, str):
        return [valor] if valor.strip() else []
    if isinstance(valor, dict):
        valor = list(valor.values())
    saida = []
    for v in valor:
        if isinstance(v, dict):
            v = " - ".join(str(x) for x in v.values())
        saida.append(str(v).strip())
    return [s for s in saida if s]


def interpretar_com_ia(cliente, nome, tipo, fatos, caminho_fonte):
    fonte = Path(caminho_fonte).read_text(encoding="latin-1")[:LIMITE_FONTE_IA]
    usuario = PROMPT_USUARIO.format(nome=nome, tipo=tipo,
                                    fatos=json.dumps(fatos, ensure_ascii=False, indent=1),
                                    fonte=fonte)
    inicio = time.time()
    try:
        bruto = cliente.gerar_json(PROMPT_SISTEMA, usuario)
    except (urllib.error.URLError, OSError, ValueError, KeyError) as e:
        log(f"  falha na IA para {nome}: {e}")
        return {"erro": str(e)}
    return {
        "resumo_negocio": str(bruto.get("resumo_negocio", "")).strip(),
        "funcao_tecnica": str(bruto.get("funcao_tecnica", "")).strip(),
        "regras_negocio": para_lista(bruto.get("regras_negocio")),
        "riscos": para_lista(bruto.get("riscos")),
        "modelo": cliente.modelo,
        "segundos": round(time.time() - inicio, 1),
    }


def fatos_programa(p):
    return {
        "programa": p["programa"], "tipo": p["tipo"], "objetivo": p["objetivo"],
        "arquivos": [{k: a[k] for k in ("arquivo_logico", "ddname", "copybook", "modo_abertura")}
                     for a in p["arquivos"]],
        "chamadas": [c["programa"] for c in p["chamadas"]],
        "chamado_por": p["chamado_por"],
        "copybooks": [c["copybook"] for c in p["copybooks"]],
        "return_codes": p["return_codes"],
        "regras_documentadas": p["regras_documentadas"],
    }


def fatos_job(j):
    return {
        "job": j["nome"], "descricao": j["descricao"], "cabecalho": j["cabecalho"],
        "steps": [{"step": s["nome"], "tipo": s["tipo"], "programa": s.get("programa"),
                   "tabelas_db2": s.get("tabelas_db2"),
                   "entradas": [d["dsn"] for d in s["dds"] if d.get("dsn") and (d.get("disp") or ["SHR"])[0] not in ("NEW", "MOD")],
                   "saidas": [d["dsn"] for d in s["dds"] if d.get("dsn") and (d.get("disp") or ["SHR"])[0] in ("NEW", "MOD")]}
                  for s in j["steps"]],
    }


# =============================================================================
# Markdown
# =============================================================================

def esc(v):
    return str(v if v is not None else "").replace("|", "\\|")


def id_mermaid(texto):
    return re.sub(r"[^A-Za-z0-9_]", "_", texto)


def md_mermaid_job(job):
    linhas = ["```mermaid", "flowchart TD"]
    declarados = set()
    for st in job["steps"]:
        sid = id_mermaid(st["nome"])
        rotulo = st.get("programa") or st["tipo"]
        linhas.append(f'    {sid}["{st["nome"]}<br/>{rotulo}"]')
    for st in job["steps"]:
        sid = id_mermaid(st["nome"])
        for dd in todos_dds(st):
            if not dd.get("dsn"):
                continue
            did = "DS_" + id_mermaid(dd["dsn"])
            if did not in declarados:
                linhas.append(f'    {did}[("{dd["dsn"]}")]')
                declarados.add(did)
            disp = (dd.get("disp") or ["SHR"])[0] or "NEW"
            linhas.append(f"    {sid} --> {did}" if disp in ("NEW", "MOD") else f"    {did} --> {sid}")
    for p_ in job["steps"]:
        if p_.get("tabelas_db2"):
            for t in p_["tabelas_db2"]:
                tid = "DB_" + id_mermaid(t)
                if tid not in declarados:
                    linhas.append(f'    {tid}[("DB2: {t}")]')
                    declarados.add(tid)
                linhas.append(f"    {tid} --> {id_mermaid(p_['nome'])}")
    linhas.append("```")
    return linhas


def md_ia(analise):
    if not analise:
        return []
    if "erro" in analise:
        return [f"> Analise de IA indisponivel: {analise['erro']}", ""]
    out = [f"**Interpretacao gerada por IA ({analise['modelo']}) — validar com o analista**", ""]
    if analise["resumo_negocio"]:
        out += [f"- **Para o negocio:** {analise['resumo_negocio']}"]
    if analise["funcao_tecnica"]:
        out += [f"- **Funcao tecnica:** {analise['funcao_tecnica']}"]
    if analise["regras_negocio"]:
        out += ["- **Regras de negocio:**"] + [f"    - {r}" for r in analise["regras_negocio"]]
    if analise["riscos"]:
        out += ["- **Riscos:**"] + [f"    - {r}" for r in analise["riscos"]]
    return out + [""]


def gerar_markdown(inv):
    md, meta, res = [], inv["metadados"], inv["resumo"]
    md += ["# Inventario de componentes mainframe", "",
           f"Gerado em {meta['gerado_em']} a partir de `{meta['pasta_fontes']}` "
           f"(inventario_mainframe.py v{meta['versao']}). "
           + (f"Interpretacao por IA local: `{meta['modelo_ia']}`." if meta["ia_utilizada"]
              else "Sem interpretacao por IA."), "",
           "## Visao geral", "",
           "| Jobs | Steps | Programas | Copybooks | Datasets | Achados |",
           "| --- | --- | --- | --- | --- | --- |",
           f"| {res['jobs']} | {res['steps']} | {res['programas']} | {res['copybooks']} "
           f"| {res['datasets']} | {res['achados']} |", ""]

    for job in inv["jobs"]:
        cab = job["cabecalho"]
        md += [f"## Job {job['nome']} — {esc(job['descricao'])}", ""]
        for chave, rotulo in (("objetivo", "Objetivo"), ("periodic", "Periodicidade"),
                              ("predec", "Predecessor"), ("sucessor", "Sucessor")):
            if cab.get(chave):
                md.append(f"- **{rotulo}:** {cab[chave]}")
        md += [f"- **Fonte:** `{job['arquivo']}`", ""]
        md += md_ia(job.get("analise_ia"))
        md += ["### Fluxo", ""] + md_mermaid_job(job) + [""]
        md += ["### Steps", "",
               "| Step | Tipo | Programa | PARM | COND | Descricao |",
               "| --- | --- | --- | --- | --- | --- |"]
        for s in job["steps"]:
            md.append(f"| {s['nome']} | {esc(s['tipo'])} | {esc(s.get('programa') or s['pgm'])} "
                      f"| {esc(s['parm'])} | {esc(s['cond'])} | {esc(s['descricao'])} |")
        md.append("")
        for s in job["steps"]:
            detalhes = []
            if s.get("tabelas_db2"):
                detalhes.append(f"- Tabelas DB2: {', '.join(s['tabelas_db2'])}")
            if s.get("sql"):
                detalhes.append(f"- SQL: `{esc(s['sql'])}`")
            if s.get("sort"):
                so = s["sort"]
                if so["filtro"]:
                    detalhes.append(f"- Filtro: `{esc(so['filtro'])}`")
                if so["chaves"]:
                    detalhes.append("- Chaves: " + ", ".join(
                        f"pos {c['pos']} tam {c['tamanho']} {c['formato']} {c['ordem']}" for c in so["chaves"]))
                if so["sumarizacao"]:
                    detalhes.append(f"- Sumarizacao: `{esc(so['sumarizacao'])}`")
                detalhes.append(f"- Reformata registro: {'sim' if so['reformata_registro'] else 'nao'}; "
                                f"gera relatorio: {'sim' if so['gera_relatorio'] else 'nao'}")
            for m in s.get("mapeamento_arquivos", []):
                detalhes.append(f"- DD `{m['ddname']}` → `{m['dsn']}` ({m['arquivo_logico']}, "
                                f"layout {m['copybook']}, {'/'.join(m['modo'])})")
            if detalhes:
                md += [f"**{s['nome']}**", ""] + detalhes + [""]

    md += ["## Programas", "",
           "| Programa | Tipo | Executado em | Chama | Chamado por | Linhas (codigo/coment.) | RCs |",
           "| --- | --- | --- | --- | --- | --- | --- |"]
    for p in inv["programas"]:
        cham = ", ".join(f"{c['programa']}{' (dinamico)' if c['dinamico'] else ''}" for c in p["chamadas"])
        mt = p["metricas"]
        md.append(f"| {p['programa']} | {p['tipo']} | {', '.join(p['executado_em']) or '-'} "
                  f"| {cham or '-'} | {', '.join(p['chamado_por']) or '-'} "
                  f"| {mt['linhas_codigo']}/{mt['linhas_comentario']} "
                  f"| {', '.join(str(r) for r in p['return_codes']) or '-'} |")
    md.append("")
    for p in inv["programas"]:
        md += [f"### {p['programa']}", "", f"- **Fonte:** `{p['arquivo']}`",
               f"- **Objetivo (cabecalho):** {p['objetivo'] or '-'}",
               f"- **Copybooks:** " + (", ".join(f"{c['copybook']} ({c['secao']})" for c in p["copybooks"]) or "-"),
               f"- **Paragrafos:** {len(p['paragrafos'])}"]
        if p["parametros_entrada"]:
            md.append(f"- **Recebe (USING):** {', '.join(p['parametros_entrada'])}")
        if p["arquivos"]:
            md += ["", "| Arquivo logico | DDNAME | Copybook | Abertura | File status |",
                   "| --- | --- | --- | --- | --- |"]
            for a in p["arquivos"]:
                md.append(f"| {a['arquivo_logico']} | {a['ddname']} | {a['copybook'] or '-'} "
                          f"| {'/'.join(a['modo_abertura']) or '-'} | {a['file_status'] or '-'} |")
        if p["regras_documentadas"]:
            md += ["", "Regras documentadas no fonte:", ""]
            md += [f"- **{r['id']}** {r['descricao']}" for r in p["regras_documentadas"]]
        if p["historico"]:
            md += ["", "Historico de alteracoes:", ""]
            md += [f"- {h['data']} ({h['autor']}): {h['descricao']}" for h in p["historico"]]
        md.append("")
        md += md_ia(p.get("analise_ia"))

    md += ["## Copybooks", ""]
    for c in inv["copybooks"]:
        status = "" if not c["lrecl_documentado"] else (
            " — confere com o LRECL documentado" if c["lrecl_documentado"] == c["tamanho_calculado"]
            else f" — DIVERGE do LRECL documentado ({c['lrecl_documentado']})")
        md += [f"### {c['nome']} — {c['tamanho_calculado']} bytes{status}", "",
               f"{c['descricao']}", "",
               f"Usado por: {', '.join(c['usado_por']) or '-'}", "",
               "| Nivel | Campo | Pos | Tam | Formato | 88 |", "| --- | --- | --- | --- | --- | --- |"]
        for f in c["campos"]:
            cond = ", ".join(f"{x['nome']}={x['valor']}" for x in f["condicoes"])
            occ = f" OCCURS {f['occurs']}" if f["occurs"] else ""
            md.append(f"| {f['nivel']:02d} | {f['nome']} | {f['pos']} | {f['tamanho']} "
                      f"| {esc(f['formato'])}{occ} | {esc(cond)} |")
        md.append("")

    md += ["## Datasets e linhagem", "",
           "| Dataset | GDG | LRECL | Layout | Criado por | Lido por |",
           "| --- | --- | --- | --- | --- | --- |"]
    for d in inv["datasets"]:
        md.append(f"| {d['dsn']} | {'sim' if d['gdg'] else 'nao'} | {d['lrecl'] or '-'} "
                  f"| {d['layout'] or '-'} | {', '.join(x['step'] for x in d['criado_por']) or '-'} "
                  f"| {', '.join(x['step'] for x in d['lido_por']) or '-'} |")
    md.append("")

    md += ["## Achados automaticos", "",
           "| Severidade | Componente | Descricao |", "| --- | --- | --- |"]
    for a in inv["achados"]:
        md.append(f"| {a['severidade']} | {a['componente']} | {esc(a['descricao'])} |")
    md.append("")
    return "\n".join(md)


# =============================================================================
# Principal
# =============================================================================

def descobrir_fontes(pasta):
    encontrados = {"jcl": [], "cobol": [], "copybook": []}
    for p in sorted(pasta.rglob("*")):
        if p.is_file() and p.suffix.lower() in EXTENSOES:
            encontrados[EXTENSOES[p.suffix.lower()]].append(p)
    return encontrados


def main():
    ap = argparse.ArgumentParser(description="Inventario de componentes mainframe (JCL, COBOL, copybooks).")
    ap.add_argument("--fontes", default="legado", help="pasta com os fontes (padrao: legado)")
    ap.add_argument("--saida", default="saida", help="pasta de saida (padrao: saida)")
    ap.add_argument("--modelo", default=MODELO_PADRAO, help=f"modelo do Ollama (padrao: {MODELO_PADRAO})")
    ap.add_argument("--ollama-url", default=OLLAMA_URL_PADRAO, help="endereco do Ollama")
    ap.add_argument("--sem-ia", action="store_true", help="gera so o inventario de fatos")
    args = ap.parse_args()

    pasta = Path(args.fontes)
    if not pasta.is_dir():
        log(f"Pasta de fontes nao encontrada: {pasta}")
        return 2

    inicio = time.time()
    fontes = descobrir_fontes(pasta)
    log(f"Fontes: {len(fontes['jcl'])} JCL, {len(fontes['cobol'])} COBOL, {len(fontes['copybook'])} copybooks")

    copybooks = [analisar_copybook(p) for p in fontes["copybook"]]
    programas = [analisar_cobol(p) for p in fontes["cobol"]]
    jobs = [analisar_jcl(p) for p in fontes["jcl"]]

    datasets, achados = montar_referencias(jobs, programas, copybooks)
    achados += verificar_regras(jobs, programas, copybooks)
    achados.sort(key=lambda a: (ORDEM_SEVERIDADE[a["severidade"]], a["componente"]))

    ia_ok = False
    if not args.sem_ia:
        cliente = ClienteOllama(args.ollama_url, args.modelo)
        ia_ok = cliente.disponivel()
        if ia_ok:
            for p in programas:
                log(f"IA: interpretando programa {p['programa']}...")
                p["analise_ia"] = interpretar_com_ia(cliente, p["programa"], f"programa COBOL {p['tipo']}",
                                                     fatos_programa(p), p["arquivo"])
            for j in jobs:
                log(f"IA: interpretando job {j['nome']}...")
                j["analise_ia"] = interpretar_com_ia(cliente, j["nome"], "JCL batch",
                                                     fatos_job(j), j["arquivo"])
        else:
            log("Seguindo sem a interpretacao por IA.")

    for p in programas:
        p.pop("_plano", None)
        p.pop("_sem_literais", None)

    inventario = {
        "metadados": {
            "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "versao": VERSAO,
            "pasta_fontes": caminho_relativo(pasta),
            "modelo_ia": args.modelo if ia_ok else None,
            "ia_utilizada": ia_ok,
        },
        "resumo": {
            "jobs": len(jobs),
            "steps": sum(len(j["steps"]) for j in jobs),
            "programas": len(programas),
            "copybooks": len(copybooks),
            "datasets": len(datasets),
            "achados": len(achados),
            "achados_por_severidade": {s: sum(1 for a in achados if a["severidade"] == s)
                                       for s in ORDEM_SEVERIDADE},
        },
        "jobs": jobs,
        "programas": programas,
        "copybooks": copybooks,
        "datasets": datasets,
        "achados": achados,
    }

    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)
    (saida / "inventario.json").write_text(json.dumps(inventario, ensure_ascii=False, indent=2), encoding="utf-8")
    (saida / "inventario.md").write_text(gerar_markdown(inventario), encoding="utf-8")

    r = inventario["resumo"]
    log(f"Pronto em {time.time() - inicio:.1f}s: {r['jobs']} job(s), {r['steps']} steps, "
        f"{r['programas']} programas, {r['copybooks']} copybooks, {r['datasets']} datasets, "
        f"{r['achados']} achados -> {saida}/inventario.json e inventario.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
