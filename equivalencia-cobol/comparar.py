#!/usr/bin/env python3
"""
Compara o resultado do COBOL (saida-cobol.csv) com a massa de equivalencia
que o servico Java usa nos testes (servico-juros/.../casos.csv).

Uso: python3 comparar.py <casos.csv> <saida-cobol.csv>
Sai com codigo 1 se houver qualquer diferenca.
"""
import csv
import sys

CAMPOS = ["codigo", "taxa_aplicada", "dias", "dias_atraso", "juros_remun",
          "juros_mora", "valor_multa", "total", "saldo_atualizado"]


def ler_esperado(caminho):
    with open(caminho, encoding="utf-8", newline="") as f:
        return {l["caso"]: [l[c] for c in CAMPOS] for l in csv.DictReader(f, delimiter=";")}


def ler_cobol(caminho):
    with open(caminho, encoding="utf-8", newline="") as f:
        return {l[0]: l[1:] for l in csv.reader(f, delimiter=";") if l}


def main():
    esperado, cobol = ler_esperado(sys.argv[1]), ler_cobol(sys.argv[2])
    divergentes = 0
    for caso, valores in esperado.items():
        obtido = cobol.get(caso)
        if obtido is None:
            print(f"FALTOU   {caso}: o COBOL nao gerou resultado")
            divergentes += 1
            continue
        difs = [f"{c}: Java={e!r} COBOL={o!r}" for c, e, o in zip(CAMPOS, valores, obtido) if e != o]
        if difs:
            divergentes += 1
            print(f"DIVERGE  {caso}")
            for d in difs:
                print(f"           {d}")
        else:
            print(f"OK       {caso}")
    print(f"\n{len(esperado) - divergentes} de {len(esperado)} casos identicos entre COBOL e Java.")
    sys.exit(1 if divergentes else 0)


if __name__ == "__main__":
    main()
