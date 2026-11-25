package br.com.bancoexemplo.juros.dominio;

/**
 * Codigos de rejeicao do legado, mantidos identicos para permitir a conciliacao
 * com o arquivo BCO.JUR.APROP.REJEITOS do batch. A unica excecao e
 * {@link #SALDO_ACIMA_DA_CAPACIDADE}, que so existe no servico.
 *
 * @see "copybook JURCCALC (retornos) e JURCREJE (codigo 01)"
 */
public enum CodigoRejeicao {

    /** Gerado pelo JURB0100 quando o SEARCH ALL nao encontra a taxa do produto. */
    PRODUTO_SEM_TAXA("01", "Produto sem taxa vigente cadastrada", 422),
    TAXA_FORA_DA_FAIXA("10", "Taxa base fora da faixa permitida (0 a 30% a.m.)", 422),
    SALDO_ZERADO_OU_NEGATIVO("20", "Saldo devedor zerado ou negativo", 422),
    SALDO_NAO_NUMERICO("21", "Saldo devedor com conteudo nao numerico", 400),
    DATA_ULTIMA_APURACAO_INVALIDA("30", "Data da ultima apuracao invalida", 400),
    DATA_VENCIMENTO_INVALIDA("31", "Data de vencimento invalida", 400),
    DATA_REFERENCIA_ANTERIOR("32", "Data de referencia anterior a ultima apuracao", 422),
    DATA_REFERENCIA_INVALIDA("33", "Data de referencia invalida", 400),
    RATING_NAO_RECONHECIDO("40", "Rating de risco nao reconhecido", 422),
    /**
     * Sem equivalente no legado (DIVERGENCIAS.md, V1): a API recusa um saldo que
     * nao cabe em S9(13)V99, em vez de trunca-lo em silencio como o MOVE do COBOL.
     */
    SALDO_ACIMA_DA_CAPACIDADE("ENTRADA_INVALIDA", "Saldo devedor com mais de 13 digitos inteiros", 400);

    private final String codigo;
    private final String mensagem;
    private final int statusHttp;

    CodigoRejeicao(String codigo, String mensagem, int statusHttp) {
        this.codigo = codigo;
        this.mensagem = mensagem;
        this.statusHttp = statusHttp;
    }

    public String codigo() {
        return codigo;
    }

    public String mensagem() {
        return mensagem;
    }

    public int statusHttp() {
        return statusHttp;
    }
}
