# servico-juros

Microserviço de cálculo de encargos de contratos de crédito: juros remuneratórios, juros de mora e multa. É o equivalente Java da sub-rotina **JURS0100** e da busca de taxa do **JURB0100**, do job batch **JURD0100**.

O escopo é a **regra de cálculo**, não o job. O unload do DB2, os sorts, o resumo para a contabilidade e o reprocessamento via GDG continuam no mainframe, e o batch continua oficial. Este serviço é a fase 1 do plano de adoção (modo sombra), descrita no `spec-microservico-java.md`.

## Como rodar

Pré-requisito: Podman ou Docker. Não é preciso ter JDK nem Maven na máquina.

```bash
# build da imagem (compila e roda os 72 testes, inclusive a equivalência com o legado)
podman build -t servico-juros:1.0 .

# sobe o serviço
podman run --rm -p 8080:8080 servico-juros:1.0
```

Com JDK 25 instalado, também dá para rodar direto:

```bash
./mvnw clean verify          # testes
./mvnw spring-boot:run       # aplicação
```

Sem JDK local, os testes rodam no contêiner:

```bash
podman run --rm -v "$PWD":/app:Z -v ~/.m2:/root/.m2:Z -w /app \
  docker.io/library/eclipse-temurin:25-jdk ./mvnw -B verify
```

## Exemplo

O exemplo numérico da Documentação Técnica JURD0100:

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

Mais exemplos, como lote misto, rejeição e consulta de taxa por vigência, estão em `requisicoes.http`.

## Endpoints

| Método | Caminho | Equivalente no legado |
| --- | --- | --- |
| POST | `/v1/encargos/calcular` | Uma iteração do JURB0100 + `CALL JURS0100` |
| POST | `/v1/encargos/calcular-lote` | Até 1.000 contratos; rejeição não interrompe o lote |
| GET | `/v1/taxas/{produto}?data=AAAA-MM-DD` | UNLOAD do STEP020 |
| GET | `/actuator/health`, `/actuator/metrics/juros.calculos`, `/actuator/metrics/juros.rejeicoes` | SYSOUT de totais do STEP040 |
| GET | `/swagger-ui.html` | Documentação OpenAPI |

## Códigos de rejeição

São os mesmos do legado, para conciliar com o arquivo `BCO.JUR.APROP.REJEITOS`:

| Código | Motivo | HTTP |
| --- | --- | --- |
| 01 | Produto sem taxa vigente | 422 |
| 10 | Taxa base fora da faixa (0 a 30% a.m.) | 422 |
| 20 | Saldo zerado ou negativo | 422 |
| 21 | Saldo não numérico | 400 |
| 30 | Data da última apuração inválida | 400 |
| 31 | Data de vencimento inválida | 400 |
| 32 | Data de referência anterior à última apuração | 422 |
| 33 | Data de referência inválida | 400 |
| 40 | Rating não reconhecido | 422 |

Código exclusivo do serviço, sem equivalente no legado:

| Código | Motivo | HTTP |
| --- | --- | --- |
| ENTRADA_INVALIDA | Requisição mal formada, ou saldo com mais de 13 dígitos inteiros, que o COBOL truncaria em silêncio (`DIVERGENCIAS.md`, V1) | 400 |

Saldo em notação científica, hexadecimal ou com mais de 18 dígitos inteiros é tratado como não numérico (código 21). Ver `DECISOES.md`, D12.

## Estrutura

```
src/main/java/br/com/bancoexemplo/juros/
├── dominio/    CalculadoraEncargos (JURS0100), PotenciaFracionaria, CodigoRejeicao, DataLegado. Sem Spring.
├── aplicacao/  CalculoEncargosService (papel do JURB0100)
├── infra/      TaxaProduto, SpreadRating e repositórios (tabelas com vigência)
└── api/        controllers, DTOs, tratamento de erros
src/main/resources/db/migration/   tabelas e carga inicial (Flyway, H2 em memória)
src/test/resources/equivalencia/casos.csv   massa de equivalência com o legado
ferramentas/referencia_jurs0100.py          implementação de referência que gera a massa
```

Cada método do domínio aponta no Javadoc o parágrafo COBOL de origem.

## Massa de equivalência

O `casos.csv` define o resultado esperado de cada caso, e qualquer diferença de um centavo falha o build. Os 27 casos foram conferidos contra a `JURS0100` original compilada com GnuCOBOL (`../equivalencia-cobol/`), com 27 de 27 idênticos. Isso demonstra equivalência com o COBOL compilado em GnuCOBOL, não com o Enterprise COBOL do z/OS: a validação definitiva depende da massa real. Para incluir a massa real do mainframe, basta converter o arquivo `BCO.JUR.APROP.JUROS` (layout JURCSAID) para o mesmo formato e acrescentar as linhas. Detalhes em `DECISOES.md` (D10).

## Segurança

Autenticação e autorização estão fora do escopo desta fase. O ponto de extensão previsto é um `SecurityFilterChain` do Spring Security, com OAuth2 Resource Server (JWT) validando o token do gateway corporativo. Os logs registram só o número do contrato e o código de retorno, sem saldo nem dado pessoal.

## Documentos

- `DECISOES.md`: decisões técnicas (precisão, potência, códigos HTTP, ordem das validações).
- `DIVERGENCIAS.md`: diferenças de comportamento em relação ao legado, para aprovação do negócio.
