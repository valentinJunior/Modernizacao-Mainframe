      *----------------------------------------------------------------
      * COPYBOOK : JURCCONT
      * SISTEMA  : JUR - APROPRIACAO DE JUROS DE CONTRATOS DE CREDITO
      * DESCRICAO: LAYOUT DO ARQUIVO DE CONTRATOS
      *            ORIGEM: UNLOAD DA TABELA DB2 BCO.TB_CONTRATO_CREDITO
      * LRECL    : 50 BYTES - RECFM FB
      *----------------------------------------------------------------
      * POS  TAM  CAMPO
      * 001  012  NUMERO DO CONTRATO
      * 013  004  CODIGO DA AGENCIA
      * 017  003  CODIGO DO PRODUTO DE CREDITO
      * 020  002  RATING DE RISCO (RES. CMN 2682: AA,A,B,...,H)
      * 022  008  SALDO DEVEDOR (PACKED 13,2)
      * 030  010  DATA DA ULTIMA APURACAO DE JUROS (AAAA-MM-DD)
      * 040  010  DATA DE VENCIMENTO DA PARCELA (AAAA-MM-DD)
      * 050  001  SITUACAO (A=ATIVO, L=LIQUIDADO, C=CANCELADO)
      *----------------------------------------------------------------
       01  REG-CONTRATO.
           05  CTR-NR-CONTRATO         PIC X(12).
           05  CTR-CD-AGENCIA          PIC X(04).
           05  CTR-CD-PRODUTO          PIC X(03).
           05  CTR-CD-RATING           PIC X(02).
           05  CTR-VL-SALDO-DEVEDOR    PIC S9(13)V99 COMP-3.
           05  CTR-DT-ULT-APURACAO     PIC X(10).
           05  CTR-DT-VENCIMENTO       PIC X(10).
           05  CTR-ST-CONTRATO         PIC X(01).
               88  CTR-ATIVO                     VALUE 'A'.
