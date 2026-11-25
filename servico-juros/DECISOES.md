# Decisões técnicas — servico-juros

Registro das decisões tomadas na conversão do JURB0100/JURS0100. Cada uma referencia a seção do `spec-microservico-java.md` que a motivou.

## D1 — `BigDecimal` com as escalas do COBOL (spec §4)

| Item | COBOL | Java |
| --- | --- | --- |
| Valores monetários | `S9(13)V99 COMP-3` | escala 2, `HALF_UP` |
| Taxas | `S9(3)V9(4) COMP-3` | escala 4 |
| Expoente dias/30 | `S9(3)V9(9)` `ROUNDED` | escala 9, `HALF_UP` |
| Fator de juros | `S9(3)V9(12)` `ROUNDED` | escala 12, `HALF_UP` |

Os cálculos intermediários de mora e multa usam `MathContext.DECIMAL128` (34 dígitos), na mesma ordem dos operandos do `COMPUTE`, e arredondam só no fim.

## D2 — Potência fracionária em `double`, num único ponto (spec §4)

`(1 + taxa/100) ^ (dias/30)` não tem solução exata em `BigDecimal` para expoente fracionário. O Enterprise COBOL também resolve esse `**` em ponto flutuante. A conta fica isolada em `PotenciaFracionaria.calcularFatorJuros`: `Math.pow`, conversão exata com `new BigDecimal(double)` e arredondamento imediato para escala 12.

É o único arquivo de produção com `double`, e o teste `DinheiroSemDoubleTest` garante isso. Se aparecer diferença de centavo contra a massa real do mainframe, a investigação começa aqui.

## D3 — Saldo e datas recebidos como texto (spec §6)

`saldoDevedor` e as três datas chegam como `String` no JSON. Os motivos:

- quem valida é o domínio, com os mesmos códigos e a mesma ordem do COBOL (21, 30, 31, 33);
- no lote, uma data mal formada num contrato vira rejeição daquele contrato, em vez de derrubar a requisição inteira por erro de desserialização.

O saldo também é aceito como número JSON (`100000.00`) e segue a semântica do `MOVE` para `S9(13)V99`: trunca além da 2ª casa decimal e além do 13º dígito inteiro, sem aviso (DIVERGENCIAS V1). As datas seguem `AAAA-MM-DD` estrito, com validação de calendário: `2026-02-30` é inválida, como no `TEST-DATE-YYYYMMDD`.

## D4 — Erros de estrutura da requisição: `ENTRADA_INVALIDA` (spec §6)

O legado não tem código para "número do contrato ausente" ou "JSON mal formado", porque isso não existe num arquivo de layout fixo. Esses casos devolvem HTTP 400 com `codigo = "ENTRADA_INVALIDA"`, para não misturar com os códigos de negócio 01 a 40.

## D5 — Ordem das validações (spec §6)

Dentro do domínio, a ordem é a do COBOL: 21, 20, 10, 30, 31, 33, 32 e 40. Na camada de aplicação, antes do domínio, vêm:

1. **33 (data de referência inválida):** sem uma data válida não há como saber qual taxa está vigente. No legado, a data vem no PARM e o JURB0100 aborta o job inteiro se ela estiver errada.
2. **01 (produto sem taxa):** no legado também é verificado antes do `CALL JURS0100`.

## D6 — HTTP por código

Seguimos a tabela do spec: 422 para regra de negócio (01, 10, 20, 32, 40) e 400 para dado mal formado (21, 30, 31, 33). Na consulta `GET /v1/taxas/{produto}`, produto sem taxa devolve **404** com código 01, porque ali é uma busca de recurso, não um cálculo.

## D7 — Rating: `trim`, sem conversão de maiúsculas

O COBOL compara `'B '` com `'B '`. Removemos os espaços de preenchimento, mas **não** convertemos minúsculas: `"b"` é rejeitado com 40, como seria no legado.

## D8 — Spread e taxas com vigência, consultados por data de referência (spec §5)

- `TB_SPREAD_RATING` recebe os valores exatos do `EVALUATE` da JURS0100. As datas de início seguem o histórico de alterações do fonte: 2019-05-08 para AA a E e 2021-02-11 para F, G e H.
- No lote, a tabela de spread é lida uma vez por data de referência.
- As taxas são consultadas por produto e data, sem limite de 500 produtos.
- Se houver mais de uma taxa vigente para o mesmo produto e data, o serviço falha com erro interno, como o legado faz ao abortar com RC 16.

## D9 — Build e testes em contêiner

A estação tem só o JRE 25, sem `javac`. O build roda no contêiner `eclipse-temurin:25-jdk`, com Podman, e o Maven vem pelo `mvnw`. O Dockerfile multi-stage roda os testes durante o build da imagem: imagem sem equivalência validada não é gerada.

## D10 — Origem da massa de equivalência

`src/test/resources/equivalencia/casos.csv` tem 27 casos:

- 2 vêm diretamente da Documentação Técnica JURD0100 (R$ 4.383,33 e R$ 67,67);
- os outros 25 (bordas, empates de meio centavo e rejeições) foram gerados por `ferramentas/referencia_jurs0100.py`, uma implementação de referência em Python, independente do Java, escrita a partir da semântica do COBOL.

**Validação contra o COBOL real (25/11/2026).** Os 27 casos foram executados na `JURS0100` original, compilada com GnuCOBOL 3.2 em modo `-std=ibm` (pasta `equivalencia-cobol/` na raiz do projeto). Os 27 bateram com o `casos.csv` em todos os campos, então a massa deixou de depender só da implementação de referência.

**Isso ainda não substitui a massa real**, porque GnuCOBOL não é o compilador de produção. O próximo passo é extrair o JUROSOUT de uma execução do JURD0100 no mainframe, converter de EBCDIC/COMP-3 para CSV e acrescentar as linhas ao mesmo arquivo.

## D11 — Casos de empate de meio centavo

Um teste de mutação (trocar `HALF_UP` por `HALF_EVEN` na calculadora) mostrou que a primeira versão da massa não detectava a troca: nenhum caso caía exatamente no meio centavo. Foram incluídos `empate_meio_centavo_multa` (multa de 2,005 → 2,01) e `empate_meio_centavo_mora` (mora de 0,005 → 0,01). Com eles, a mesma mutação derruba 2 casos.

Quando a massa real do mainframe chegar, vale repetir esse teste de mutação para confirmar que ela também cobre os empates.
