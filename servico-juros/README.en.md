# servico-juros

[🇧🇷 Português](README.md) | 🇺🇸 English

A microservice that calculates charges on credit contracts: contractual interest, late-payment interest and late fee. It is the Java equivalent of the **JURS0100** subroutine and of the rate lookup in **JURB0100**, from the **JURD0100** batch job.

The scope is the **calculation rule**, not the job. The DB2 unload, the sorts, the summary for accounting and the GDG-based reprocessing remain on the mainframe, and the batch remains the system of record. This service is phase 1 of the adoption plan (shadow mode), described in `spec-microservico-java.en.md`.

## How to run

Prerequisite: Podman or Docker. No JDK or Maven needed on the machine.

```bash
# build the image (compiles and runs the 72 tests, including equivalence with the legacy)
podman build -t servico-juros:1.0 .

# start the service
podman run --rm -p 8080:8080 servico-juros:1.0
```

With JDK 25 installed, you can also run it directly:

```bash
./mvnw clean verify          # tests
./mvnw spring-boot:run       # application
```

Without a local JDK, the tests run in a container:

```bash
podman run --rm -v "$PWD":/app:Z -v ~/.m2:/root/.m2:Z -w /app \
  docker.io/library/eclipse-temurin:25-jdk ./mvnw -B verify
```

## Example

The worked example from the JURD0100 Technical Documentation:

```bash
curl -s -X POST localhost:8080/v1/encargos/calcular \
  -H 'Content-Type: application/json' \
  -d '{"numeroContrato":"000012345678","codigoProduto":"CDC","rating":"B",
       "saldoDevedor":100000.00,"dataUltimaApuracao":"2026-10-25",
       "dataVencimento":"2026-11-14","dataReferencia":"2026-11-24"}'
```

```json
{"numeroContrato":"000012345678","taxaAplicada":2.0500,"dias":30,"diasAtraso":10,"emAtraso":true,
 "jurosRemuneratorios":2050.00,"jurosMora":333.33,"multa":2000.00,"totalEncargos":4383.33,
 "saldoAtualizado":104383.33,"regraVersao":"JURS0100-equivalente-1.0"}
```

More examples, such as a mixed batch, a rejection and a rate lookup by validity period, are in `requisicoes.http`.

## Endpoints

| Method | Path | Legacy equivalent |
| --- | --- | --- |
| POST | `/v1/encargos/calcular` | One iteration of JURB0100 + `CALL JURS0100` |
| POST | `/v1/encargos/calcular-lote` | Up to 1,000 contracts; a rejection does not stop the batch |
| GET | `/v1/taxas/{produto}?data=AAAA-MM-DD` | UNLOAD in STEP020 |
| GET | `/actuator/health`, `/actuator/metrics/juros.calculos`, `/actuator/metrics/juros.rejeicoes` | STEP040 totals SYSOUT |
| GET | `/swagger-ui.html` | OpenAPI documentation |

## Rejection codes

They are the same as in the legacy, so results can be reconciled with the `BCO.JUR.APROP.REJEITOS` file:

| Code | Reason | HTTP |
| --- | --- | --- |
| 01 | Product has no rate in effect | 422 |
| 10 | Base rate out of range (0 to 30% per month) | 422 |
| 20 | Zero or negative balance | 422 |
| 21 | Non-numeric balance | 400 |
| 30 | Invalid last accrual date | 400 |
| 31 | Invalid due date | 400 |
| 32 | Reference date earlier than the last accrual date | 422 |
| 33 | Invalid reference date | 400 |
| 40 | Unrecognized rating | 422 |

Service-only code, with no legacy equivalent:

| Code | Reason | HTTP |
| --- | --- | --- |
| ENTRADA_INVALIDA | Malformed request, or a balance with more than 13 integer digits, which the COBOL would silently truncate (`DIVERGENCIAS.en.md`, V1) | 400 |

A balance in scientific notation, in hexadecimal or with more than 18 integer digits is treated as non-numeric (code 21). See `DECISOES.en.md`, D12.

## Structure

```
src/main/java/br/com/bancoexemplo/juros/
├── dominio/    CalculadoraEncargos (JURS0100), PotenciaFracionaria, CodigoRejeicao, DataLegado. No Spring.
├── aplicacao/  CalculoEncargosService (plays the role of JURB0100)
├── infra/      TaxaProduto, SpreadRating and repositories (tables with validity periods)
└── api/        controllers, DTOs, error handling
src/main/resources/db/migration/   tables and initial load (Flyway, in-memory H2)
src/test/resources/equivalencia/casos.csv   equivalence dataset against the legacy
ferramentas/referencia_jurs0100.py          reference implementation that generates the dataset
```

Each domain method's Javadoc points to the COBOL paragraph it comes from.

## Equivalence dataset

`casos.csv` defines the expected result for each case, and any one-cent difference fails the build. All 27 cases were checked against the original `JURS0100` compiled with GnuCOBOL (`../equivalencia-cobol/`), with 27 out of 27 identical. This demonstrates equivalence with COBOL compiled by GnuCOBOL, not with z/OS Enterprise COBOL: definitive validation depends on real data. To add real mainframe data, simply convert the `BCO.JUR.APROP.JUROS` file (JURCSAID layout) to the same format and append the rows. Details in `DECISOES.en.md` (D10).

## Security

Authentication and authorization are out of scope for this phase. The planned extension point is a Spring Security `SecurityFilterChain`, with an OAuth2 Resource Server (JWT) validating the token issued by the corporate gateway. Logs record only the contract number and the return code, with no balance or personal data.

## Documents

- `DECISOES.en.md`: technical decisions (precision, exponentiation, HTTP codes, validation order).
- `DIVERGENCIAS.en.md`: behavioral differences from the legacy, pending business approval.
