      *----------------------------------------------------------------
      * COPYBOOK : JURCCALC
      * SISTEMA  : JUR - APROPRIACAO DE JUROS DE CONTRATOS DE CREDITO
      * DESCRICAO: AREA DE COMUNICACAO ENTRE O PROGRAMA JURB0100 E A
      *            SUB-ROTINA DE CALCULO JURS0100 (CALL ... USING)
      *----------------------------------------------------------------
      * RETORNOS POSSIVEIS (JUR-CD-RETORNO):
      *   00 - CALCULO EFETUADO COM SUCESSO
      *   10 - TAXA BASE FORA DA FAIXA PERMITIDA
      *   20 - SALDO DEVEDOR ZERADO OU NEGATIVO
      *   21 - SALDO DEVEDOR COM CONTEUDO NAO NUMERICO
      *   30 - DATA DA ULTIMA APURACAO INVALIDA
      *   31 - DATA DE VENCIMENTO INVALIDA
      *   32 - DATA DE REFERENCIA ANTERIOR A ULTIMA APURACAO
      *   33 - DATA DE REFERENCIA INVALIDA
      *   40 - RATING DE RISCO NAO RECONHECIDO
      *----------------------------------------------------------------
       01  JUR-AREA-CALCULO.
      *--- DADOS DE ENTRADA (PREENCHIDOS PELO PROGRAMA CHAMADOR) ------
           05  JUR-ENTRADA.
               10  JUR-E-NR-CONTRATO       PIC X(12).
               10  JUR-E-CD-RATING         PIC X(02).
               10  JUR-E-VL-SALDO          PIC S9(13)V99 COMP-3.
               10  JUR-E-PC-TAXA-BASE      PIC S9(03)V9(04) COMP-3.
               10  JUR-E-PC-MORA           PIC S9(03)V9(04) COMP-3.
               10  JUR-E-PC-MULTA          PIC S9(03)V9(04) COMP-3.
               10  JUR-E-DT-ULT-APURACAO   PIC X(10).
               10  JUR-E-DT-VENCIMENTO     PIC X(10).
               10  JUR-E-DT-REFERENCIA     PIC X(10).
      *--- DADOS DE SAIDA (DEVOLVIDOS PELA SUB-ROTINA) -----------------
           05  JUR-SAIDA.
               10  JUR-S-PC-TAXA-APLICADA  PIC S9(03)V9(04) COMP-3.
               10  JUR-S-QT-DIAS           PIC S9(05) COMP-3.
               10  JUR-S-QT-DIAS-ATRASO    PIC S9(05) COMP-3.
               10  JUR-S-FL-ATRASO         PIC X(01).
                   88  JUR-S-EM-ATRASO               VALUE 'S'.
                   88  JUR-S-EM-DIA                  VALUE 'N'.
               10  JUR-S-VL-JUROS-REMUN    PIC S9(13)V99 COMP-3.
               10  JUR-S-VL-JUROS-MORA     PIC S9(13)V99 COMP-3.
               10  JUR-S-VL-MULTA          PIC S9(13)V99 COMP-3.
               10  JUR-S-VL-TOTAL-ENCARGOS PIC S9(13)V99 COMP-3.
               10  JUR-S-VL-SALDO-ATUALIZ  PIC S9(13)V99 COMP-3.
      *--- RETORNO -----------------------------------------------------
           05  JUR-RETORNO.
               10  JUR-CD-RETORNO          PIC X(02).
                   88  JUR-RET-OK                    VALUE '00'.
               10  JUR-DS-RETORNO          PIC X(50).
