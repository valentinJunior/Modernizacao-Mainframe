# Divergences from the legacy

[🇧🇷 Português](DIVERGENCIAS.md) | 🇺🇸 English

Every difference in behavior between `servico-juros` and JURB0100/JURS0100 is recorded here, for a decision by the business area. No calculation rule (RN01 to RN05) was changed. Resolved rows stay in the table as history.

| # | Situation | Legacy (COBOL) | Java service | Status |
| --- | --- | --- | --- | --- |
| V1 | Balance with more than 13 integer digits | The `MOVE` to `S9(13)V99` truncates the leftmost digits **silently**, and the calculation proceeds with the truncated balance | **Domain identical to the legacy** (truncates from the left: 12,345,678,901,234.00 becomes 2,345,678,901,234.00), but **the API rejects** the value with HTTP 400, `ENTRADA_INVALIDA` | Revised on 2026-11-25. On 2026-11-24 the decision was to keep fidelity in the API as well. An external review pointed out that repeating the truncation in a new interface means being faithful to a bug. Fidelity remains in the domain, covered by the `saldo_acima_de_13_inteiros_truncado` case in the equivalence dataset; the API boundary rejects the value. In a batch request, only the affected contract is rejected |
| V2 | Rating spread | Hardcoded (`EVALUATE`) | `TB_SPREAD_RATING` table with validity period, with the same values | Requested in the spec (§5, risk #1). Identical result with the initial load |
| V3 | Request without a contract number, or invalid JSON | Does not exist (fixed-layout file) | HTTP 400, `ENTRADA_INVALIDA` | No equivalent in the legacy (DECISOES.en.md D4) |

No divergence was found between the Technical Documentation and the COBOL code during the conversion.
