       IDENTIFICATION DIVISION.
       PROGRAM-ID.    JURS0100.
       AUTHOR.        SISTEMAS CREDITO - BANCO EXEMPLO S.A.
       DATE-WRITTEN.  2019-05-08.
      *----------------------------------------------------------------
      * SISTEMA  : JUR - APROPRIACAO DE JUROS DE CONTRATOS DE CREDITO
      * PROGRAMA : JURS0100 (SUB-ROTINA - CHAMADA VIA CALL)
      * OBJETIVO : CALCULAR OS ENCARGOS DE UM CONTRATO DE CREDITO NO
      *            PERIODO ENTRE A ULTIMA APURACAO E A DATA DE
      *            REFERENCIA:
      *            - JUROS REMUNERATORIOS (COMPOSTOS, BASE 30 DIAS)
      *            - JUROS DE MORA (SIMPLES, PRO RATA DIE)
      *            - MULTA POR ATRASO (UNICA VEZ)
      * CHAMADO  : JURB0100 (E QUALQUER PROGRAMA QUE USE A JURCCALC)
      * INTERFACE: COPYBOOK JURCCALC
      *----------------------------------------------------------------
      * REGRAS DE NEGOCIO
      * RN01 - TAXA APLICADA = TAXA BASE DO PRODUTO + SPREAD DO RATING
      * RN02 - JUROS REMUNERATORIOS = SALDO * ((1+TAXA)^(DIAS/30) - 1)
      * RN03 - JUROS DE MORA = SALDO * TAXA MORA * DIAS ATRASO / 30,
      *        CONSIDERANDO APENAS OS DIAS DE ATRASO DENTRO DO PERIODO
      * RN04 - MULTA = SALDO * PERCENTUAL DE MULTA, COBRADA SOMENTE NO
      *        PERIODO EM QUE O VENCIMENTO OCORREU
      * RN05 - SALDO ATUALIZADO = SALDO + TOTAL DE ENCARGOS
      *----------------------------------------------------------------
      * HISTORICO DE ALTERACOES
      * DATA       AUTOR    DESCRICAO
      * 2019-05-08 ACV      VERSAO INICIAL (EXTRAIDO DO JURB0100)
      * 2021-02-11 ACV      INCLUSAO DOS RATINGS F, G E H
      * 2023-09-14 LMS      VALIDACAO DE SALDO NAO NUMERICO (S0C7)
      *----------------------------------------------------------------
       ENVIRONMENT DIVISION.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-DT-ISO.
           05  WS-ISO-AAAA             PIC X(04).
           05  WS-ISO-SEP1             PIC X(01).
           05  WS-ISO-MM               PIC X(02).
           05  WS-ISO-SEP2             PIC X(01).
           05  WS-ISO-DD               PIC X(02).
       01  WS-DT-NUM                   PIC 9(08).
       01  WS-DT-NUM-R REDEFINES WS-DT-NUM.
           05  WS-NUM-AAAA             PIC X(04).
           05  WS-NUM-MM               PIC X(02).
           05  WS-NUM-DD               PIC X(02).
       01  WS-FL-DATA                  PIC X(01).
           88  DATA-VALIDA                       VALUE 'S'.
           88  DATA-INVALIDA                     VALUE 'N'.

      *--- DATAS CONVERTIDAS EM DIAS CORRIDOS (INTEGER-OF-DATE) --------
       01  WS-DIAS-CORRIDOS.
           05  WS-DIA-ULT-APURACAO     PIC S9(09) COMP.
           05  WS-DIA-VENCIMENTO       PIC S9(09) COMP.
           05  WS-DIA-REFERENCIA       PIC S9(09) COMP.

       01  WS-CALCULO.
           05  WS-SPREAD-RATING        PIC S9(03)V9(04) COMP-3.
           05  WS-EXPOENTE             PIC S9(03)V9(09) COMP-3.
           05  WS-FATOR-JUROS          PIC S9(03)V9(12) COMP-3.
           05  WS-DIAS-ATRASO-PERIODO  PIC S9(05) COMP-3.

       LINKAGE SECTION.
           COPY JURCCALC.

       PROCEDURE DIVISION USING JUR-AREA-CALCULO.
      *----------------------------------------------------------------
       0000-PRINCIPAL.
      *----------------------------------------------------------------
           INITIALIZE JUR-SAIDA
           SET JUR-S-EM-DIA TO TRUE
           MOVE '00' TO JUR-CD-RETORNO
           MOVE 'CALCULO EFETUADO COM SUCESSO' TO JUR-DS-RETORNO

           PERFORM 1000-VALIDAR-ENTRADA

           IF JUR-RET-OK
              PERFORM 2000-APLICAR-SPREAD-RATING
           END-IF

           IF JUR-RET-OK
              PERFORM 3000-CALCULAR-PRAZO
              PERFORM 4000-CALCULAR-JUROS-REMUN
              PERFORM 5000-CALCULAR-ENCARGOS-ATRASO
              PERFORM 6000-TOTALIZAR
           END-IF

           MOVE ZERO TO RETURN-CODE
           GOBACK.

      *----------------------------------------------------------------
       1000-VALIDAR-ENTRADA.
      *----------------------------------------------------------------
           EVALUATE TRUE
              WHEN JUR-E-VL-SALDO NOT NUMERIC
                 MOVE '21' TO JUR-CD-RETORNO
                 MOVE 'SALDO DEVEDOR COM CONTEUDO NAO NUMERICO'
                   TO JUR-DS-RETORNO
              WHEN JUR-E-VL-SALDO NOT > ZERO
                 MOVE '20' TO JUR-CD-RETORNO
                 MOVE 'SALDO DEVEDOR ZERADO OU NEGATIVO'
                   TO JUR-DS-RETORNO
              WHEN JUR-E-PC-TAXA-BASE NOT > ZERO
              WHEN JUR-E-PC-TAXA-BASE > 30
                 MOVE '10' TO JUR-CD-RETORNO
                 MOVE 'TAXA BASE FORA DA FAIXA PERMITIDA (0 A 30% AM)'
                   TO JUR-DS-RETORNO
              WHEN OTHER
                 PERFORM 1100-VALIDAR-DATAS
           END-EVALUATE.

      *----------------------------------------------------------------
       1100-VALIDAR-DATAS.
      *----------------------------------------------------------------
           MOVE JUR-E-DT-ULT-APURACAO TO WS-DT-ISO
           PERFORM 1110-CONVERTER-DATA-ISO
           IF DATA-INVALIDA
              MOVE '30' TO JUR-CD-RETORNO
              MOVE 'DATA DA ULTIMA APURACAO INVALIDA' TO JUR-DS-RETORNO
           ELSE
              COMPUTE WS-DIA-ULT-APURACAO =
                      FUNCTION INTEGER-OF-DATE(WS-DT-NUM)
           END-IF

           IF JUR-RET-OK
              MOVE JUR-E-DT-VENCIMENTO TO WS-DT-ISO
              PERFORM 1110-CONVERTER-DATA-ISO
              IF DATA-INVALIDA
                 MOVE '31' TO JUR-CD-RETORNO
                 MOVE 'DATA DE VENCIMENTO INVALIDA' TO JUR-DS-RETORNO
              ELSE
                 COMPUTE WS-DIA-VENCIMENTO =
                         FUNCTION INTEGER-OF-DATE(WS-DT-NUM)
              END-IF
           END-IF

           IF JUR-RET-OK
              MOVE JUR-E-DT-REFERENCIA TO WS-DT-ISO
              PERFORM 1110-CONVERTER-DATA-ISO
              IF DATA-INVALIDA
                 MOVE '33' TO JUR-CD-RETORNO
                 MOVE 'DATA DE REFERENCIA INVALIDA' TO JUR-DS-RETORNO
              ELSE
                 COMPUTE WS-DIA-REFERENCIA =
                         FUNCTION INTEGER-OF-DATE(WS-DT-NUM)
              END-IF
           END-IF

           IF JUR-RET-OK
              IF WS-DIA-REFERENCIA < WS-DIA-ULT-APURACAO
                 MOVE '32' TO JUR-CD-RETORNO
                 MOVE 'DATA DE REFERENCIA ANTERIOR A ULTIMA APURACAO'
                   TO JUR-DS-RETORNO
              END-IF
           END-IF.

      *----------------------------------------------------------------
       1110-CONVERTER-DATA-ISO.
      *----------------------------------------------------------------
      *    CONVERTE AAAA-MM-DD PARA AAAAMMDD E VALIDA NO CALENDARIO
           SET DATA-VALIDA TO TRUE
           MOVE WS-ISO-AAAA TO WS-NUM-AAAA
           MOVE WS-ISO-MM   TO WS-NUM-MM
           MOVE WS-ISO-DD   TO WS-NUM-DD

           IF WS-ISO-SEP1 NOT = '-' OR WS-ISO-SEP2 NOT = '-'
           OR WS-DT-NUM NOT NUMERIC
              SET DATA-INVALIDA TO TRUE
           ELSE
              IF FUNCTION TEST-DATE-YYYYMMDD(WS-DT-NUM) NOT = ZERO
                 SET DATA-INVALIDA TO TRUE
              END-IF
           END-IF.

      *----------------------------------------------------------------
       2000-APLICAR-SPREAD-RATING.
      *----------------------------------------------------------------
      *    RN01 - SPREAD DE RISCO POR RATING (% AO MES)
      *    ATENCAO: TABELA FIXA NO PROGRAMA. ALTERACOES EXIGEM
      *    MANUTENCAO, COMPILACAO E IMPLANTACAO DA SUB-ROTINA.
           EVALUATE JUR-E-CD-RATING
              WHEN 'AA'  MOVE 0.0000 TO WS-SPREAD-RATING
              WHEN 'A '  MOVE 0.1000 TO WS-SPREAD-RATING
              WHEN 'B '  MOVE 0.2500 TO WS-SPREAD-RATING
              WHEN 'C '  MOVE 0.5000 TO WS-SPREAD-RATING
              WHEN 'D '  MOVE 0.7500 TO WS-SPREAD-RATING
              WHEN 'E '  MOVE 1.0000 TO WS-SPREAD-RATING
              WHEN 'F '  MOVE 1.2500 TO WS-SPREAD-RATING
              WHEN 'G '  MOVE 1.5000 TO WS-SPREAD-RATING
              WHEN 'H '  MOVE 2.0000 TO WS-SPREAD-RATING
              WHEN OTHER
                 MOVE '40' TO JUR-CD-RETORNO
                 MOVE 'RATING DE RISCO NAO RECONHECIDO'
                   TO JUR-DS-RETORNO
           END-EVALUATE

           IF JUR-RET-OK
              COMPUTE JUR-S-PC-TAXA-APLICADA =
                      JUR-E-PC-TAXA-BASE + WS-SPREAD-RATING
           END-IF.

      *----------------------------------------------------------------
       3000-CALCULAR-PRAZO.
      *----------------------------------------------------------------
           COMPUTE JUR-S-QT-DIAS =
                   WS-DIA-REFERENCIA - WS-DIA-ULT-APURACAO

           IF WS-DIA-REFERENCIA > WS-DIA-VENCIMENTO
              SET JUR-S-EM-ATRASO TO TRUE
              COMPUTE JUR-S-QT-DIAS-ATRASO =
                      WS-DIA-REFERENCIA - WS-DIA-VENCIMENTO
           ELSE
              SET JUR-S-EM-DIA TO TRUE
              MOVE ZERO TO JUR-S-QT-DIAS-ATRASO
           END-IF.

      *----------------------------------------------------------------
       4000-CALCULAR-JUROS-REMUN.
      *----------------------------------------------------------------
      *    RN02 - JUROS COMPOSTOS COM TAXA MENSAL EQUIVALENTE DIARIA
      *           (CONVENCAO MES COMERCIAL DE 30 DIAS)
           IF JUR-S-QT-DIAS = ZERO
              MOVE ZERO TO JUR-S-VL-JUROS-REMUN
           ELSE
              COMPUTE WS-EXPOENTE ROUNDED = JUR-S-QT-DIAS / 30
              COMPUTE WS-FATOR-JUROS ROUNDED =
                      (1 + JUR-S-PC-TAXA-APLICADA / 100)
                      ** WS-EXPOENTE
              COMPUTE JUR-S-VL-JUROS-REMUN ROUNDED =
                      JUR-E-VL-SALDO * (WS-FATOR-JUROS - 1)
           END-IF.

      *----------------------------------------------------------------
       5000-CALCULAR-ENCARGOS-ATRASO.
      *----------------------------------------------------------------
           IF JUR-S-EM-ATRASO
      *       RN03 - MORA SOMENTE SOBRE OS DIAS DE ATRASO CONTIDOS
      *              NO PERIODO APURADO (EVITA COBRAR DUAS VEZES)
              IF JUR-S-QT-DIAS-ATRASO < JUR-S-QT-DIAS
                 MOVE JUR-S-QT-DIAS-ATRASO TO WS-DIAS-ATRASO-PERIODO
              ELSE
                 MOVE JUR-S-QT-DIAS        TO WS-DIAS-ATRASO-PERIODO
              END-IF

              COMPUTE JUR-S-VL-JUROS-MORA ROUNDED =
                      JUR-E-VL-SALDO * JUR-E-PC-MORA / 100
                      * WS-DIAS-ATRASO-PERIODO / 30

      *       RN04 - MULTA APENAS NO PERIODO EM QUE O VENCIMENTO
      *              OCORREU (NAO E COBRADA NOVAMENTE NOS PROXIMOS DIAS)
              IF WS-DIA-VENCIMENTO >= WS-DIA-ULT-APURACAO
                 COMPUTE JUR-S-VL-MULTA ROUNDED =
                         JUR-E-VL-SALDO * JUR-E-PC-MULTA / 100
              END-IF
           END-IF.

      *----------------------------------------------------------------
       6000-TOTALIZAR.
      *----------------------------------------------------------------
      *    RN05 - CONSOLIDACAO DOS ENCARGOS
           COMPUTE JUR-S-VL-TOTAL-ENCARGOS =
                   JUR-S-VL-JUROS-REMUN
                 + JUR-S-VL-JUROS-MORA
                 + JUR-S-VL-MULTA

           COMPUTE JUR-S-VL-SALDO-ATUALIZ =
                   JUR-E-VL-SALDO + JUR-S-VL-TOTAL-ENCARGOS.
