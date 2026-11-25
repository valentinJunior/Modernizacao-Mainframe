package br.com.bancoexemplo.juros.dominio;

import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvFileSource;

import java.math.BigDecimal;
import java.util.Map;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Equivalencia com o legado: cada campo comparado ao centavo.
 *
 * <p>Cada linha de casos.csv tem a entrada e o resultado esperado. Hoje a massa
 * vem da documentacao e da implementacao de referencia (ferramentas/), e foi
 * conferida contra a JURS0100 original compilada com GnuCOBOL
 * (../equivalencia-cobol/: 27 de 27 identicos). GnuCOBOL nao e o Enterprise COBOL
 * do z/OS: a validacao definitiva vem da massa real do JUROSOUT, que entra no
 * mesmo arquivo quando for extraida do mainframe.
 * A comparacao e por texto (toPlainString): escala diferente tambem falha.
 */
class EquivalenciaLegadoTest {

    /** Valores do EVALUATE do JURS0100 (os mesmos da carga V2__carga_inicial.sql). */
    static final Map<String, BigDecimal> SPREAD_LEGADO = Map.of(
            "AA", new BigDecimal("0.0000"), "A", new BigDecimal("0.1000"), "B", new BigDecimal("0.2500"),
            "C", new BigDecimal("0.5000"), "D", new BigDecimal("0.7500"), "E", new BigDecimal("1.0000"),
            "F", new BigDecimal("1.2500"), "G", new BigDecimal("1.5000"), "H", new BigDecimal("2.0000"));

    static final TabelaSpread TABELA = rating -> Optional.ofNullable(SPREAD_LEGADO.get(rating));

    @ParameterizedTest(name = "{0}")
    @CsvFileSource(resources = "/equivalencia/casos.csv", delimiter = ';', numLinesToSkip = 1)
    void resultadoIgualAoLegado(String caso, String rating, String saldo, String taxaBase, String mora,
                                String multa, String ultimaApuracao, String vencimento, String referencia,
                                String codigo, String taxaAplicada, String dias, String diasAtraso,
                                String jurosRemun, String jurosMora, String valorMulta, String total,
                                String saldoAtualizado) {

        EntradaCalculo entrada = new EntradaCalculo(caso, rating, saldo, new BigDecimal(taxaBase),
                new BigDecimal(mora), new BigDecimal(multa), ultimaApuracao, vencimento, referencia);

        if (!"00".equals(codigo)) {
            assertThatThrownBy(() -> CalculadoraEncargos.calcular(entrada, TABELA))
                    .isInstanceOfSatisfying(RejeicaoException.class,
                            e -> assertThat(e.codigo().codigo()).as("codigo de rejeicao").isEqualTo(codigo));
            return;
        }

        ResultadoCalculo r = CalculadoraEncargos.calcular(entrada, TABELA);
        assertThat(r.taxaAplicada().toPlainString()).as("taxa aplicada").isEqualTo(taxaAplicada);
        assertThat(r.dias()).as("dias").isEqualTo(Long.parseLong(dias));
        assertThat(r.diasAtraso()).as("dias de atraso").isEqualTo(Long.parseLong(diasAtraso));
        assertThat(r.jurosRemuneratorios().toPlainString()).as("juros remuneratorios").isEqualTo(jurosRemun);
        assertThat(r.jurosMora().toPlainString()).as("juros de mora").isEqualTo(jurosMora);
        assertThat(r.multa().toPlainString()).as("multa").isEqualTo(valorMulta);
        assertThat(r.totalEncargos().toPlainString()).as("total de encargos").isEqualTo(total);
        assertThat(r.saldoAtualizado().toPlainString()).as("saldo atualizado").isEqualTo(saldoAtualizado);
    }
}
