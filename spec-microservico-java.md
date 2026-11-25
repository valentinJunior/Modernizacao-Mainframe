# Spec — Conversão do cálculo de juros (JURB0100/JURS0100) para microserviço Java

**Projeto:** Capstone de Modernização Mainframe com Agentes de IA
**Autor:** Jair Valentin, analista mainframe
**Data:** 24/11/2026
**Fase:** 3 de 3 (1 = inventário, 2 = documentação, 3 = conversão)
**Destinatários:** agente de IA de desenvolvimento (Claude) e equipe técnica
**Status:** implementada em `servico-juros/`; equivalência verificada contra o COBOL original em `equivalencia-cobol/`

> **Como esta especificação foi usada.** O projeto segue desenvolvimento guiado por especificação: o analista define as regras, as fontes de verdade e os critérios de aceite; um agente de IA implementa a partir deste documento; o analista revisa, decide as divergências e valida o resultado contra os critérios da seção 12.

---

## 1. Contexto

As fases anteriores produziram:

1. o inventário automático do sistema de juros (`inventario_mainframe.py` → `saida/inventario.json`);
2. a **Documentação Técnica — Apropriação Diária de Juros (JURD0100)**, com as regras RN01 a RN05, os códigos de rejeição, o exemplo numérico e os riscos.

Esta fase fecha o ciclo: **transformar o que foi documentado num microserviço Java**, demonstrando que a documentação produzida com apoio de IA é uma base confiável para a modernização.

## 2. Fontes de verdade (e a ordem de prioridade)

A implementação deve usar as três fontes abaixo, nesta ordem:

| Prioridade | Fonte | Para quê |
| --- | --- | --- |
| 1 | Fontes COBOL em `legado/` (`JURS0100.cbl`, `JURB0100.cbl`, `JURCCALC.cpy`) | Comportamento exato: ordem das validações, arredondamentos, condições de borda |
| 2 | Documentação Técnica JURD0100 | Regras de negócio, códigos de rejeição, exemplo numérico, riscos |
| 3 | `saida/inventario.json` | Interfaces, layouts, campos e tamanhos, ligações entre componentes |

**Regra de ouro:** se a documentação e o COBOL divergirem, **vale o COBOL**. A divergência deve ser registrada em `DIVERGENCIAS.md` e comunicada ao analista responsável. Nenhuma regra de negócio deve ser corrigida por iniciativa própria, mesmo que pareça errada. Em banco, mudar regra é decisão de negócio, não de desenvolvimento.

## 3. Objetivo

Criar o microserviço **`servico-juros`**, que expõe via API REST o mesmo cálculo de encargos que hoje roda no batch noturno. Na prática:

- a lógica da sub-rotina **JURS0100** vira o núcleo de domínio do serviço;
- a busca da taxa vigente por produto, que o **JURB0100** faz no batch, vira consulta a um repositório de taxas;
- o serviço permite que os canais digitais simulem encargos em tempo real **com a mesma regra do batch**.

O batch mainframe **continua rodando**. Este serviço é o primeiro passo do strangler pattern descrito na documentação, e não a substituição do job.

## 4. Stack e restrições técnicas

- **Java 25 (LTS)**, o JDK instalado na máquina.
- **Spring Boot**, na versão estável mais recente compatível com Java 25.
- Build com **Maven Wrapper** (`./mvnw`); o Maven não está instalado e não deve ser exigido.
- Banco **H2 em memória** com carga inicial via script (Flyway ou `data.sql`), simulando as tabelas DB2.
- **OpenAPI/Swagger** gerado a partir do código.
- **Dockerfile** multi-stage para gerar a imagem (Docker e Podman estão disponíveis).
- Testes com **JUnit 5**; testes de API com MockMvc ou RestAssured.
- Sem chamadas a serviços externos. Tudo roda localmente, como no inventário.
- Código, nomes de classes de domínio e mensagens em **português**, para manter a rastreabilidade com o COBOL (`CalculadoraEncargos`, `TaxaProduto`, `CodigoRejeicao`).

### Dinheiro e precisão (inegociável)

- **Proibido `double` ou `float` para valores monetários e taxas.** Use `BigDecimal` em tudo.
- O `ROUNDED` do COBOL equivale a `RoundingMode.HALF_UP`.
- Escalas iguais às do COBOL:

| Item | COBOL | Java |
| --- | --- | --- |
| Valores monetários | `S9(13)V99 COMP-3` | `BigDecimal`, escala 2, `HALF_UP` |
| Taxas (%) | `S9(3)V9(4) COMP-3` | `BigDecimal`, escala 4 |
| Expoente dias/30 | `S9(3)V9(9)` com `ROUNDED` | escala 9, `HALF_UP` |
| Fator de juros | `S9(3)V9(12)` com `ROUNDED` | escala 12, `HALF_UP` |

- **Potência fracionária:** o COBOL calcula `(1 + taxa) ** expoente` com ponto flutuante interno. Em Java, calcule com `Math.pow` sobre os valores convertidos e arredonde imediatamente para a escala 12 com `HALF_UP`, igual ao COBOL. Isolar esse ponto num único método (`calcularFatorJuros`) e documentar em `DECISOES.md`, porque é ali que pode surgir diferença de centavo entre as plataformas.
- Nos demais cálculos intermediários (mora, multa), use `MathContext.DECIMAL128` e arredonde só no resultado final, como o COBOL faz no `COMPUTE ... ROUNDED`.

## 5. Regras de negócio a implementar

Todas conforme a documentação e o `JURS0100`, uma classe ou método por regra e com o identificador da regra no Javadoc (`RN01` a `RN05`).

| Regra | Descrição | Origem no COBOL |
| --- | --- | --- |
| RN01 | Taxa aplicada = taxa base do produto + spread do rating | `2000-APLICAR-SPREAD-RATING` |
| RN02 | Juros remuneratórios = saldo × ((1 + taxa/100)^(dias/30) − 1) | `4000-CALCULAR-JUROS-REMUN` |
| RN03 | Juros de mora = saldo × mora/100 × dias de atraso no período / 30 | `5000-CALCULAR-ENCARGOS-ATRASO` |
| RN04 | Multa = saldo × multa/100, só quando o vencimento ≥ data da última apuração | `5000-CALCULAR-ENCARGOS-ATRASO` |
| RN05 | Total = remuneratórios + mora + multa; saldo atualizado = saldo + total | `6000-TOTALIZAR` |

Detalhes que precisam ser preservados:

- **Dias** = diferença em dias corridos entre a data de referência e a da última apuração (equivalente ao `INTEGER-OF-DATE`; em Java, `ChronoUnit.DAYS.between`).
- **Dias = 0** → juros remuneratórios zero, sem calcular a potência.
- **Atraso** existe quando data de referência > vencimento. Os dias de atraso considerados são o **menor** entre os dias de atraso e os dias do período.
- **Contrato em dia** → mora e multa zero.

### Spread por rating — resolver o risco nº 1 da documentação

No COBOL o spread está fixo no código; na documentação isso está classificado como risco de severidade alta. No microserviço:

- o spread vai para uma **tabela com vigência** (`TB_SPREAD_RATING`: rating, percentual, início e fim de vigência), lida pelo repositório;
- a carga inicial usa exatamente os valores atuais do COBOL:

| Rating | AA | A | B | C | D | E | F | G | H |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Spread (% a.m.) | 0,0000 | 0,1000 | 0,2500 | 0,5000 | 0,7500 | 1,0000 | 1,2500 | 1,5000 | 2,0000 |

O rating chega na API sem os espaços do COBOL (`"A"`, não `"A "`). Faça o `trim` na entrada.

### Data de referência — resolver o risco nº 2

A data de referência é **obrigatória na requisição**; o serviço não usa a data do sistema. Ela define a vigência da taxa **e** do spread, o mesmo valor para os dois, para que o problema de "data digitada em dois lugares" do JCL não exista aqui.

### Limite de 500 produtos — resolver o risco nº 3

O repositório de taxas não tem limite fixo. A consulta é feita por produto e data, e não carregando a tabela inteira em memória.

## 6. Validações e códigos de retorno

Manter **os mesmos códigos do legado**. Isso é o que permite conciliar o resultado do serviço com o arquivo de rejeitados do batch. A ordem das validações tem que ser a mesma do `1000-VALIDAR-ENTRADA` e do `1100-VALIDAR-DATAS`, porque quando há mais de um erro o código devolvido precisa ser o mesmo.

| Código | Mensagem | HTTP |
| --- | --- | --- |
| 01 | Produto sem taxa vigente cadastrada | 422 |
| 10 | Taxa base fora da faixa permitida (0 a 30% a.m.) | 422 |
| 20 | Saldo devedor zerado ou negativo | 422 |
| 21 | Saldo devedor com conteúdo não numérico | 400 |
| 30 | Data da última apuração inválida | 400 |
| 31 | Data de vencimento inválida | 400 |
| 32 | Data de referência anterior à última apuração | 422 |
| 33 | Data de referência inválida | 400 |
| 40 | Rating de risco não reconhecido | 422 |

Corpo de erro padrão:

```json
{ "codigo": "20", "mensagem": "Saldo devedor zerado ou negativo", "contrato": "000012345678" }
```

Criar um enum `CodigoRejeicao` com essa tabela, sem mensagem espalhada pelo código.

## 7. API

### 7.1 `POST /v1/encargos/calcular`

Calcula os encargos de um contrato. Equivale a uma iteração do `JURB0100` mais o `CALL JURS0100`.

Requisição (o exemplo numérico da documentação):

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

Resposta esperada (200), considerando o produto `CDC` com taxa de 1,80% a.m., mora de 1% a.m. e multa de 2%:

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

Recebe até 1.000 contratos e devolve, para cada um, o resultado ou o erro com o código do legado, **sem interromper o lote** por causa de um contrato inválido. É o mesmo comportamento do batch, que rejeita o contrato e segue.

### 7.3 `GET /v1/taxas/{codigoProduto}?data=AAAA-MM-DD`

Retorna a taxa, a mora e a multa vigentes do produto na data (equivalente ao UNLOAD do STEP020).

### 7.4 Operação
- `GET /actuator/health` e métricas básicas (quantidade de cálculos, quantidade de rejeições por código).
- Logs estruturados com o número do contrato e o código de retorno; **sem logar saldo ou dados pessoais**.

## 8. Arquitetura do código

O domínio fica isolado do Spring: o cálculo tem que ser testável sem subir a aplicação.

```
servico-juros/
├── src/main/java/br/com/bancoexemplo/juros/
│   ├── dominio/        # CalculadoraEncargos, RegrasJuros, CodigoRejeicao, records de entrada e saída (sem Spring)
│   ├── aplicacao/      # CalculoEncargosService: busca taxa e spread, chama o domínio (papel do JURB0100)
│   ├── infra/          # repositórios JPA de TaxaProduto e SpreadRating
│   └── api/            # controllers, DTOs, tratamento de erros
├── src/main/resources/ # application.yml, carga inicial das tabelas
├── src/test/java/...   # testes de domínio, de equivalência e de API
├── src/test/resources/equivalencia/casos.csv
├── Dockerfile
├── README.md
├── DECISOES.md
└── DIVERGENCIAS.md
```

Rastreabilidade: cada método do domínio leva no Javadoc o parágrafo COBOL de origem (por exemplo, `@see JURS0100 4000-CALCULAR-JUROS-REMUN`).

## 9. Testes (critério principal da demonstração)

### 9.1 Testes de regra
Um teste por regra e por código de retorno, incluindo as bordas:
- dias = 0 (mesmo dia da última apuração);
- vencimento igual à data da última apuração (cobra multa);
- vencimento anterior à última apuração (atraso que vem de antes: mora sim, multa não);
- atraso maior que o período (mora limitada aos dias do período);
- cada rating de AA a H e um rating inválido;
- taxa base 0 e acima de 30;
- duas validações falhando ao mesmo tempo (vale o código da primeira na ordem do COBOL).

### 9.2 Testes de equivalência com o legado
Arquivo `src/test/resources/equivalencia/casos.csv`, com uma linha por caso: entrada mais os valores esperados. O teste parametrizado compara **centavo a centavo**; qualquer diferença falha o build.

Casos obrigatórios desde já (calculados a partir da documentação):

| Caso | Entrada resumida | Esperado |
| --- | --- | --- |
| Exemplo da documentação | saldo 100.000,00, taxa 1,80, rating B, 30 dias, 10 de atraso, mora 1%, multa 2% | remun. 2.050,00; mora 333,33; multa 2.000,00; total 4.383,33 |
| Rotina diária em dia | saldo 100.000,00, taxa 1,80, rating B, 1 dia, sem atraso | remun. 67,67; total 67,67 |

Quando a massa extraída da execução real do JURB0100 no mainframe estiver disponível (arquivo JUROSOUT convertido para CSV), ela será acrescentada a este mesmo arquivo, sem mudança de código.

### 9.3 Testes de API
Chamada real dos endpoints com o exemplo da seção 7.1, um contrato rejeitado e um lote misto (válidos e inválidos).

## 10. Restrições explícitas (não fazer)

- Valor monetário em `double`.
- Mudança de regra sem registro em `DIVERGENCIAS.md`.
- Mensagens e códigos de erro diferentes dos do legado.
- Dependência de serviço externo ou de nuvem.
- "Melhorias" de negócio não pedidas, como juros diários exatos (base 365) ou arredondamento bancário (`HALF_EVEN`).

## 11. Fora do escopo

- Reescrever os steps de UNLOAD e SORT do JCL; o batch continua no mainframe.
- Integração com a Contabilidade (job CTBD0300).
- Autenticação e autorização. Deixar só um ponto de extensão documentado no README.
- Conversão de EBCDIC/COMP-3 de arquivos reais (vai entrar na fase de testes de equivalência com massa de produção).

## 12. Critérios de aceite

1. `./mvnw clean verify` passa sem nenhum teste falhando.
2. O exemplo da documentação devolve exatamente 2.050,00 / 333,33 / 2.000,00 / 4.383,33 / 104.383,33.
3. A rotina diária (1 dia, em dia) devolve 67,67.
4. Os 9 códigos de rejeição do legado têm teste e são devolvidos com o HTTP da seção 6.
5. Nenhum `double` ou `float` em valor monetário (exceto dentro do `calcularFatorJuros`, documentado).
6. O spread vem da tabela com vigência, não do código.
7. O lote com um contrato inválido no meio devolve os demais calculados.
8. A imagem Docker sobe e responde em `/actuator/health`.
9. `README.md` explica como rodar e mostra um `curl` com o exemplo; `DECISOES.md` registra as decisões técnicas (precisão, potência, códigos HTTP); `DIVERGENCIAS.md` existe, mesmo que vazio.

## 13. Plano de adoção

| Fase | O que acontece | Critério para avançar |
| --- | --- | --- |
| 1. Sombra | O batch continua oficial; os mesmos contratos passam pelo serviço e os resultados são comparados | 30 dias com diferença zero |
| 2. Simulação | Os canais digitais passam a usar o serviço para simular encargos | Aprovação da área de Produtos e da Auditoria |
| 3. Substituição | O STEP040 chama o serviço, ou o cálculo migra de vez | Decisão da arquitetura, com o histórico da fase 1 |
