package br.com.bancoexemplo.juros.api;

import br.com.bancoexemplo.juros.infra.TaxaProduto;

import java.math.BigDecimal;
import java.time.LocalDate;

public record TaxaResponse(
        String codigoProduto,
        String descricao,
        BigDecimal taxaMensal,
        BigDecimal moraMensal,
        BigDecimal multa,
        LocalDate inicioVigencia,
        LocalDate fimVigencia) {

    static TaxaResponse de(TaxaProduto t) {
        return new TaxaResponse(t.getCodigoProduto(), t.getDescricao(), t.getTaxaMensal(),
                t.getMoraMensal(), t.getMulta(), t.getInicioVigencia(), t.getFimVigencia());
    }
}
