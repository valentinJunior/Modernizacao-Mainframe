# Equivalência com o COBOL real

🇧🇷 Português | [🇺🇸 English](README.en.md)

Esta pasta compila e executa a sub-rotina **JURS0100 original**, de `legado/cobol/`, sem nenhuma alteração. Ela roda a mesma massa de casos que os testes do `servico-juros` usam e compara os dois resultados campo a campo.

```bash
./equivalencia-cobol/executar.sh     # precisa só de Podman ou Docker
```

## Como funciona

1. A imagem `Containerfile` instala o GnuCOBOL 3.2.
2. A `JURS0100` é compilada com `-std=ibm`, o modo de compatibilidade com o IBM Enterprise COBOL, como módulo carregado por `CALL` dinâmico, igual ao que o `JURB0100` faz.
3. O driver `JURT0100.cbl` lê as entradas de `servico-juros/src/test/resources/equivalencia/casos.csv`, monta a área `JURCCALC` e chama a `JURS0100`.
4. O resultado vai para `saida-cobol.csv`, e `comparar.py` confere cada um dos 9 campos de saída contra o esperado pelo Java. Uma diferença de um centavo já falha.

## Resultado

**27 de 27 casos idênticos**, incluindo os seguintes:
- o exemplo da documentação (R$ 4.383,33);
- os empates de meio centavo (arredondamento `ROUNDED`);
- o saldo truncado pela esquerda;
- o ano bissexto;
- as 11 rejeições, entre elas o saldo não numérico (`COMP-3` inválido, código 21).

Como os testes Java usam o mesmo `casos.csv`, a cadeia de prova fica assim:

```
COBOL original (GnuCOBOL)  ==  casos.csv  ==  servico-juros (Java)
```

## Limites desta prova

- **GnuCOBOL não é o compilador de produção.** O `-std=ibm` aproxima o comportamento do IBM Enterprise COBOL, mas a aritmética intermediária e a potência fracionária (`**`) podem diferir em casos extremos. A validação definitiva é com a saída real do job `JURD0100` no mainframe (`BCO.JUR.APROP.JUROS`), que pode ser acrescentada ao mesmo `casos.csv`.
- A prova cobre a sub-rotina de cálculo (`JURS0100`). A busca de taxa do `JURB0100` é coberta pelos testes do repositório de taxas do serviço.
