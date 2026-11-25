# Spec — Automated inventory of mainframe components

[🇧🇷 Português](spec.md) | 🇺🇸 English

**Project:** Mainframe Modernization Capstone with AI Agents
**Author:** Jair Valentin, mainframe analyst
**Date:** 2026-11-24
**Phase:** 1 of 3 (1 = inventory, 2 = documentation, 3 = conversion)
**Audience:** AI development agent (Claude) and technical team
**Status:** implemented in `inventario_mainframe.py`

> **How this specification was used.** The project follows spec-driven development: the analyst defines the problem, the constraints and the acceptance criteria; an AI agent implements from this document; the analyst reviews the result and validates it against the criteria in section 8.

---

## 1. Context

This document specifies the first phase of the mainframe modernization capstone with AI agents. The `legado/` folder contains a demonstration banking system, with synthetic names and data: the daily interest accrual for credit contracts.

| Type | Components |
| --- | --- |
| JCL | `JURD0100` — daily job with 5 steps (2 DB2 UNLOADs, 2 SORTs and the program) |
| COBOL batch | `JURB0100` — reads the contracts, looks up the rate and calls the subroutine |
| COBOL subroutine | `JURS0100` — calculation of interest, late-payment interest and late fee (via CALL) |
| Copybooks | `JURCCONT`, `JURCTAXA`, `JURCCALC`, `JURCSAID`, `JURCREJE` |

In day-to-day work, the first step of any modernization is always the same: **knowing what exists and how the pieces connect**. Today this is done by hand, opening one source after another in ISPF, and on a real system it takes weeks. This phase shows that this discovery can be automated with a simple tool, under the analyst's control.

## 2. Objective

Develop a Python program that reads the sources in the `legado/` folder and generates a **structured inventory** in two formats:

- `saida/inventario.json` — to be consumed by other tools and agents;
- `saida/inventario.md` — for human reading and for the presentation.

## 3. Architecture principle (mandatory)

The inventory has two layers, and they must not be mixed:

1. **Facts (deterministic parser).** Everything structural comes from a parser written in Python, with no AI: steps, programs, DDs, datasets, CALLs, COPYs, record layouts, positions and sizes. The result must be reproducible: two runs over the same sources produce the same inventory.
2. **Interpretation (local AI).** The business summary, rules and risks of each program and each job are left to a model running on **local Ollama**. The AI receives the already-extracted facts plus the source and only interprets; it does not invent structure.

Rationale: in a bank, a wrong inventory is worse than none. In addition, no source code may leave the institution's environment, which rules out external APIs; only the local model is allowed.

If Ollama is unavailable, the program must generate the facts inventory normally and simply warn that the AI interpretation was not included. The program must also offer the `--sem-ia` option.

## 4. What the parser must extract

### 4.1 JCL
- Job: name, accounting, description, CLASS/MSGCLASS and the comment header (system, objective, frequency, predecessor, successor).
- Per step: name, executed program, PARM, COND and the description taken from the comments.
- Step classification:
  - `IKJEFT01` with `RUN PROGRAM(DSNTIAUL)` → DB2 UNLOAD, with the SQL and the tables read;
  - `IKJEFT01` with another program → DB2 program (the actual program is the one in RUN PROGRAM);
  - `SORT`/`ICEMAN`/`SYNCSORT` → SORT, with the control statements (INCLUDE/OMIT, SORT FIELDS, SUM, INREC/OUTREC/OUTFIL);
  - known utilities (IDCAMS, IEBGENER, IEFBR14) → identified by name;
  - everything else → application program.
- DDs of each step: DDNAME, DSN, GDG generation (+1/0), DISP, SYSOUT, LRECL/RECFM and instream data.
- Handle line continuation, `//*` comments, instream `DD *` up to `/*` and DD concatenation.

### 4.2 COBOL
- PROGRAM-ID, AUTHOR, DATE-WRITTEN, comment header and change history.
- SELECT/ASSIGN (logical file → DDNAME), FILE STATUS and the copybook of each FD.
- File open mode (INPUT/OUTPUT/I-O/EXTEND).
- COPYs, grouped by section (FILE, WORKING-STORAGE, LINKAGE).
- CALLs, static or dynamic. For a dynamic CALL, resolve the name from the variable's `VALUE`.
- `PROCEDURE DIVISION USING`, paragraphs and PERFORMs.
- Return codes (`MOVE n TO RETURN-CODE`), documented rules (`RNxx`) and return codes in comments.
- Metrics: total lines, code lines and comment lines.
- Type: main batch program or subroutine, confirmed by the cross-reference (who calls whom).

### 4.3 Copybooks
- All fields with level, name, PIC, USAGE, OCCURS, REDEFINES and level 88s.
- **Starting position and size in bytes of each field**, calculated from PIC and USAGE (COMP-3, COMP, display).
- Compare the calculated size with the LRECL documented in the copybook comment.

### 4.4 Cross-reference
- JCL step → COBOL source of the executed program.
- Step DD ↔ program SELECT ↔ FD copybook. This ties each dataset to its layout.
- Propagate the layout through SORTs that do not reformat the record (SORTIN and SORTOUT have the same layout).
- Program → called subroutines, and who calls each one.
- Dataset lineage: which step creates and which step reads each file.

### 4.5 Automatic findings
The parser must flag the following on its own, with severity:
- DD required by the program and missing from the step;
- JCL LRECL different from the copybook's calculated size;
- COPY or CALL with no source in the folder, or executed program with no source;
- SELECT without FILE STATUS;
- hardcoded dates in the JCL (PARM or instream);
- internal tables with a fixed limit (OCCURS);
- value tables hardcoded in the code (EVALUATE with many literal values);
- exponentiation (`**`), which must be validated in a migration because of precision;
- paragraphs that nobody calls (possible dead code).

## 5. Outputs

### 5.1 JSON (`inventario.json`)
High-level structure:

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

The `analise_ia` of each component has: `resumo_negocio`, `funcao_tecnica`, `regras_negocio` and `riscos`.

### 5.2 Markdown (`inventario.md`)
- Overview with the inventory figures.
- Flow of each job in **Mermaid** (steps and datasets).
- Steps table; programs table with files, calls and copybooks.
- Layout of each copybook with position, size and format.
- Dataset lineage.
- Findings sorted by severity.
- AI analysis, always labeled "interpretação gerada por IA, validar com o analista" (AI-generated interpretation, validate with the analyst).

## 6. Usage

```bash
python3 inventario_mainframe.py --fontes legado --saida saida
python3 inventario_mainframe.py --fontes legado --sem-ia
python3 inventario_mainframe.py --modelo qwen2.5:14b --ollama-url http://localhost:11434
```

Defaults: model `qwen2.5:7b`, temperature 0 and JSON-formatted response (Ollama's `format: json`).

## 7. Technical constraints
- Python 3, **standard library only** (no pip install; the bank's environment is locked down).
- A single `.py` file, easy to carry to another machine.
- Sources read as `latin-1`, which is how they arrive from the mainframe after transfer.
- Respect the fixed format: columns 1–6 for sequence, 7 for indicator, 8–72 for code; JCL up to column 71.
- Code and comments in Portuguese, with clear function names.

## 8. Acceptance criteria
1. Run against `legado/`, the inventory lists 1 job, 5 steps, 2 programs, 5 copybooks and 6 datasets.
2. `JURB0100` appears as batch, calling `JURS0100` (dynamic CALL resolved through the VALUE).
3. `JURS0100` appears as a subroutine, called by `JURB0100`.
4. The calculated sizes match the documented LRECL: JURCCONT 50, JURCTAXA 45, JURCSAID 100 and JURCREJE 80.
5. The STEP040 datasets appear linked to the correct copybook, and `BCO.JUR.CONTRATO.ATIVOS` inherits the JURCCONT layout through the SORT.
6. The hardcoded `2026-11-24` dates in the JCL appear as a finding.
7. With `--sem-ia` or with Ollama turned off, the program finishes normally.
8. Running twice with `--sem-ia` produces the same JSON (except for the generation timestamp).

## 9. Out of scope (for now)
- Cataloged PROCs and JCL INCLUDEs.
- Online CICS programs and BMS maps (the parser only identifies `EXEC CICS`).
- Code conversion. This step is only the inventory; conversion comes later, built on top of this JSON.
