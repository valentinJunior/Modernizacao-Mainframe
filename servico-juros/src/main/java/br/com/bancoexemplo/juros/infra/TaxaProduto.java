package br.com.bancoexemplo.juros.infra;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.math.BigDecimal;
import java.time.LocalDate;

/**
 * Espelho da tabela DB2 BCO.TB_TAXA_PRODUTO (layout JURCTAXA + vigencia).
 */
@Entity
@Table(name = "TB_TAXA_PRODUTO")
public class TaxaProduto {

    @Id
    @Column(name = "ID")
    private Long id;

    @Column(name = "CD_PRODUTO", columnDefinition = "CHAR(3)", nullable = false)
    private String codigoProduto;

    @Column(name = "DS_PRODUTO", length = 30, nullable = false)
    private String descricao;

    @Column(name = "PC_TAXA_MENSAL", precision = 7, scale = 4, nullable = false)
    private BigDecimal taxaMensal;

    @Column(name = "PC_MORA_MENSAL", precision = 7, scale = 4, nullable = false)
    private BigDecimal moraMensal;

    @Column(name = "PC_MULTA", precision = 7, scale = 4, nullable = false)
    private BigDecimal multa;

    @Column(name = "DT_INI_VIGENCIA", nullable = false)
    private LocalDate inicioVigencia;

    @Column(name = "DT_FIM_VIGENCIA", nullable = false)
    private LocalDate fimVigencia;

    protected TaxaProduto() {
    }

    public Long getId() {
        return id;
    }

    public String getCodigoProduto() {
        return codigoProduto;
    }

    public String getDescricao() {
        return descricao;
    }

    public BigDecimal getTaxaMensal() {
        return taxaMensal;
    }

    public BigDecimal getMoraMensal() {
        return moraMensal;
    }

    public BigDecimal getMulta() {
        return multa;
    }

    public LocalDate getInicioVigencia() {
        return inicioVigencia;
    }

    public LocalDate getFimVigencia() {
        return fimVigencia;
    }
}
