#!/usr/bin/env bash
# Compila a JURS0100 ORIGINAL de legado/ com GnuCOBOL, roda a massa de
# equivalencia pelo driver JURT0100 e compara o resultado com o que o
# servico Java espera (casos.csv). Precisa so de Podman ou Docker.
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
MOTOR="${CONTAINER:-$(command -v podman || command -v docker)}"
IMAGEM="gnucobol-jur:3.2"
CASOS="servico-juros/src/test/resources/equivalencia/casos.csv"

echo "[1/3] Preparando imagem GnuCOBOL..."
"$MOTOR" build -q -t "$IMAGEM" -f "$RAIZ/equivalencia-cobol/Containerfile" "$RAIZ/equivalencia-cobol" >/dev/null

echo "[2/3] Compilando JURS0100 (sem alteracao) e JURT0100, rodando a massa..."
"$MOTOR" run --rm -v "$RAIZ":/w:Z "$IMAGEM" bash -euo pipefail -c "
  cobc -std=ibm -m -I /w/legado/copybook /w/legado/cobol/JURS0100.cbl -o JURS0100.so
  cobc -std=ibm -x -I /w/legado/copybook /w/equivalencia-cobol/JURT0100.cbl -o jurt0100
  tail -n +2 /w/$CASOS | cut -d';' -f1-9 > entrada.csv
  COB_LIBRARY_PATH=. ./jurt0100
  cp saida.csv /w/equivalencia-cobol/saida-cobol.csv
  cobc --version > versao.txt
  head -n 1 versao.txt > /w/equivalencia-cobol/versao-compilador.txt
"

echo "[3/3] Comparando COBOL x Java..."
python3 -I "$RAIZ/equivalencia-cobol/comparar.py" "$RAIZ/$CASOS" "$RAIZ/equivalencia-cobol/saida-cobol.csv"
