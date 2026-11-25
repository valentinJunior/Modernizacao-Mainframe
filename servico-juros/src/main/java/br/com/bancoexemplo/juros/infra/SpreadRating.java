package br.com.bancoexemplo.juros.infra;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.math.BigDecimal;
import java.time.LocalDate;

/**
 * Spread de risco por rating com vigencia. Substitui a tabela fixa do
 * paragrafo 2000-APLICAR-SPREAD-RATING do JURS0100 (risco n. 1 da documentacao).
 */
@Entity
@Table(name = "TB_SPREAD_RATING")
public class SpreadRating {

    @Id
    @Column(name = "ID")
    private Long id;

    @Column(name = "CD_RATING", length = 2, nullable = false)
    private String rating;

    @Column(name = "PC_SPREAD_MENSAL", precision = 7, scale = 4, nullable = false)
    private BigDecimal spreadMensal;

    @Column(name = "DT_INI_VIGENCIA", nullable = false)
    private LocalDate inicioVigencia;

    @Column(name = "DT_FIM_VIGENCIA", nullable = false)
    private LocalDate fimVigencia;

    protected SpreadRating() {
    }

    public String getRating() {
        return rating;
    }

    public BigDecimal getSpreadMensal() {
        return spreadMensal;
    }

    public LocalDate getInicioVigencia() {
        return inicioVigencia;
    }

    public LocalDate getFimVigencia() {
        return fimVigencia;
    }
}
