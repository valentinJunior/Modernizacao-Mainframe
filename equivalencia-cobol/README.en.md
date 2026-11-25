# Equivalence with the real COBOL

[🇧🇷 Português](README.md) | 🇺🇸 English

This folder compiles and runs the **original JURS0100** subroutine, from `legado/cobol/`, without any modification. It runs the same set of cases used by the `servico-juros` tests and compares both results field by field.

```bash
./equivalencia-cobol/executar.sh     # only needs Podman or Docker
```

## How it works

1. The `Containerfile` image installs GnuCOBOL 3.2.
2. `JURS0100` is compiled with `-std=ibm`, the IBM Enterprise COBOL compatibility mode, as a module loaded through a dynamic `CALL`, just as `JURB0100` does.
3. The `JURT0100.cbl` driver reads the inputs from `servico-juros/src/test/resources/equivalencia/casos.csv`, builds the `JURCCALC` area and calls `JURS0100`.
4. The output goes to `saida-cobol.csv`, and `comparar.py` checks each of the 9 output fields against what the Java expects. A one-cent difference is enough to fail.

## Result

**27 out of 27 cases identical**, including:
- the documentation example (R$ 4,383.33);
- the half-cent ties (`ROUNDED` rounding);
- the balance truncated on the left (high-order digits);
- the leap year;
- the 11 rejections, among them the non-numeric balance (invalid `COMP-3`, code 21).

Since the Java tests use the same `casos.csv`, the chain of evidence looks like this:

```
COBOL original (GnuCOBOL)  ==  casos.csv  ==  servico-juros (Java)
```

## Limits of this proof

- **GnuCOBOL is not the production compiler.** `-std=ibm` approximates IBM Enterprise COBOL behavior, but intermediate arithmetic and fractional exponentiation (`**`) may differ in extreme cases. Definitive validation requires the real output of the `JURD0100` job on the mainframe (`BCO.JUR.APROP.JUROS`), which can be appended to the same `casos.csv`.
- The proof covers the calculation subroutine (`JURS0100`). The rate lookup in `JURB0100` is covered by the service's rate repository tests.
