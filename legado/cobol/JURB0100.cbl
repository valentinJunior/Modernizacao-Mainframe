       IDENTIFICATION DIVISION.
       PROGRAM-ID.    JURB0100.
       AUTHOR.        SISTEMAS CREDITO - BANCO EXEMPLO S.A.
       DATE-WRITTEN.  1998-03-15.
      *----------------------------------------------------------------
      * SISTEMA  : JUR - APROPRIACAO DE JUROS DE CONTRATOS DE CREDITO
      * PROGRAMA : JURB0100 (BATCH)
      * OBJETIVO : LER OS CONTRATOS ATIVOS, LOCALIZAR A TAXA VIGENTE DE
      *            CADA PRODUTO, ACIONAR A SUB-ROTINA JURS0100 PARA O
      *            CALCULO DOS ENCARGOS E GRAVAR O ARQUIVO DE JUROS
      *            APROPRIADOS E O ARQUIVO DE REJEITADOS.
      *----------------------------------------------------------------
      * ENTRADAS : CONTRATO - CONTRATOS ATIVOS ORDENADOS (JURCCONT)
      *            TAXAPROD - TAXAS VIGENTES POR PRODUTO (JURCTAXA)
      *            PARM     - DATA DE REFERENCIA (AAAA-MM-DD)
      * SAIDAS   : JUROSOUT - JUROS APROPRIADOS (JURCSAID)
      *            REJEITOS - CONTRATOS REJEITADOS (JURCREJE)
      * CHAMA    : JURS0100 - SUB-ROTINA DE CALCULO (CALL DINAMICO)
      *----------------------------------------------------------------
      * RETURN-CODE:
      *   00 - PROCESSAMENTO NORMAL, SEM REJEICOES
      *   04 - PROCESSAMENTO NORMAL, COM CONTRATOS REJEITADOS
      *   16 - ERRO GRAVE - PROCESSAMENTO INTERROMPIDO
      *----------------------------------------------------------------
      * HISTORICO DE ALTERACOES
      * DATA       AUTOR    DESCRICAO
      * 1998-03-15 JCS      VERSAO INICIAL
      * 2003-07-02 MAF      INCLUSAO DE JUROS DE MORA E MULTA
      * 2011-10-20 RPL      TAXA PASSA A VIR DA TB_TAXA_PRODUTO (DB2)
      * 2019-05-08 ACV      CALCULO MOVIDO PARA A SUB-ROTINA JURS0100
      *----------------------------------------------------------------
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT ARQ-CONTRATO  ASSIGN TO CONTRATO
                  FILE STATUS IS WS-FS-CONTRATO.
           SELECT ARQ-TAXA      ASSIGN TO TAXAPROD
                  FILE STATUS IS WS-FS-TAXA.
           SELECT ARQ-JUROS     ASSIGN TO JUROSOUT
                  FILE STATUS IS WS-FS-JUROS.
           SELECT ARQ-REJEITO   ASSIGN TO REJEITOS
                  FILE STATUS IS WS-FS-REJEITO.

       DATA DIVISION.
       FILE SECTION.
       FD  ARQ-CONTRATO
           RECORDING MODE IS F
           BLOCK CONTAINS 0 RECORDS.
           COPY JURCCONT.

       FD  ARQ-TAXA
           RECORDING MODE IS F
           BLOCK CONTAINS 0 RECORDS.
           COPY JURCTAXA.

       FD  ARQ-JUROS
           RECORDING MODE IS F
           BLOCK CONTAINS 0 RECORDS.
           COPY JURCSAID.

       FD  ARQ-REJEITO
           RECORDING MODE IS F
           BLOCK CONTAINS 0 RECORDS.
           COPY JURCREJE.

       WORKING-STORAGE SECTION.
       77  WS-SUBROTINA                PIC X(08) VALUE 'JURS0100'.
       77  WS-MAX-TAXAS                PIC S9(04) COMP VALUE 500.

       01  WS-FILE-STATUS.
           05  WS-FS-CONTRATO          PIC X(02).
           05  WS-FS-TAXA              PIC X(02).
           05  WS-FS-JUROS             PIC X(02).
           05  WS-FS-REJEITO           PIC X(02).

       01  WS-FLAGS.
           05  WS-FL-FIM-CONTRATO      PIC X(01) VALUE 'N'.
               88  FIM-CONTRATO                  VALUE 'S'.
           05  WS-FL-FIM-TAXA          PIC X(01) VALUE 'N'.
               88  FIM-TAXA                      VALUE 'S'.

       01  WS-CONTADORES.
           05  WS-QT-LIDOS             PIC S9(09) COMP-3 VALUE 0.
           05  WS-QT-CALCULADOS        PIC S9(09) COMP-3 VALUE 0.
           05  WS-QT-REJEITADOS        PIC S9(09) COMP-3 VALUE 0.
           05  WS-VL-TOT-SALDO         PIC S9(15)V99 COMP-3 VALUE 0.
           05  WS-VL-TOT-ENCARGOS      PIC S9(15)V99 COMP-3 VALUE 0.

       01  WS-EDICAO.
           05  WS-ED-QTDE              PIC ZZZ,ZZZ,ZZ9.
           05  WS-ED-VALOR             PIC ZZZ,ZZZ,ZZZ,ZZZ,ZZ9.99-.

       01  WS-MENSAGEM-ERRO            PIC X(60).
       01  WS-CD-PRODUTO-ANT           PIC X(03) VALUE LOW-VALUES.

      *--- DATA DE REFERENCIA RECEBIDA VIA PARM ------------------------
       01  WS-DT-REFERENCIA.
           05  WS-DT-REF-AAAA          PIC X(04).
           05  WS-DT-REF-SEP1          PIC X(01).
           05  WS-DT-REF-MM            PIC X(02).
           05  WS-DT-REF-SEP2          PIC X(01).
           05  WS-DT-REF-DD            PIC X(02).
       01  WS-DT-REF-NUM               PIC 9(08).
       01  WS-DT-REF-NUM-R REDEFINES WS-DT-REF-NUM.
           05  WS-DT-REF-NUM-AAAA      PIC X(04).
           05  WS-DT-REF-NUM-MM        PIC X(02).
           05  WS-DT-REF-NUM-DD        PIC X(02).

      *--- TABELA DE TAXAS EM MEMORIA (BUSCA BINARIA) ------------------
       01  WS-QT-TAXAS                 PIC S9(04) COMP VALUE 0.
       01  WS-TAB-TAXAS.
           05  WS-TAX-ITEM OCCURS 1 TO 500 TIMES
                           DEPENDING ON WS-QT-TAXAS
                           ASCENDING KEY IS WS-TAX-CD-PRODUTO
                           INDEXED BY IX-TAX.
               10  WS-TAX-CD-PRODUTO   PIC X(03).
               10  WS-TAX-PC-TAXA      PIC S9(03)V9(04) COMP-3.
               10  WS-TAX-PC-MORA      PIC S9(03)V9(04) COMP-3.
               10  WS-TAX-PC-MULTA     PIC S9(03)V9(04) COMP-3.

      *--- AREA DE COMUNICACAO COM A SUB-ROTINA ------------------------
           COPY JURCCALC.

       LINKAGE SECTION.
       01  LK-PARM.
           05  LK-PARM-TAM             PIC S9(04) COMP.
           05  LK-PARM-DATA            PIC X(10).

       PROCEDURE DIVISION USING LK-PARM.
      *----------------------------------------------------------------
       0000-PRINCIPAL.
      *----------------------------------------------------------------
           PERFORM 1000-INICIALIZAR
           PERFORM 2000-PROCESSAR-CONTRATO
                   UNTIL FIM-CONTRATO
           PERFORM 9000-FINALIZAR
           GOBACK.

      *----------------------------------------------------------------
       1000-INICIALIZAR.
      *----------------------------------------------------------------
           DISPLAY '*** JURB0100 - APROPRIACAO DE JUROS - INICIO ***'
           PERFORM 1050-VALIDAR-PARM

           OPEN INPUT  ARQ-CONTRATO
                       ARQ-TAXA
                OUTPUT ARQ-JUROS
                       ARQ-REJEITO

           IF WS-FS-CONTRATO NOT = '00' OR WS-FS-TAXA    NOT = '00'
           OR WS-FS-JUROS    NOT = '00' OR WS-FS-REJEITO NOT = '00'
              STRING 'ERRO NA ABERTURA DE ARQUIVOS - FS: '
                     WS-FS-CONTRATO '/' WS-FS-TAXA '/'
                     WS-FS-JUROS    '/' WS-FS-REJEITO
                     DELIMITED BY SIZE INTO WS-MENSAGEM-ERRO
              PERFORM 9900-ERRO-GRAVE
           END-IF

           PERFORM 1100-CARREGAR-TAXAS
           PERFORM 2100-LER-CONTRATO.

      *----------------------------------------------------------------
       1050-VALIDAR-PARM.
      *----------------------------------------------------------------
           IF LK-PARM-TAM NOT = 10
              MOVE 'PARM AUSENTE OU INVALIDO - ESPERADO AAAA-MM-DD'
                TO WS-MENSAGEM-ERRO
              PERFORM 9900-ERRO-GRAVE
           END-IF

           MOVE LK-PARM-DATA   TO WS-DT-REFERENCIA
           MOVE WS-DT-REF-AAAA TO WS-DT-REF-NUM-AAAA
           MOVE WS-DT-REF-MM   TO WS-DT-REF-NUM-MM
           MOVE WS-DT-REF-DD   TO WS-DT-REF-NUM-DD

           IF WS-DT-REF-SEP1 NOT = '-' OR WS-DT-REF-SEP2 NOT = '-'
           OR WS-DT-REF-NUM  NOT NUMERIC
              MOVE 'DATA DE REFERENCIA COM FORMATO INVALIDO'
                TO WS-MENSAGEM-ERRO
              PERFORM 9900-ERRO-GRAVE
           END-IF

           IF FUNCTION TEST-DATE-YYYYMMDD(WS-DT-REF-NUM) NOT = ZERO
              MOVE 'DATA DE REFERENCIA INEXISTENTE NO CALENDARIO'
                TO WS-MENSAGEM-ERRO
              PERFORM 9900-ERRO-GRAVE
           END-IF

           DISPLAY 'DATA DE REFERENCIA......: ' WS-DT-REFERENCIA.

      *----------------------------------------------------------------
       1100-CARREGAR-TAXAS.
      *----------------------------------------------------------------
      *    CARREGA AS TAXAS VIGENTES EM MEMORIA. O ARQUIVO DEVE VIR
      *    ORDENADO E SEM DUPLICIDADE DE PRODUTO (REQUISITO DA BUSCA
      *    BINARIA - SEARCH ALL).
           PERFORM 1110-LER-TAXA
           PERFORM UNTIL FIM-TAXA
              IF WS-QT-TAXAS >= WS-MAX-TAXAS
                 MOVE 'TABELA DE TAXAS EXCEDEU 500 PRODUTOS'
                   TO WS-MENSAGEM-ERRO
                 PERFORM 9900-ERRO-GRAVE
              END-IF
              IF TAX-CD-PRODUTO NOT > WS-CD-PRODUTO-ANT
                 STRING 'TAXAS FORA DE ORDEM OU DUPLICADAS - PRODUTO '
                        TAX-CD-PRODUTO
                        DELIMITED BY SIZE INTO WS-MENSAGEM-ERRO
                 PERFORM 9900-ERRO-GRAVE
              END-IF
              ADD 1 TO WS-QT-TAXAS
              MOVE TAX-CD-PRODUTO     TO WS-TAX-CD-PRODUTO(WS-QT-TAXAS)
              MOVE TAX-PC-TAXA-MENSAL TO WS-TAX-PC-TAXA(WS-QT-TAXAS)
              MOVE TAX-PC-MORA-MENSAL TO WS-TAX-PC-MORA(WS-QT-TAXAS)
              MOVE TAX-PC-MULTA       TO WS-TAX-PC-MULTA(WS-QT-TAXAS)
              MOVE TAX-CD-PRODUTO     TO WS-CD-PRODUTO-ANT
              PERFORM 1110-LER-TAXA
           END-PERFORM

           IF WS-QT-TAXAS = ZERO
              MOVE 'ARQUIVO DE TAXAS VAZIO' TO WS-MENSAGEM-ERRO
              PERFORM 9900-ERRO-GRAVE
           END-IF

           MOVE WS-QT-TAXAS TO WS-ED-QTDE
           DISPLAY 'PRODUTOS COM TAXA.......: ' WS-ED-QTDE.

      *----------------------------------------------------------------
       1110-LER-TAXA.
      *----------------------------------------------------------------
           READ ARQ-TAXA
              AT END
                 SET FIM-TAXA TO TRUE
           END-READ
           IF WS-FS-TAXA NOT = '00' AND WS-FS-TAXA NOT = '10'
              STRING 'ERRO NA LEITURA DE TAXAPROD - FS: ' WS-FS-TAXA
                     DELIMITED BY SIZE INTO WS-MENSAGEM-ERRO
              PERFORM 9900-ERRO-GRAVE
           END-IF.

      *----------------------------------------------------------------
       2000-PROCESSAR-CONTRATO.
      *----------------------------------------------------------------
           ADD 1 TO WS-QT-LIDOS

           SEARCH ALL WS-TAX-ITEM
              AT END
                 INITIALIZE REG-REJEITO
                 MOVE '01' TO REJ-CD-MOTIVO
                 MOVE 'PRODUTO SEM TAXA VIGENTE CADASTRADA'
                   TO REJ-DS-MOTIVO
                 PERFORM 2300-GRAVAR-REJEITO
              WHEN WS-TAX-CD-PRODUTO(IX-TAX) = CTR-CD-PRODUTO
                 PERFORM 2200-CALCULAR-JUROS
           END-SEARCH

           PERFORM 2100-LER-CONTRATO.

      *----------------------------------------------------------------
       2100-LER-CONTRATO.
      *----------------------------------------------------------------
           READ ARQ-CONTRATO
              AT END
                 SET FIM-CONTRATO TO TRUE
           END-READ
           IF WS-FS-CONTRATO NOT = '00' AND WS-FS-CONTRATO NOT = '10'
              STRING 'ERRO NA LEITURA DE CONTRATO - FS: '
                     WS-FS-CONTRATO
                     DELIMITED BY SIZE INTO WS-MENSAGEM-ERRO
              PERFORM 9900-ERRO-GRAVE
           END-IF.

      *----------------------------------------------------------------
       2200-CALCULAR-JUROS.
      *----------------------------------------------------------------
           INITIALIZE JUR-AREA-CALCULO
           MOVE CTR-NR-CONTRATO           TO JUR-E-NR-CONTRATO
           MOVE CTR-CD-RATING             TO JUR-E-CD-RATING
           MOVE CTR-VL-SALDO-DEVEDOR      TO JUR-E-VL-SALDO
           MOVE WS-TAX-PC-TAXA(IX-TAX)    TO JUR-E-PC-TAXA-BASE
           MOVE WS-TAX-PC-MORA(IX-TAX)    TO JUR-E-PC-MORA
           MOVE WS-TAX-PC-MULTA(IX-TAX)   TO JUR-E-PC-MULTA
           MOVE CTR-DT-ULT-APURACAO       TO JUR-E-DT-ULT-APURACAO
           MOVE CTR-DT-VENCIMENTO         TO JUR-E-DT-VENCIMENTO
           MOVE WS-DT-REFERENCIA          TO JUR-E-DT-REFERENCIA

           CALL WS-SUBROTINA USING JUR-AREA-CALCULO
              ON EXCEPTION
                 MOVE 'SUB-ROTINA JURS0100 NAO ENCONTRADA NA STEPLIB'
                   TO WS-MENSAGEM-ERRO
                 PERFORM 9900-ERRO-GRAVE
           END-CALL

           IF JUR-RET-OK
              PERFORM 2210-GRAVAR-JUROS
           ELSE
              INITIALIZE REG-REJEITO
              MOVE JUR-CD-RETORNO TO REJ-CD-MOTIVO
              MOVE JUR-DS-RETORNO TO REJ-DS-MOTIVO
              PERFORM 2300-GRAVAR-REJEITO
           END-IF.

      *----------------------------------------------------------------
       2210-GRAVAR-JUROS.
      *----------------------------------------------------------------
           INITIALIZE REG-JUROS
           MOVE CTR-NR-CONTRATO          TO JRS-NR-CONTRATO
           MOVE CTR-CD-AGENCIA           TO JRS-CD-AGENCIA
           MOVE CTR-CD-PRODUTO           TO JRS-CD-PRODUTO
           MOVE CTR-CD-RATING            TO JRS-CD-RATING
           MOVE CTR-VL-SALDO-DEVEDOR     TO JRS-VL-SALDO-ANTERIOR
           MOVE JUR-S-PC-TAXA-APLICADA   TO JRS-PC-TAXA-APLICADA
           MOVE JUR-S-QT-DIAS            TO JRS-QT-DIAS
           MOVE JUR-S-FL-ATRASO          TO JRS-FL-ATRASO
           MOVE JUR-S-VL-JUROS-REMUN     TO JRS-VL-JUROS-REMUN
           MOVE JUR-S-VL-JUROS-MORA      TO JRS-VL-JUROS-MORA
           MOVE JUR-S-VL-MULTA           TO JRS-VL-MULTA
           MOVE JUR-S-VL-TOTAL-ENCARGOS  TO JRS-VL-TOTAL-ENCARGOS
           MOVE JUR-S-VL-SALDO-ATUALIZ   TO JRS-VL-SALDO-ATUALIZ
           MOVE WS-DT-REFERENCIA         TO JRS-DT-REFERENCIA

           WRITE REG-JUROS
           IF WS-FS-JUROS NOT = '00'
              STRING 'ERRO NA GRAVACAO DE JUROSOUT - FS: ' WS-FS-JUROS
                     DELIMITED BY SIZE INTO WS-MENSAGEM-ERRO
              PERFORM 9900-ERRO-GRAVE
           END-IF

           ADD 1                         TO WS-QT-CALCULADOS
           ADD CTR-VL-SALDO-DEVEDOR      TO WS-VL-TOT-SALDO
           ADD JUR-S-VL-TOTAL-ENCARGOS   TO WS-VL-TOT-ENCARGOS.

      *----------------------------------------------------------------
       2300-GRAVAR-REJEITO.
      *----------------------------------------------------------------
           MOVE CTR-NR-CONTRATO TO REJ-NR-CONTRATO
           MOVE CTR-CD-AGENCIA  TO REJ-CD-AGENCIA
           MOVE CTR-CD-PRODUTO  TO REJ-CD-PRODUTO

           WRITE REG-REJEITO
           IF WS-FS-REJEITO NOT = '00'
              STRING 'ERRO NA GRAVACAO DE REJEITOS - FS: '
                     WS-FS-REJEITO
                     DELIMITED BY SIZE INTO WS-MENSAGEM-ERRO
              PERFORM 9900-ERRO-GRAVE
           END-IF

           ADD 1 TO WS-QT-REJEITADOS.

      *----------------------------------------------------------------
       9000-FINALIZAR.
      *----------------------------------------------------------------
           CLOSE ARQ-CONTRATO ARQ-TAXA ARQ-JUROS ARQ-REJEITO

           DISPLAY '------------------------------------------------'
           MOVE WS-QT-LIDOS        TO WS-ED-QTDE
           DISPLAY 'CONTRATOS LIDOS.........: ' WS-ED-QTDE
           MOVE WS-QT-CALCULADOS   TO WS-ED-QTDE
           DISPLAY 'CONTRATOS CALCULADOS....: ' WS-ED-QTDE
           MOVE WS-QT-REJEITADOS   TO WS-ED-QTDE
           DISPLAY 'CONTRATOS REJEITADOS....: ' WS-ED-QTDE
           MOVE WS-VL-TOT-SALDO    TO WS-ED-VALOR
           DISPLAY 'SALDO DEVEDOR PROCESSADO: ' WS-ED-VALOR
           MOVE WS-VL-TOT-ENCARGOS TO WS-ED-VALOR
           DISPLAY 'TOTAL DE ENCARGOS.......: ' WS-ED-VALOR
           DISPLAY '------------------------------------------------'

           IF WS-QT-REJEITADOS > ZERO
              MOVE 4 TO RETURN-CODE
           ELSE
              MOVE 0 TO RETURN-CODE
           END-IF

           DISPLAY '*** JURB0100 - FIM NORMAL - RC='
                   RETURN-CODE ' ***'.

      *----------------------------------------------------------------
       9900-ERRO-GRAVE.
      *----------------------------------------------------------------
           DISPLAY '************************************************'
           DISPLAY '* JURB0100 - ERRO GRAVE - PROCESSAMENTO ABORTADO'
           DISPLAY '* ' WS-MENSAGEM-ERRO
           DISPLAY '* CONTRATOS LIDOS ATE O ERRO: ' WS-QT-LIDOS
           DISPLAY '************************************************'
           MOVE 16 TO RETURN-CODE
           STOP RUN.
