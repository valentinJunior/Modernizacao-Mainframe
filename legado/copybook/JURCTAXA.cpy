      *----------------------------------------------------------------
      * COPYBOOK : JURCTAXA
      * SISTEMA  : JUR - APROPRIACAO DE JUROS DE CONTRATOS DE CREDITO
      * DESCRICAO: LAYOUT DO ARQUIVO DE TAXAS VIGENTES POR PRODUTO
      *            ORIGEM: UNLOAD DA TABELA DB2 BCO.TB_TAXA_PRODUTO
      *            (ORDENADO POR CD_PRODUTO - EXIGIDO PELO SEARCH ALL)
      * LRECL    : 45 BYTES - RECFM FB
      *----------------------------------------------------------------
      * POS  TAM  CAMPO
      * 001  003  CODIGO DO PRODUTO
      * 004  030  DESCRICAO DO PRODUTO
      * 034  004  TAXA DE JUROS REMUNERATORIOS % AO MES (PACKED 3,4)
      * 038  004  TAXA DE JUROS DE MORA % AO MES        (PACKED 3,4)
      * 042  004  PERCENTUAL DE MULTA POR ATRASO        (PACKED 3,4)
      *----------------------------------------------------------------
       01  REG-TAXA.
           05  TAX-CD-PRODUTO          PIC X(03).
           05  TAX-DS-PRODUTO          PIC X(30).
           05  TAX-PC-TAXA-MENSAL      PIC S9(03)V9(04) COMP-3.
           05  TAX-PC-MORA-MENSAL      PIC S9(03)V9(04) COMP-3.
           05  TAX-PC-MULTA            PIC S9(03)V9(04) COMP-3.
