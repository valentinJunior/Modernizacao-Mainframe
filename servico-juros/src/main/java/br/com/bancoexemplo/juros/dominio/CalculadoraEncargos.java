package br.com.bancoexemplo.juros.dominio;

import java.math.BigDecimal;
import java.math.MathContext;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.regex.Pattern;

/**
 * Equivalente Java da sub-rotina JURS0100.
 *
 * <p>Calcula os encargos de um contrato no periodo entre a ultima apuracao e a
 * data de referencia. Sem dependencia de framework: pode ser testada isolada.
 *
 * <p>Ordem das validacoes identica ao COBOL (1000-VALIDAR-ENTRADA,
 * 1100-VALIDAR-DATAS e 2000-APLICAR-SPREAD-RATING): quando ha mais de um erro,
 * o codigo devolvido e o mesmo do legado.
 */
public final class CalculadoraEncargos {

    public static final String VERSAO_REGRA = "JURS0100-equivalente-1.0";

    private static final BigDecimal CEM = new BigDecimal("100");
    private static final BigDecimal TRINTA = new BigDecimal("30");
    private static final BigDecimal TAXA_MAXIMA = new BigDecimal("30");
    private static final int ESCALA_VALOR = 2;
    private static final int ESCALA_TAXA = 4;
    private static final int ESCALA_EXPOENTE = 9;
    /** S9(13)V99: so cabem 13 digitos inteiros; o resto e truncado pela esquerda. */
    private static final BigDecimal LIMITE_INTEIROS_SALDO = BigDecimal.TEN.pow(13);
    private static final MathContext PRECISAO = MathContext.DECIMAL128;
    /**
     * Formato aceito para o saldo: sinal opcional, ate 18 digitos inteiros e ate 9
     * decimais. Sem notacao cientifica: um texto como "1E+50000000" faria o
     * BigDecimal operar com milhoes de digitos (DECISOES.md, D12).
     */
    private static final Pattern FORMATO_SALDO = Pattern.compile("-?\\d{1,18}(\\.\\d{1,9})?");
    private static final int TAMANHO_MAXIMO_SALDO = 40;

    private CalculadoraEncargos() {
    }

    /**
     * @throws RejeicaoException com o codigo do legado quando o contrato e rejeitado
     */
    public static ResultadoCalculo calcular(EntradaCalculo entrada, TabelaSpread tabelaSpread) {
        String contrato = entrada.numeroContrato();

        // ---- 1000-VALIDAR-ENTRADA ------------------------------------------
        BigDecimal saldo = converterSaldo(entrada.saldoDevedor(), contrato);
        if (saldo.signum() <= 0) {
            throw new RejeicaoException(CodigoRejeicao.SALDO_ZERADO_OU_NEGATIVO, contrato);
        }
        BigDecimal taxaBase = entrada.taxaBase();
        if (taxaBase == null || taxaBase.signum() <= 0 || taxaBase.compareTo(TAXA_MAXIMA) > 0) {
            throw new RejeicaoException(CodigoRejeicao.TAXA_FORA_DA_FAIXA, contrato);
        }

        // ---- 1100-VALIDAR-DATAS --------------------------------------------
        LocalDate ultimaApuracao = DataLegado.converter(entrada.dataUltimaApuracao())
                .orElseThrow(() -> new RejeicaoException(CodigoRejeicao.DATA_ULTIMA_APURACAO_INVALIDA, contrato));
        LocalDate vencimento = DataLegado.converter(entrada.dataVencimento())
                .orElseThrow(() -> new RejeicaoException(CodigoRejeicao.DATA_VENCIMENTO_INVALIDA, contrato));
        LocalDate referencia = DataLegado.converter(entrada.dataReferencia())
                .orElseThrow(() -> new RejeicaoException(CodigoRejeicao.DATA_REFERENCIA_INVALIDA, contrato));
        if (referencia.isBefore(ultimaApuracao)) {
            throw new RejeicaoException(CodigoRejeicao.DATA_REFERENCIA_ANTERIOR, contrato);
        }

        // ---- RN01 / 2000-APLICAR-SPREAD-RATING -----------------------------
        BigDecimal taxaAplicada = aplicarSpread(taxaBase, entrada.rating(), tabelaSpread, contrato);

        // ---- 3000-CALCULAR-PRAZO -------------------------------------------
        long dias = ChronoUnit.DAYS.between(ultimaApuracao, referencia);
        boolean emAtraso = referencia.isAfter(vencimento);
        long diasAtraso = emAtraso ? ChronoUnit.DAYS.between(vencimento, referencia) : 0;

        // ---- RN02 a RN05 ---------------------------------------------------
        BigDecimal jurosRemuneratorios = calcularJurosRemuneratorios(saldo, taxaAplicada, dias);
        BigDecimal jurosMora = zero();
        BigDecimal multa = zero();
        if (emAtraso) {
            jurosMora = calcularJurosMora(saldo, entrada.taxaMora(), Math.min(diasAtraso, dias));
            if (!vencimento.isBefore(ultimaApuracao)) {
                multa = calcularMulta(saldo, entrada.percentualMulta());
            }
        }
        BigDecimal total = jurosRemuneratorios.add(jurosMora).add(multa);

        return new ResultadoCalculo(contrato, saldo, taxaAplicada, dias, diasAtraso, emAtraso,
                jurosRemuneratorios, jurosMora, multa, total, saldo.add(total));
    }

    /**
     * Valida e converte o saldo (codigo 21) com a semantica do MOVE para
     * S9(13)V99: casas alem da segunda sao truncadas e digitos inteiros alem do
     * 13o sao descartados pela esquerda, sem aviso, exatamente como no COBOL
     * (ver DIVERGENCIAS.md, V1 - o dominio mantem a fidelidade ao legado; quem
     * recusa saldo acima da capacidade e a borda da API).
     *
     * <p>Antes da conversao, o texto precisa ser um decimal simples (D12): notacao
     * cientifica, hexadecimal ou texto longo demais sao "conteudo nao numerico".
     */
    static BigDecimal converterSaldo(String texto, String contrato) {
        String limpo = texto == null ? "" : texto.trim();
        if (limpo.length() > TAMANHO_MAXIMO_SALDO || !FORMATO_SALDO.matcher(limpo).matches()) {
            throw new RejeicaoException(CodigoRejeicao.SALDO_NAO_NUMERICO, contrato);
        }
        BigDecimal saldo = new BigDecimal(limpo);
        // remainder preserva o sinal do dividendo, como a truncagem de magnitude do COBOL
        return saldo.setScale(ESCALA_VALOR, RoundingMode.DOWN).remainder(LIMITE_INTEIROS_SALDO);
    }

    /**
     * RN01 - Taxa aplicada = taxa base do produto + spread do rating.
     *
     * @see "JURS0100 2000-APLICAR-SPREAD-RATING"
     */
    static BigDecimal aplicarSpread(BigDecimal taxaBase, String rating, TabelaSpread tabela, String contrato) {
        String chave = rating == null ? "" : rating.trim();
        BigDecimal spread = tabela.spreadDe(chave)
                .orElseThrow(() -> new RejeicaoException(CodigoRejeicao.RATING_NAO_RECONHECIDO, contrato));
        return taxaBase.add(spread).setScale(ESCALA_TAXA, RoundingMode.HALF_UP);
    }

    /**
     * RN02 - Juros compostos, mes comercial de 30 dias:
     * saldo x ((1 + taxa/100) ^ (dias/30) - 1).
     *
     * @see "JURS0100 4000-CALCULAR-JUROS-REMUN"
     */
    static BigDecimal calcularJurosRemuneratorios(BigDecimal saldo, BigDecimal taxaAplicada, long dias) {
        if (dias == 0) {
            return zero();
        }
        BigDecimal expoente = BigDecimal.valueOf(dias).divide(TRINTA, ESCALA_EXPOENTE, RoundingMode.HALF_UP);
        BigDecimal base = BigDecimal.ONE.add(taxaAplicada.divide(CEM, PRECISAO));
        BigDecimal fator = PotenciaFracionaria.calcularFatorJuros(base, expoente);
        return saldo.multiply(fator.subtract(BigDecimal.ONE)).setScale(ESCALA_VALOR, RoundingMode.HALF_UP);
    }

    /**
     * RN03 - Mora simples pro rata die, so sobre os dias de atraso dentro do
     * periodo apurado: saldo x mora / 100 x dias / 30 (mesma ordem do COMPUTE).
     *
     * @see "JURS0100 5000-CALCULAR-ENCARGOS-ATRASO"
     */
    static BigDecimal calcularJurosMora(BigDecimal saldo, BigDecimal taxaMora, long diasAtrasoNoPeriodo) {
        return saldo.multiply(taxaMora, PRECISAO)
                .divide(CEM, PRECISAO)
                .multiply(BigDecimal.valueOf(diasAtrasoNoPeriodo), PRECISAO)
                .divide(TRINTA, PRECISAO)
                .setScale(ESCALA_VALOR, RoundingMode.HALF_UP);
    }

    /**
     * RN04 - Multa unica, cobrada so no periodo em que o vencimento ocorreu
     * (vencimento &gt;= data da ultima apuracao).
     *
     * @see "JURS0100 5000-CALCULAR-ENCARGOS-ATRASO"
     */
    static BigDecimal calcularMulta(BigDecimal saldo, BigDecimal percentualMulta) {
        return saldo.multiply(percentualMulta, PRECISAO)
                .divide(CEM, PRECISAO)
                .setScale(ESCALA_VALOR, RoundingMode.HALF_UP);
    }

    private static BigDecimal zero() {
        return BigDecimal.ZERO.setScale(ESCALA_VALOR);
    }
}
