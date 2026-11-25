# Spec — Conversion of the interest calculation (JURB0100/JURS0100) into a Java microservice

[🇧🇷 Português](spec-microservico-java.md) | 🇺🇸 English

**Project:** Mainframe Modernization Capstone with AI Agents
**Author:** Jair Valentin, mainframe analyst
**Date:** 2026-11-24
**Phase:** 3 of 3 (1 = inventory, 2 = documentation, 3 = conversion)
**Audience:** AI development agent (Claude) and technical team
**Status:** implemented in `servico-juros/`; equivalence verified against the original COBOL in `equivalencia-cobol/`

> **How this specification was used.** The project follows spec-driven development: the analyst defines the rules, the sources of truth and the acceptance criteria; an AI agent implements from this document; the analyst reviews, decides on divergences and validates the result against the criteria in section 12.

---

## 1. Context

The previous phases produced:

1. the automated inventory of the interest system (`inventario_mainframe.py` → `saida/inventario.json`);
2. the **Technical Documentation — Daily Interest Accrual (JURD0100)**, with business rules RN01 to RN05, the rejection codes, the numerical example and the risks.

This phase closes the loop: **turning what was documented into a Java microservice**, showing that documentation produced with AI assistance is a reliable foundation for modernization.

## 2. Sources of truth (and their priority order)

The implementation must use the three sources below, in this order:

| Priority | Source | Used for |
| --- | --- | --- |
| 1 | COBOL sources in `legado/` (`JURS0100.cbl`, `JURB0100.cbl`, `JURCCALC.cpy`) | Exact behavior: order of validations, rounding, edge conditions |
| 2 | Technical Documentation JURD0100 | Business rules, rejection codes, numerical example, risks |
| 3 | `saida/inventario.json` | Interfaces, layouts, fields and sizes, links between components |

**Golden rule:** if the documentation and the COBOL disagree, **the COBOL wins**. The divergence must be recorded in `DIVERGENCIAS.md` and reported to the responsible analyst. No business rule may be corrected on your own initiative, even if it looks wrong. In a bank, changing a rule is a business decision, not a development one.

## 3. Objective

Build the **`servico-juros`** microservice, which exposes through a REST API the same charges calculation that runs today in the nightly batch job. In practice:

- the logic of the **JURS0100** subroutine becomes the service's domain core;
- the lookup of the current rate by product, which **JURB0100** performs in the batch, becomes a query against a rate repository;
- the service lets digital channels simulate charges in real time **with the same rule as the batch**.

The mainframe batch **keeps running**. This service is the first step of the strangler pattern described in the documentation, not a replacement for the job.

## 4. Stack and technical constraints

- **Java 25 (LTS)**, the JDK installed on the machine.
- **Spring Boot**, the latest stable version compatible with Java 25.
- Build with the **Maven Wrapper** (`./mvnw`); Maven is not installed and must not be required.
- **In-memory H2** database with initial load via script (Flyway or `data.sql`), simulating the DB2 tables.
- **OpenAPI/Swagger** generated from the code.
- Multi-stage **Dockerfile** to build the image (Docker and Podman are available).
- Tests with **JUnit 5**; API tests with MockMvc or RestAssured.
- No calls to external services. Everything runs locally, as with the inventory.
- Code, domain class names and messages in **Portuguese**, to preserve traceability to the COBOL (`CalculadoraEncargos`, `TaxaProduto`, `CodigoRejeicao`).

### Money and precision (non-negotiable)

- **`double` or `float` are forbidden for monetary values and rates.** Use `BigDecimal` everywhere.
- COBOL's `ROUNDED` is equivalent to `RoundingMode.HALF_UP`.
- Scales identical to the COBOL ones:

| Item | COBOL | Java |
| --- | --- | --- |
| Monetary values | `S9(13)V99 COMP-3` | `BigDecimal`, scale 2, `HALF_UP` |
| Rates (%) | `S9(3)V9(4) COMP-3` | `BigDecimal`, scale 4 |
| Exponent days/30 | `S9(3)V9(9)` with `ROUNDED` | scale 9, `HALF_UP` |
| Interest factor | `S9(3)V9(12)` with `ROUNDED` | scale 12, `HALF_UP` |

- **Fractional power:** the COBOL computes `(1 + taxa) ** expoente` using internal floating point. In Java, compute it with `Math.pow` on the converted values and round immediately to scale 12 with `HALF_UP`, just like the COBOL. Isolate this step in a single method (`calcularFatorJuros`) and document it in `DECISOES.md`, because that is where a one-cent difference between the platforms may arise.
- In the other intermediate calculations (late-payment interest, late fee), use `MathContext.DECIMAL128` and round only the final result, as the COBOL does in `COMPUTE ... ROUNDED`.

## 5. Business rules to implement

All according to the documentation and to `JURS0100`, one class or method per rule, with the rule identifier in the Javadoc (`RN01` to `RN05`).

| Rule | Description | Origin in the COBOL |
| --- | --- | --- |
| RN01 | Applied rate = product base rate + rating spread | `2000-APLICAR-SPREAD-RATING` |
| RN02 | Contractual interest = balance × ((1 + rate/100)^(days/30) − 1) | `4000-CALCULAR-JUROS-REMUN` |
| RN03 | Late-payment interest = balance × late-payment rate/100 × days overdue within the period / 30 | `5000-CALCULAR-ENCARGOS-ATRASO` |
| RN04 | Late fee = balance × late fee/100, only when the due date ≥ last accrual date | `5000-CALCULAR-ENCARGOS-ATRASO` |
| RN05 | Total = contractual interest + late-payment interest + late fee; updated balance = balance + total | `6000-TOTALIZAR` |

Details that must be preserved:

- **Days** = difference in calendar days between the reference date and the last accrual date (equivalent to `INTEGER-OF-DATE`; in Java, `ChronoUnit.DAYS.between`).
- **Days = 0** → contractual interest is zero, without computing the power.
- **Overdue** status exists when reference date > due date. The days overdue taken into account are the **smaller** of the days overdue and the days in the period.
- **Contract up to date** → late-payment interest and late fee are zero.

### Rating spread — resolving risk #1 from the documentation

In the COBOL the spread is hardcoded; the documentation classifies this as a high-severity risk. In the microservice:

- the spread moves to a **table with a validity period** (`TB_SPREAD_RATING`: rating, percentage, validity start and end), read by the repository;
- the initial load uses exactly the current COBOL values:

| Rating | AA | A | B | C | D | E | F | G | H |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Spread (% per month) | 0.0000 | 0.1000 | 0.2500 | 0.5000 | 0.7500 | 1.0000 | 1.2500 | 1.5000 | 2.0000 |

The rating arrives at the API without the COBOL padding spaces (`"A"`, not `"A "`). Apply `trim` on input.

### Reference date — resolving risk #2

The reference date is **mandatory in the request**; the service does not use the system date. It determines the validity period of the rate **and** of the spread, the same value for both, so that the JCL's "date typed in two places" problem does not exist here.

### 500-product limit — resolving risk #3

The rate repository has no fixed limit. The lookup is done by product and date, not by loading the whole table into memory.

## 6. Validations and return codes

Keep **the same codes as the legacy**. This is what makes it possible to reconcile the service's results with the batch rejects file. The order of validations must be the same as in `1000-VALIDAR-ENTRADA` and `1100-VALIDAR-DATAS`, because when there is more than one error the returned code must be the same.

| Code | Message | HTTP |
| --- | --- | --- |
| 01 | Produto sem taxa vigente cadastrada (no current rate registered for the product) | 422 |
| 10 | Taxa base fora da faixa permitida (0 a 30% a.m.) (base rate outside the allowed range, 0 to 30% per month) | 422 |
| 20 | Saldo devedor zerado ou negativo (outstanding balance zero or negative) | 422 |
| 21 | Saldo devedor com conteúdo não numérico (outstanding balance with non-numeric content) | 400 |
| 30 | Data da última apuração inválida (invalid last accrual date) | 400 |
| 31 | Data de vencimento inválida (invalid due date) | 400 |
| 32 | Data de referência anterior à última apuração (reference date earlier than the last accrual) | 422 |
| 33 | Data de referência inválida (invalid reference date) | 400 |
| 40 | Rating de risco não reconhecido (unrecognized risk rating) | 422 |

Standard error body:

```json
{ "codigo": "20", "mensagem": "Saldo devedor zerado ou negativo", "contrato": "000012345678" }
```

Create a `CodigoRejeicao` enum with this table, with no messages scattered through the code.

## 7. API

### 7.1 `POST /v1/encargos/calcular`

Calculates the charges for one contract. Equivalent to one iteration of `JURB0100` plus the `CALL JURS0100`.

Request (the numerical example from the documentation):

```json
{
  "numeroContrato": "000012345678",
  "codigoProduto": "CDC",
  "rating": "B",
  "saldoDevedor": 100000.00,
  "dataUltimaApuracao": "2026-10-25",
  "dataVencimento": "2026-11-14",
  "dataReferencia": "2026-11-24"
}
```

Expected response (200), given product `CDC` with a rate of 1.80% per month, late-payment interest of 1% per month and a late fee of 2%:

```json
{
  "numeroContrato": "000012345678",
  "taxaAplicada": 2.0500,
  "dias": 30,
  "diasAtraso": 10,
  "emAtraso": true,
  "jurosRemuneratorios": 2050.00,
  "jurosMora": 333.33,
  "multa": 2000.00,
  "totalEncargos": 4383.33,
  "saldoAtualizado": 104383.33,
  "regraVersao": "JURS0100-equivalente-1.0"
}
```

### 7.2 `POST /v1/encargos/calcular-lote`

Accepts up to 1,000 contracts and returns, for each one, either the result or the error with the legacy code, **without aborting the batch** because of one invalid contract. This is the same behavior as the nightly batch job, which rejects the contract and moves on.

### 7.3 `GET /v1/taxas/{codigoProduto}?data=AAAA-MM-DD`

Returns the product's rate, late-payment interest rate and late fee in effect on the given date (equivalent to the STEP020 UNLOAD).

### 7.4 Operations
- `GET /actuator/health` and basic metrics (number of calculations, number of rejections per code).
- Structured logs with the contract number and the return code; **never log the balance or personal data**.

## 8. Code architecture

The domain is isolated from Spring: the calculation must be testable without starting the application.

```
servico-juros/
├── src/main/java/br/com/bancoexemplo/juros/
│   ├── dominio/        # CalculadoraEncargos, RegrasJuros, CodigoRejeicao, input and output records (no Spring)
│   ├── aplicacao/      # CalculoEncargosService: fetches rate and spread, calls the domain (the role of JURB0100)
│   ├── infra/          # JPA repositories for TaxaProduto and SpreadRating
│   └── api/            # controllers, DTOs, error handling
├── src/main/resources/ # application.yml, initial table load
├── src/test/java/...   # domain, equivalence and API tests
├── src/test/resources/equivalencia/casos.csv
├── Dockerfile
├── README.md
├── DECISOES.md
└── DIVERGENCIAS.md
```

Traceability: each domain method carries the originating COBOL paragraph in its Javadoc (for example, `@see JURS0100 4000-CALCULAR-JUROS-REMUN`).

## 9. Tests (the main criterion of the demonstration)

### 9.1 Rule tests
One test per rule and per return code, including the edge cases:
- days = 0 (same day as the last accrual);
- due date equal to the last accrual date (late fee is charged);
- due date earlier than the last accrual (delinquency carried over from before: late-payment interest yes, late fee no);
- delay longer than the period (late-payment interest capped at the days in the period);
- each rating from AA to H, plus an invalid rating;
- base rate 0 and above 30;
- two validations failing at the same time (the code of the first one in COBOL order wins).

### 9.2 Equivalence tests against the legacy
File `src/test/resources/equivalencia/casos.csv`, with one line per case: input plus expected values. The parameterized test compares **to the cent**; any difference fails the build.

Cases required from the start (calculated from the documentation):

| Case | Summarized input | Expected |
| --- | --- | --- |
| Documentation example | balance 100,000.00, rate 1.80, rating B, 30 days, 10 overdue, late-payment interest 1%, late fee 2% | contractual 2,050.00; late-payment 333.33; late fee 2,000.00; total 4,383.33 |
| Daily routine, up to date | balance 100,000.00, rate 1.80, rating B, 1 day, not overdue | contractual 67.67; total 67.67 |

When the dataset extracted from an actual run of JURB0100 on the mainframe becomes available (the JUROSOUT file converted to CSV), it will be appended to this same file, with no code changes.

### 9.3 API tests
Real calls to the endpoints with the example from section 7.1, a rejected contract and a mixed batch (valid and invalid).

## 10. Explicit constraints (do not)

- Monetary value in `double`.
- Rule change without an entry in `DIVERGENCIAS.md`.
- Error messages and codes different from the legacy ones.
- Dependency on an external or cloud service.
- Unrequested business "improvements", such as exact daily interest (365-day basis) or banker's rounding (`HALF_EVEN`).

## 11. Out of scope

- Rewriting the JCL UNLOAD and SORT steps; the batch stays on the mainframe.
- Integration with Accounting (job CTBD0300).
- Authentication and authorization. Leave only an extension point documented in the README.
- EBCDIC/COMP-3 conversion of real files (this will come in the equivalence testing phase with production data).

## 12. Acceptance criteria

1. `./mvnw clean verify` passes with no failing tests.
2. The documentation example returns exactly 2,050.00 / 333.33 / 2,000.00 / 4,383.33 / 104,383.33.
3. The daily routine (1 day, up to date) returns 67.67.
4. The 9 legacy rejection codes have tests and are returned with the HTTP status from section 6.
5. No `double` or `float` in monetary values (except inside `calcularFatorJuros`, documented).
6. The spread comes from the table with a validity period, not from the code.
7. A batch with an invalid contract in the middle returns the others calculated.
8. The Docker image starts and responds on `/actuator/health`.
9. `README.md` explains how to run it and shows a `curl` with the example; `DECISOES.md` records the technical decisions (precision, power, HTTP codes); `DIVERGENCIAS.md` exists, even if empty.

## 13. Adoption plan

| Phase | What happens | Criterion to move forward |
| --- | --- | --- |
| 1. Shadow | The batch remains the official one; the same contracts go through the service and the results are compared | 30 days with zero difference |
| 2. Simulation | Digital channels start using the service to simulate charges | Approval from the Products area and from Audit |
| 3. Replacement | STEP040 calls the service, or the calculation migrates for good | Architecture decision, based on the history from phase 1 |
