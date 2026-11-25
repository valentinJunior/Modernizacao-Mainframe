      *----------------------------------------------------------------
      * COPYBOOK : JURCSAID
      * SISTEMA  : JUR - APROPRIACAO DE JUROS DE CONTRATOS DE CREDITO
      * DESCRICAO: LAYOUT DO ARQUIVO DE JUROS APROPRIADOS (SAIDA)
      *            CONSUMIDO PELA CONTABILIDADE E PELO STEP DE RESUMO
      * LRECL    : 100 BYTES - RECFM FB
      *----------------------------------------------------------------
      * POS  TAM  CAMPO
      * 001  012  NUMERO DO CONTRATO
      * 013  004  CODIGO DA AGENCIA
      * 017  003  CODIGO DO PRODUTO
      * 020  002  RATING DE RISCO
      * 022  008  SALDO DEVEDOR ANTERIOR          (PACKED 13,2)
      * 030  004  TAXA APLICADA % A.M.            (PACKED 3,4)
      * 034  005  QUANTIDADE DE DIAS APURADOS     (ZONADO)
      * 039  001  INDICADOR DE ATRASO (S/N)
      * 040  008  JUROS REMUNERATORIOS            (PACKED 13,2)
      * 048  008  JUROS DE MORA                   (PACKED 13,2)
      * 056  008  MULTA                           (PACKED 13,2)
      * 064  008  TOTAL DE ENCARGOS               (PACKED 13,2)
      * 072  008  SALDO DEVEDOR ATUALIZADO        (PACKED 13,2)
      * 080  010  DATA DE REFERENCIA (AAAA-MM-DD)
      * 090  011  RESERVADO
      *----------------------------------------------------------------
       01  REG-JUROS.
           05  JRS-NR-CONTRATO         PIC X(12).
           05  JRS-CD-AGENCIA          PIC X(04).
           05  JRS-CD-PRODUTO          PIC X(03).
           05  JRS-CD-RATING           PIC X(02).
           05  JRS-VL-SALDO-ANTERIOR   PIC S9(13)V99 COMP-3.
           05  JRS-PC-TAXA-APLICADA    PIC S9(03)V9(04) COMP-3.
           05  JRS-QT-DIAS             PIC 9(05).
           05  JRS-FL-ATRASO           PIC X(01).
           05  JRS-VL-JUROS-REMUN      PIC S9(13)V99 COMP-3.
           05  JRS-VL-JUROS-MORA       PIC S9(13)V99 COMP-3.
           05  JRS-VL-MULTA            PIC S9(13)V99 COMP-3.
           05  JRS-VL-TOTAL-ENCARGOS   PIC S9(13)V99 COMP-3.
           05  JRS-VL-SALDO-ATUALIZ    PIC S9(13)V99 COMP-3.
           05  JRS-DT-REFERENCIA       PIC X(10).
           05  FILLER                  PIC X(11).
