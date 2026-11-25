      *----------------------------------------------------------------
      * COPYBOOK : JURCREJE
      * SISTEMA  : JUR - APROPRIACAO DE JUROS DE CONTRATOS DE CREDITO
      * DESCRICAO: LAYOUT DO ARQUIVO DE CONTRATOS REJEITADOS
      *            (TRATADO PELA AREA DE OPERACOES NO D+1)
      * LRECL    : 80 BYTES - RECFM FB
      *----------------------------------------------------------------
      * CODIGOS DE REJEICAO:
      *   01      - PRODUTO SEM TAXA VIGENTE (GERADO PELO JURB0100)
      *   10 A 40 - ERROS DE CALCULO DEVOLVIDOS PELA SUB-ROTINA JURS0100
      *             (VER COPYBOOK JURCCALC)
      *----------------------------------------------------------------
       01  REG-REJEITO.
           05  REJ-NR-CONTRATO         PIC X(12).
           05  REJ-CD-AGENCIA          PIC X(04).
           05  REJ-CD-PRODUTO          PIC X(03).
           05  REJ-CD-MOTIVO           PIC X(02).
           05  REJ-DS-MOTIVO           PIC X(50).
           05  FILLER                  PIC X(09).
