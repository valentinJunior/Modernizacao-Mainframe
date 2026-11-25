       IDENTIFICATION DIVISION.
       PROGRAM-ID.    JURT0100.
      *----------------------------------------------------------------
      * SISTEMA  : JUR - APROPRIACAO DE JUROS DE CONTRATOS DE CREDITO
      * PROGRAMA : JURT0100 - DRIVER DE TESTE DA SUB-ROTINA JURS0100
      * OBJETIVO : LER OS CASOS DA MASSA DE EQUIVALENCIA, CHAMAR A
      *            JURS0100 ORIGINAL (SEM ALTERACAO) VIA CALL E GRAVAR
      *            O RESULTADO, PARA COMPARAR COM O SERVICO JAVA.
      * ENTRADA  : entrada.csv
      *            CASO;RATING;SALDO;TAXA;MORA;MULTA;ULT;VENC;REF
      * SAIDA    : saida.csv
      *            CASO;CODIGO;TAXA-APLICADA;DIAS;DIAS-ATRASO;REMUN;
      *            MORA;MULTA;TOTAL;SALDO-ATUALIZADO
      * OBSERVACAO: SALDO NAO NUMERICO E GRAVADO COMO HIGH-VALUES NO
      *            CAMPO COMP-3, SIMULANDO O DADO INVALIDO QUE NO
      *            MAINFRAME CAUSARIA S0C7 SEM A VALIDACAO DE 2023.
      *----------------------------------------------------------------
       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT ARQ-ENTRADA ASSIGN TO 'entrada.csv'
                  ORGANIZATION IS LINE SEQUENTIAL
                  FILE STATUS IS WS-FS-ENTRADA.
           SELECT ARQ-SAIDA   ASSIGN TO 'saida.csv'
                  ORGANIZATION IS LINE SEQUENTIAL
                  FILE STATUS IS WS-FS-SAIDA.

       DATA DIVISION.
       FILE SECTION.
       FD  ARQ-ENTRADA.
       01  REG-ENTRADA                 PIC X(200).
       FD  ARQ-SAIDA.
       01  REG-SAIDA                   PIC X(300).

       WORKING-STORAGE SECTION.
       01  WS-FS-ENTRADA               PIC X(02).
       01  WS-FS-SAIDA                 PIC X(02).
       01  WS-FL-FIM                   PIC X(01) VALUE 'N'.
           88  FIM-ENTRADA                       VALUE 'S'.
       01  WS-QT-CASOS                 PIC 9(05) VALUE ZERO.

       01  WS-CAMPOS.
           05  WS-T-CASO               PIC X(60).
           05  WS-T-RATING             PIC X(10).
           05  WS-T-SALDO              PIC X(30).
           05  WS-T-TAXA               PIC X(15).
           05  WS-T-MORA               PIC X(15).
           05  WS-T-MULTA              PIC X(15).
           05  WS-T-ULT                PIC X(15).
           05  WS-T-VENC               PIC X(15).
           05  WS-T-REF                PIC X(15).

      *--- SALDO LIDO COM FOLGA; O MOVE PARA S9(13)V99 TRUNCA COMO NO
      *--- MAINFRAME (INTEIROS PELA ESQUERDA, DECIMAIS PELA DIREITA)
       01  WS-SALDO-LARGO              PIC S9(18)V9(03).

       01  WS-EDICAO.
           05  WS-ED-TAXA              PIC ZZ9.9999.
           05  WS-ED-DIAS              PIC -(5)9.
           05  WS-ED-ATRASO            PIC -(5)9.
           05  WS-ED-REMUN             PIC -(14)9.99.
           05  WS-ED-MORA              PIC -(14)9.99.
           05  WS-ED-MULTA             PIC -(14)9.99.
           05  WS-ED-TOTAL             PIC -(14)9.99.
           05  WS-ED-SALDO             PIC -(14)9.99.

           COPY JURCCALC.
       01  WS-AREA-BYTES REDEFINES JUR-AREA-CALCULO.
           05  FILLER                  PIC X(14).
           05  WS-SALDO-BYTES          PIC X(08).

       PROCEDURE DIVISION.
      *----------------------------------------------------------------
       0000-PRINCIPAL.
      *----------------------------------------------------------------
           OPEN INPUT  ARQ-ENTRADA
           OPEN OUTPUT ARQ-SAIDA
           IF WS-FS-ENTRADA NOT = '00' OR WS-FS-SAIDA NOT = '00'
              DISPLAY 'JURT0100 - ERRO NA ABERTURA. FS ENTRADA='
                      WS-FS-ENTRADA ' SAIDA=' WS-FS-SAIDA
              MOVE 16 TO RETURN-CODE
              STOP RUN
           END-IF

           PERFORM 1000-LER-ENTRADA
           PERFORM UNTIL FIM-ENTRADA
              PERFORM 2000-PROCESSAR-CASO
              PERFORM 1000-LER-ENTRADA
           END-PERFORM

           CLOSE ARQ-ENTRADA ARQ-SAIDA
           DISPLAY 'JURT0100 - CASOS PROCESSADOS: ' WS-QT-CASOS
           MOVE ZERO TO RETURN-CODE
           STOP RUN.

      *----------------------------------------------------------------
       1000-LER-ENTRADA.
      *----------------------------------------------------------------
           READ ARQ-ENTRADA
              AT END SET FIM-ENTRADA TO TRUE
           END-READ.

      *----------------------------------------------------------------
       2000-PROCESSAR-CASO.
      *----------------------------------------------------------------
           ADD 1 TO WS-QT-CASOS
           MOVE SPACES TO WS-CAMPOS
           UNSTRING REG-ENTRADA DELIMITED BY ';'
               INTO WS-T-CASO  WS-T-RATING WS-T-SALDO
                    WS-T-TAXA  WS-T-MORA   WS-T-MULTA
                    WS-T-ULT   WS-T-VENC   WS-T-REF
           END-UNSTRING

           INITIALIZE JUR-AREA-CALCULO
           MOVE '000000000001'  TO JUR-E-NR-CONTRATO
           MOVE WS-T-RATING     TO JUR-E-CD-RATING

           IF FUNCTION TEST-NUMVAL(WS-T-SALDO) = ZERO
              COMPUTE WS-SALDO-LARGO = FUNCTION NUMVAL(WS-T-SALDO)
              MOVE WS-SALDO-LARGO TO JUR-E-VL-SALDO
           ELSE
              MOVE HIGH-VALUES TO WS-SALDO-BYTES
           END-IF

           COMPUTE JUR-E-PC-TAXA-BASE = FUNCTION NUMVAL(WS-T-TAXA)
           COMPUTE JUR-E-PC-MORA      = FUNCTION NUMVAL(WS-T-MORA)
           COMPUTE JUR-E-PC-MULTA     = FUNCTION NUMVAL(WS-T-MULTA)
           MOVE WS-T-ULT              TO JUR-E-DT-ULT-APURACAO
           MOVE WS-T-VENC             TO JUR-E-DT-VENCIMENTO
           MOVE WS-T-REF              TO JUR-E-DT-REFERENCIA

           CALL 'JURS0100' USING JUR-AREA-CALCULO

           MOVE SPACES TO REG-SAIDA
           IF JUR-RET-OK
              MOVE JUR-S-PC-TAXA-APLICADA  TO WS-ED-TAXA
              MOVE JUR-S-QT-DIAS           TO WS-ED-DIAS
              MOVE JUR-S-QT-DIAS-ATRASO    TO WS-ED-ATRASO
              MOVE JUR-S-VL-JUROS-REMUN    TO WS-ED-REMUN
              MOVE JUR-S-VL-JUROS-MORA     TO WS-ED-MORA
              MOVE JUR-S-VL-MULTA          TO WS-ED-MULTA
              MOVE JUR-S-VL-TOTAL-ENCARGOS TO WS-ED-TOTAL
              MOVE JUR-S-VL-SALDO-ATUALIZ  TO WS-ED-SALDO
              STRING FUNCTION TRIM(WS-T-CASO)   ';'
                     JUR-CD-RETORNO             ';'
                     FUNCTION TRIM(WS-ED-TAXA)  ';'
                     FUNCTION TRIM(WS-ED-DIAS)  ';'
                     FUNCTION TRIM(WS-ED-ATRASO) ';'
                     FUNCTION TRIM(WS-ED-REMUN) ';'
                     FUNCTION TRIM(WS-ED-MORA)  ';'
                     FUNCTION TRIM(WS-ED-MULTA) ';'
                     FUNCTION TRIM(WS-ED-TOTAL) ';'
                     FUNCTION TRIM(WS-ED-SALDO)
                     DELIMITED BY SIZE INTO REG-SAIDA
              END-STRING
           ELSE
              STRING FUNCTION TRIM(WS-T-CASO)   ';'
                     JUR-CD-RETORNO             ';;;;;;;;'
                     DELIMITED BY SIZE INTO REG-SAIDA
              END-STRING
           END-IF
           WRITE REG-SAIDA.
