package br.com.bancoexemplo.juros.dominio;

/**
 * Contrato rejeitado. Equivale a gravar o registro no arquivo REJEITOS do batch:
 * nao e erro de sistema, e um resultado de negocio com codigo do legado.
 */
public class RejeicaoException extends RuntimeException {

    private final CodigoRejeicao codigo;
    private final String numeroContrato;

    public RejeicaoException(CodigoRejeicao codigo, String numeroContrato) {
        super(codigo.codigo() + " - " + codigo.mensagem());
        this.codigo = codigo;
        this.numeroContrato = numeroContrato;
    }

    public CodigoRejeicao codigo() {
        return codigo;
    }

    public String numeroContrato() {
        return numeroContrato;
    }
}
