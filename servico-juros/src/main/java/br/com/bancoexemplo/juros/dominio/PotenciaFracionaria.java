package br.com.bancoexemplo.juros.dominio;

import java.math.BigDecimal;
import java.math.RoundingMode;

/**
 * Unico ponto do servico onde se usa ponto flutuante (ver DECISOES.md, D2).
 *
 * <p>O COBOL calcula {@code (1 + TAXA / 100) ** WS-EXPOENTE} com expoente
 * fracionario, o que o compilador resolve internamente em ponto flutuante, e
 * em seguida arredonda para WS-FATOR-JUROS PIC S9(03)V9(12) com ROUNDED.
 * Aqui reproduzimos o mesmo: potencia em double e arredondamento imediato
 * para escala 12, HALF_UP. Se aparecer diferenca de centavo entre plataformas,
 * e neste metodo que ela nasce.
 */
public final class PotenciaFracionaria {

    static final int ESCALA_FATOR = 12;

    private PotenciaFracionaria() {
    }

    /**
     * @param base     (1 + taxa / 100), exata em decimal
     * @param expoente dias / 30, ja arredondado para escala 9
     * @return fator de juros com escala 12 (HALF_UP)
     * @see "JURS0100 4000-CALCULAR-JUROS-REMUN"
     */
    public static BigDecimal calcularFatorJuros(BigDecimal base, BigDecimal expoente) {
        double fator = Math.pow(base.doubleValue(), expoente.doubleValue());
        // new BigDecimal(double) usa o valor binario exato, sem arredondamento previo de texto
        return new BigDecimal(fator).setScale(ESCALA_FATOR, RoundingMode.HALF_UP);
    }
}
