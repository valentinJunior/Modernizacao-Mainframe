#!/usr/bin/env python3
"""
Implementacao de referencia da JURS0100, independente do codigo Java, usada para
gerar src/test/resources/equivalencia/casos.csv enquanto nao temos a massa real
extraida do JUROSOUT no mainframe. Segue a semantica do COBOL linha a linha.

Uso: python3 ferramentas/referencia_jurs0100.py > src/test/resources/equivalencia/casos.csv
"""
from datetime import date
from decimal import Decimal as D, ROUND_HALF_UP, ROUND_DOWN, getcontext

getcontext().prec = 34
SPREAD = {"AA": "0", "A": "0.10", "B": "0.25", "C": "0.50", "D": "0.75",
          "E": "1.00", "F": "1.25", "G": "1.50", "H": "2.00"}


def data(txt):
    try:
        a, m, d = txt.split("-")
        assert len(a) == 4 and len(m) == 2 and len(d) == 2
        return date(int(a), int(m), int(d))
    except Exception:
        return None


def q(v, casas):
    return v.quantize(D(1).scaleb(-casas), rounding=ROUND_HALF_UP)


def jurs0100(rating, saldo_txt, taxa, mora, multa, ult_txt, venc_txt, ref_txt):
    try:
        saldo = D(saldo_txt).quantize(D("0.01"), rounding=ROUND_DOWN)
    except Exception:
        return "21", None
    saldo = saldo % D(10) ** 13  # MOVE para S9(13)V99 descarta inteiros alem do 13o (pela esquerda)
    if saldo <= 0:
        return "20", None
    taxa, mora, multa = D(taxa), D(mora), D(multa)
    if taxa <= 0 or taxa > 30:
        return "10", None
    ult, venc, ref = data(ult_txt), data(venc_txt), data(ref_txt)
    if ult is None:
        return "30", None
    if venc is None:
        return "31", None
    if ref is None:
        return "33", None
    if ref < ult:
        return "32", None
    if rating.strip() not in SPREAD:
        return "40", None
    taxa_apl = q(taxa + D(SPREAD[rating.strip()]), 4)
    dias = (ref - ult).days
    atraso = ref > venc
    dias_atraso = (ref - venc).days if atraso else 0
    remun = D("0.00")
    if dias:
        exp = q(D(dias) / 30, 9)
        fator = q(D((float(1 + taxa_apl / 100)) ** float(exp)), 12)
        remun = q(saldo * (fator - 1), 2)
    v_mora = v_multa = D("0.00")
    if atraso:
        dp = min(dias_atraso, dias)
        v_mora = q(saldo * mora / 100 * dp / 30, 2)
        if venc >= ult:
            v_multa = q(saldo * multa / 100, 2)
    total = remun + v_mora + v_multa
    return "00", (taxa_apl, dias, dias_atraso, remun, v_mora, v_multa, total, saldo + total)


CASOS = [
    # caso, rating, saldo, taxa, mora, multa, ult, venc, ref
    ("exemplo_documentacao", "B", "100000.00", "1.80", "1.00", "2.00", "2026-10-25", "2026-11-14", "2026-11-24"),
    ("rotina_diaria_em_dia", "B", "100000.00", "1.80", "1.00", "2.00", "2026-11-23", "2026-12-14", "2026-11-24"),
    ("dias_zero", "B", "100000.00", "1.80", "1.00", "2.00", "2026-11-24", "2026-12-14", "2026-11-24"),
    ("vencimento_igual_ultima_apuracao", "A", "50000.00", "1.80", "1.00", "2.00", "2026-10-25", "2026-10-25", "2026-11-24"),
    ("atraso_anterior_ao_periodo", "C", "35000.00", "1.65", "1.00", "2.00", "2026-11-23", "2026-11-01", "2026-11-24"),
    ("atraso_maior_que_periodo", "D", "12000.00", "1.49", "1.00", "2.00", "2026-11-10", "2026-10-01", "2026-11-24"),
    ("rating_AA_45_dias", "AA", "2500.50", "1.80", "1.00", "2.00", "2026-10-10", "2026-12-10", "2026-11-24"),
    ("rating_E", "E", "7777.77", "1.80", "1.00", "2.00", "2026-11-01", "2026-12-01", "2026-11-24"),
    ("rating_F", "F", "1000.00", "1.80", "1.00", "2.00", "2026-11-14", "2026-12-14", "2026-11-24"),
    ("rating_G", "G", "123456.78", "1.80", "1.00", "2.00", "2026-10-24", "2026-12-24", "2026-11-24"),
    ("rating_H_cheque_especial", "H", "3200.00", "7.90", "1.00", "2.00", "2026-10-24", "2026-11-20", "2026-11-24"),
    ("saldo_com_3_casas_truncado", "B", "1000.009", "1.80", "1.00", "2.00", "2026-10-25", "2026-12-25", "2026-11-24"),
    ("saldo_acima_de_13_inteiros_truncado", "B", "12345678901234.00", "1.80", "1.00", "2.00", "2026-10-25", "2026-11-14", "2026-11-24"),
    ("ano_bissexto_fevereiro", "B", "10000.00", "1.80", "1.00", "2.00", "2028-02-01", "2028-03-15", "2028-03-01"),
    # empates de meio centavo: so aqui HALF_UP (ROUNDED do COBOL) e HALF_EVEN divergem
    ("empate_meio_centavo_multa", "B", "100.25", "1.80", "1.00", "2.00", "2026-10-25", "2026-11-14", "2026-11-24"),
    ("empate_meio_centavo_mora", "B", "1.50", "1.80", "1.00", "2.00", "2026-11-14", "2026-11-14", "2026-11-24"),
    ("rejeita_rating_invalido", "X", "100000.00", "1.80", "1.00", "2.00", "2026-10-25", "2026-11-14", "2026-11-24"),
    ("rejeita_saldo_zero", "B", "0.00", "1.80", "1.00", "2.00", "2026-10-25", "2026-11-14", "2026-11-24"),
    ("rejeita_saldo_negativo", "B", "-10.00", "1.80", "1.00", "2.00", "2026-10-25", "2026-11-14", "2026-11-24"),
    ("rejeita_saldo_nao_numerico", "B", "ABC", "1.80", "1.00", "2.00", "2026-10-25", "2026-11-14", "2026-11-24"),
    ("rejeita_taxa_zero", "B", "100000.00", "0.00", "1.00", "2.00", "2026-10-25", "2026-11-14", "2026-11-24"),
    ("rejeita_taxa_acima_30", "B", "100000.00", "30.0001", "1.00", "2.00", "2026-10-25", "2026-11-14", "2026-11-24"),
    ("rejeita_ultima_apuracao_invalida", "B", "100000.00", "1.80", "1.00", "2.00", "2026-02-30", "2026-11-14", "2026-11-24"),
    ("rejeita_vencimento_invalido", "B", "100000.00", "1.80", "1.00", "2.00", "2026-10-25", "14/11/2026", "2026-11-24"),
    ("rejeita_referencia_invalida", "B", "100000.00", "1.80", "1.00", "2.00", "2026-10-25", "2026-11-14", "2026-13-01"),
    ("rejeita_referencia_anterior", "B", "100000.00", "1.80", "1.00", "2.00", "2026-11-25", "2026-11-14", "2026-11-24"),
    ("dois_erros_vale_o_primeiro", "X", "0.00", "1.80", "1.00", "2.00", "2026-10-25", "2026-11-14", "2026-11-24"),
]

print("caso;rating;saldo;taxa_base;mora;multa;dt_ult_apuracao;dt_vencimento;dt_referencia;"
      "codigo;taxa_aplicada;dias;dias_atraso;juros_remun;juros_mora;valor_multa;total;saldo_atualizado")
for c in CASOS:
    cod, r = jurs0100(*c[1:])
    saida = [cod] + ([str(x) for x in r] if r else [""] * 8)
    print(";".join(list(c) + saida))
