package br.com.bancoexemplo.juros.dominio;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Timeout;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import java.math.BigDecimal;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Testes por regra de negocio (RN01 a RN05) e pela ordem das validacoes.
 * Os valores de borda completos estao em EquivalenciaLegadoTest / casos.csv.
 */
class CalculadoraEncargosTest {

    private static final TabelaSpread TABELA = EquivalenciaLegadoTest.TABELA;

    private static EntradaCalculo entrada(String rating, String saldo, String ult, String venc, String ref) {
        return new EntradaCalculo("000012345678", rating, saldo, new BigDecimal("1.8000"),
                new BigDecimal("1.0000"), new BigDecimal("2.0000"), ult, venc, ref);
    }

    private static ResultadoCalculo exemploDocumentacao() {
        return CalculadoraEncargos.calcular(
                entrada("B", "100000.00", "2026-10-25", "2026-11-14", "2026-11-24"), TABELA);
    }

    @Nested
    @DisplayName("Exemplo numerico da Documentacao Tecnica JURD0100")
    class ExemploDocumentacao {

        @Test
        void rn01TaxaAplicadaSomaSpreadDoRating() {
            assertThat(exemploDocumentacao().taxaAplicada()).isEqualByComparingTo("2.05");
        }

        @Test
        void rn02JurosRemuneratoriosCompostos() {
            assertThat(exemploDocumentacao().jurosRemuneratorios()).isEqualByComparingTo("2050.00");
        }

        @Test
        void rn03MoraProporcionalAosDiasDeAtraso() {
            ResultadoCalculo r = exemploDocumentacao();
            assertThat(r.diasAtraso()).isEqualTo(10);
            assertThat(r.jurosMora()).isEqualByComparingTo("333.33");
        }

        @Test
        void rn04MultaCobradaNoPeriodoDoVencimento() {
            assertThat(exemploDocumentacao().multa()).isEqualByComparingTo("2000.00");
        }

        @Test
        void rn05TotalESaldoAtualizado() {
            ResultadoCalculo r = exemploDocumentacao();
            assertThat(r.totalEncargos()).isEqualByComparingTo("4383.33");
            assertThat(r.saldoAtualizado()).isEqualByComparingTo("104383.33");
        }
    }

    @Test
    void rotinaDiariaEmDiaRende6767() {
        ResultadoCalculo r = CalculadoraEncargos.calcular(
                entrada("B", "100000.00", "2026-11-23", "2026-12-14", "2026-11-24"), TABELA);
        assertThat(r.totalEncargos()).isEqualByComparingTo("67.67");
        assertThat(r.emAtraso()).isFalse();
    }

    @Test
    void multaNaoECobradaDeNovoNosDiasSeguintes() {
        // vencimento antes da ultima apuracao: o contrato ja estava atrasado na noite anterior
        ResultadoCalculo r = CalculadoraEncargos.calcular(
                entrada("B", "100000.00", "2026-11-15", "2026-11-14", "2026-11-16"), TABELA);
        assertThat(r.jurosMora()).isPositive();
        assertThat(r.multa()).isZero();
    }

    @Test
    void ratingComEspacosDoCobolEAceito() {
        ResultadoCalculo r = CalculadoraEncargos.calcular(
                entrada("B ", "100000.00", "2026-10-25", "2026-11-14", "2026-11-24"), TABELA);
        assertThat(r.taxaAplicada()).isEqualByComparingTo("2.05");
    }

    @Test
    void ratingEmMinusculaERejeitadoComoNoCobol() {
        assertThatThrownBy(() -> CalculadoraEncargos.calcular(
                entrada("b", "100000.00", "2026-10-25", "2026-11-14", "2026-11-24"), TABELA))
                .isInstanceOfSatisfying(RejeicaoException.class,
                        e -> assertThat(e.codigo()).isEqualTo(CodigoRejeicao.RATING_NAO_RECONHECIDO));
    }

    @Test
    void saldoComMaisDe13DigitosInteirosETruncadoPelaEsquerdaComoNoMove() {
        // fidelidade ao legado (DIVERGENCIAS.md, V1): 12.345.678.901.234,00 vira 2.345.678.901.234,00
        ResultadoCalculo r = CalculadoraEncargos.calcular(
                entrada("B", "12345678901234.00", "2026-10-25", "2026-11-14", "2026-11-24"), TABELA);
        assertThat(r.saldoDevedor()).isEqualByComparingTo("2345678901234.00");
    }

    /**
     * Achado de revisao externa (DECISOES.md, D12): notacao cientifica levava a
     * 44 s de CPU ("1E+50000000") ou a ArithmeticException ("1E+999999999").
     */
    @ParameterizedTest
    @ValueSource(strings = {"1E+50000000", "1E+999999999", "1E+3", "1e5", "0x10", ".5", "1.",
            "NaN", "Infinity", "1234567890123456789.00", "1.0000000001"})
    @Timeout(2)
    void saldoForaDoFormatoDecimalSimplesERejeitadoComo21SemCusto(String saldo) {
        assertThatThrownBy(() -> CalculadoraEncargos.calcular(
                entrada("B", saldo, "2026-10-25", "2026-11-14", "2026-11-24"), TABELA))
                .isInstanceOfSatisfying(RejeicaoException.class,
                        e -> assertThat(e.codigo()).isEqualTo(CodigoRejeicao.SALDO_NAO_NUMERICO));
    }

    @Test
    @Timeout(2)
    void saldoGiganteERejeitadoSemConverter() {
        String gigante = "9".repeat(5_000_000);
        assertThatThrownBy(() -> CalculadoraEncargos.calcular(
                entrada("B", gigante, "2026-10-25", "2026-11-14", "2026-11-24"), TABELA))
                .isInstanceOfSatisfying(RejeicaoException.class,
                        e -> assertThat(e.codigo()).isEqualTo(CodigoRejeicao.SALDO_NAO_NUMERICO));
    }

    @Test
    void ordemDasValidacoesSegueOCobol() {
        // saldo zero (20), data invalida (30) e rating invalido (40) ao mesmo tempo: vale o 20
        assertThatThrownBy(() -> CalculadoraEncargos.calcular(
                entrada("X", "0", "2026-02-30", "2026-11-14", "2026-11-24"), TABELA))
                .isInstanceOfSatisfying(RejeicaoException.class,
                        e -> assertThat(e.codigo()).isEqualTo(CodigoRejeicao.SALDO_ZERADO_OU_NEGATIVO));
        // data invalida (30) e rating invalido (40): vale o 30, porque datas sao validadas antes do spread
        assertThatThrownBy(() -> CalculadoraEncargos.calcular(
                entrada("X", "100.00", "2026-02-30", "2026-11-14", "2026-11-24"), TABELA))
                .isInstanceOfSatisfying(RejeicaoException.class,
                        e -> assertThat(e.codigo()).isEqualTo(CodigoRejeicao.DATA_ULTIMA_APURACAO_INVALIDA));
    }
}
