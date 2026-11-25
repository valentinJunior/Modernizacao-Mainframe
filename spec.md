# Spec — Inventário automático de componentes mainframe

🇧🇷 Português | [🇺🇸 English](spec.en.md)

**Projeto:** Capstone de Modernização Mainframe com Agentes de IA
**Autor:** Jair Valentin, analista mainframe
**Data:** 24/11/2026
**Fase:** 1 de 3 (1 = inventário, 2 = documentação, 3 = conversão)
**Destinatários:** agente de IA de desenvolvimento (Claude) e equipe técnica
**Status:** implementada em `inventario_mainframe.py`

> **Como esta especificação foi usada.** O projeto segue desenvolvimento guiado por especificação: o analista define o problema, as restrições e os critérios de aceite; um agente de IA implementa a partir deste documento; o analista revisa e valida o resultado contra os critérios da seção 8.

---

## 1. Contexto

Este documento especifica a primeira fase do capstone de modernização mainframe com agentes de IA. A pasta `legado/` contém um sistema bancário de demonstração, com nomes e dados sintéticos: a apropriação diária de juros de contratos de crédito.

| Tipo | Componentes |
| --- | --- |
| JCL | `JURD0100` — job diário com 5 steps (2 UNLOADs DB2, 2 SORTs e o programa) |
| COBOL batch | `JURB0100` — lê os contratos, acha a taxa e chama a sub-rotina |
| COBOL sub-rotina | `JURS0100` — cálculo de juros, mora e multa (via CALL) |
| Copybooks | `JURCCONT`, `JURCTAXA`, `JURCCALC`, `JURCSAID`, `JURCREJE` |

No dia a dia, o primeiro passo de qualquer modernização é o mesmo: **saber o que existe e como as peças se ligam**. Hoje isso é feito manualmente, abrindo fonte por fonte no ISPF, e leva semanas num sistema real. Esta fase demonstra que esse levantamento pode ser automatizado com uma ferramenta simples, sob controle do analista.

## 2. Objetivo

Desenvolver um programa Python que leia os fontes da pasta `legado/` e gere um **inventário estruturado** em dois formatos:

- `saida/inventario.json` — para ser consumido por outras ferramentas e agentes;
- `saida/inventario.md` — para leitura humana e para a apresentação.

## 3. Princípio de arquitetura (obrigatório)

O inventário tem duas camadas, e elas não podem se misturar:

1. **Fatos (parser determinístico).** Tudo que é estrutura sai de um parser feito em Python, sem IA: steps, programas, DDs, datasets, CALLs, COPYs, layouts de registro, posições e tamanhos. O resultado deve ser reproduzível: duas execuções sobre os mesmos fontes geram o mesmo inventário.
2. **Interpretação (IA local).** Resumo de negócio, regras e riscos de cada programa e de cada job ficam com um modelo rodando no **Ollama local**. A IA recebe os fatos já extraídos mais o fonte e só interpreta; não inventa estrutura.

Justificativa: em banco, um inventário errado é pior que nenhum. Além disso, nenhum fonte pode sair do ambiente da instituição, o que exclui APIs externas; só o modelo local é permitido.

Se o Ollama estiver indisponível, o programa deve gerar o inventário de fatos normalmente e apenas avisar que a interpretação por IA não foi incluída. O programa também deve oferecer a opção `--sem-ia`.

## 4. O que o parser precisa extrair

### 4.1 JCL
- Job: nome, accounting, descrição, CLASS/MSGCLASS e o cabeçalho de comentários (sistema, objetivo, periodicidade, predecessor, sucessor).
- Por step: nome, programa executado, PARM, COND e a descrição tirada dos comentários.
- Classificação do step:
  - `IKJEFT01` com `RUN PROGRAM(DSNTIAUL)` → UNLOAD DB2, com o SQL e as tabelas lidas;
  - `IKJEFT01` com outro programa → programa DB2 (o programa real é o do RUN PROGRAM);
  - `SORT`/`ICEMAN`/`SYNCSORT` → SORT, com os comandos (INCLUDE/OMIT, SORT FIELDS, SUM, INREC/OUTREC/OUTFIL);
  - utilitários conhecidos (IDCAMS, IEBGENER, IEFBR14) → identificados pelo nome;
  - o resto → programa aplicativo.
- DDs de cada step: DDNAME, DSN, geração GDG (+1/0), DISP, SYSOUT, LRECL/RECFM e dados instream.
- Tratar continuação de linha, comentários `//*`, instream `DD *` até `/*` e concatenação de DD.

### 4.2 COBOL
- PROGRAM-ID, AUTHOR, DATE-WRITTEN, cabeçalho de comentários e histórico de alterações.
- SELECT/ASSIGN (arquivo lógico → DDNAME), FILE STATUS e o copybook de cada FD.
- Modo de abertura dos arquivos (INPUT/OUTPUT/I-O/EXTEND).
- COPYs, separados por seção (FILE, WORKING-STORAGE, LINKAGE).
- CALLs, estáticos ou dinâmicos. No CALL dinâmico, resolver o nome pelo `VALUE` da variável.
- `PROCEDURE DIVISION USING`, parágrafos e PERFORMs.
- Return codes (`MOVE n TO RETURN-CODE`), regras documentadas (`RNxx`) e códigos de retorno em comentário.
- Métricas: linhas totais, de código e de comentário.
- Tipo: batch principal ou sub-rotina, confirmado pela referência cruzada (quem chama quem).

### 4.3 Copybooks
- Todos os campos com nível, nome, PIC, USAGE, OCCURS, REDEFINES e níveis 88.
- **Posição inicial e tamanho em bytes de cada campo**, calculados pelo PIC e USAGE (COMP-3, COMP, display).
- Comparar o tamanho calculado com o LRECL documentado no comentário do copybook.

### 4.4 Referência cruzada
- Step do JCL → fonte COBOL do programa executado.
- DD do step ↔ SELECT do programa ↔ copybook do FD. Isso amarra cada dataset ao seu layout.
- Propagar o layout através de SORTs que não reformatam o registro (SORTIN e SORTOUT têm o mesmo layout).
- Programa → sub-rotinas chamadas e quem chama cada uma.
- Linhagem de datasets: qual step cria e qual step lê cada arquivo.

### 4.5 Achados automáticos
O parser deve apontar sozinho, com severidade:
- DD exigida pelo programa e ausente no step;
- LRECL do JCL diferente do tamanho calculado do copybook;
- COPY ou CALL sem fonte na pasta, ou programa executado sem fonte;
- SELECT sem FILE STATUS;
- datas fixas no JCL (PARM ou instream);
- tabelas internas com limite fixo (OCCURS);
- tabelas de valores fixas no código (EVALUATE com muitos valores literais);
- exponenciação (`**`), que deve ser validada numa migração por causa da precisão;
- parágrafos que ninguém chama (possível código morto).

## 5. Saídas

### 5.1 JSON (`inventario.json`)
Estrutura de alto nível:

```json
{
  "metadados": { "gerado_em": "...", "versao": "...", "pasta_fontes": "...", "modelo_ia": "...", "ia_utilizada": true },
  "resumo":    { "jobs": 1, "steps": 5, "programas": 2, "copybooks": 5, "datasets": 6, "achados": 0 },
  "jobs":      [ { "nome": "...", "steps": [ { "nome": "...", "tipo": "...", "dds": [] } ], "analise_ia": {} } ],
  "programas": [ { "programa": "...", "tipo": "...", "arquivos": [], "chamadas": [], "copybooks": [], "analise_ia": {} } ],
  "copybooks": [ { "nome": "...", "tamanho_calculado": 0, "lrecl_documentado": 0, "campos": [] } ],
  "datasets":  [ { "dsn": "...", "criado_por": [], "lido_por": [], "layout": "..." } ],
  "achados":   [ { "severidade": "alta|media|baixa|info", "componente": "...", "descricao": "..." } ]
}
```

A `analise_ia` de cada componente tem: `resumo_negocio`, `funcao_tecnica`, `regras_negocio` e `riscos`.

### 5.2 Markdown (`inventario.md`)
- Visão geral com os números do inventário.
- Fluxo de cada job em **Mermaid** (steps e datasets).
- Tabela de steps; tabela de programas com arquivos, chamadas e copybooks.
- Layout de cada copybook com posição, tamanho e formato.
- Linhagem de datasets.
- Achados ordenados por severidade.
- Análise da IA, sempre marcada como "interpretação gerada por IA, validar com o analista".

## 6. Uso

```bash
python3 inventario_mainframe.py --fontes legado --saida saida
python3 inventario_mainframe.py --fontes legado --sem-ia
python3 inventario_mainframe.py --modelo qwen2.5:14b --ollama-url http://localhost:11434
```

Padrão: modelo `qwen2.5:7b`, temperatura 0 e resposta em formato JSON (`format: json` do Ollama).

## 7. Restrições técnicas
- Python 3, **só biblioteca padrão** (sem pip install; o ambiente do banco é fechado).
- Um único arquivo `.py`, fácil de levar para outra máquina.
- Fontes lidos em `latin-1`, que é como chegam do mainframe depois da transferência.
- Respeitar o formato fixo: colunas 1–6 de sequência, 7 de indicador, 8–72 de código; JCL até a coluna 71.
- Código e comentários em português, com nomes de funções claros.

## 8. Critérios de aceite
1. Rodando em `legado/`, o inventário lista 1 job, 5 steps, 2 programas, 5 copybooks e 6 datasets.
2. `JURB0100` aparece como batch, chamando `JURS0100` (CALL dinâmico resolvido pelo VALUE).
3. `JURS0100` aparece como sub-rotina, chamada por `JURB0100`.
4. Os tamanhos calculados batem com o LRECL documentado: JURCCONT 50, JURCTAXA 45, JURCSAID 100 e JURCREJE 80.
5. Os datasets do STEP040 aparecem ligados ao copybook correto, e `BCO.JUR.CONTRATO.ATIVOS` herda o layout JURCCONT através do SORT.
6. As datas fixas `2026-11-24` no JCL aparecem como achado.
7. Com `--sem-ia` ou com o Ollama desligado, o programa termina normalmente.
8. Rodar duas vezes com `--sem-ia` gera o mesmo JSON (menos a data de geração).

## 9. Fora do escopo (por enquanto)
- PROCs catalogadas e INCLUDEs de JCL.
- Programas CICS online e telas BMS (o parser só identifica `EXEC CICS`).
- Conversão de código. Este passo é só o inventário; a conversão vem depois, em cima deste JSON.
