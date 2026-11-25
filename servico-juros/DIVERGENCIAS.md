# Divergências em relação ao legado

🇧🇷 Português | [🇺🇸 English](DIVERGENCIAS.en.md)

Toda diferença de comportamento entre o `servico-juros` e o JURB0100/JURS0100 é registrada aqui, para decisão da área de negócio. Nenhuma regra de cálculo (RN01 a RN05) foi alterada. Linhas resolvidas ficam na tabela como histórico.

| # | Situação | Legado (COBOL) | Serviço Java | Status |
| --- | --- | --- | --- | --- |
| V1 | Saldo com mais de 13 dígitos inteiros | O `MOVE` para `S9(13)V99` trunca os dígitos da esquerda **sem aviso**, e o cálculo segue com o saldo truncado | **Domínio igual ao legado** (trunca pela esquerda: 12.345.678.901.234,00 vira 2.345.678.901.234,00), mas **a API recusa** o valor com HTTP 400, `ENTRADA_INVALIDA` | Revista em 25/11/2026. Em 24/11 a decisão foi manter a fidelidade também na API. Uma revisão externa apontou que repetir o truncamento numa interface nova é ser fiel a um bug. A fidelidade continua no domínio, coberta pelo caso `saldo_acima_de_13_inteiros_truncado` da massa de equivalência; a borda da API recusa o valor. No lote, só o contrato afetado é recusado |
| V2 | Spread por rating | Fixo no código (`EVALUATE`) | Tabela `TB_SPREAD_RATING` com vigência, com os mesmos valores | Pedido no spec (§5, risco nº 1). Resultado idêntico com a carga inicial |
| V3 | Requisição sem número de contrato ou JSON inválido | Não existe (arquivo de layout fixo) | HTTP 400, `ENTRADA_INVALIDA` | Sem equivalente no legado (DECISOES D4) |

Nenhuma divergência foi encontrada entre a Documentação Técnica e o código COBOL durante a conversão.
