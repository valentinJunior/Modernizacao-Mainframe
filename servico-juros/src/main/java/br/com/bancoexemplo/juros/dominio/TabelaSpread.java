package br.com.bancoexemplo.juros.dominio;

import java.math.BigDecimal;
import java.util.Optional;

/**
 * Spread de risco por rating, vigente na data de referencia.
 *
 * <p>No legado era o EVALUATE fixo do paragrafo 2000-APLICAR-SPREAD-RATING
 * (risco n. 1 da documentacao). Aqui vem de tabela com vigencia; o dominio so
 * conhece esta interface.
 */
@FunctionalInterface
public interface TabelaSpread {

    /** Spread em % a.m. (escala 4), ou vazio se o rating nao existir. */
    Optional<BigDecimal> spreadDe(String rating);
}
