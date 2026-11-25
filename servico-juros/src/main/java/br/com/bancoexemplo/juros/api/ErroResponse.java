package br.com.bancoexemplo.juros.api;

import br.com.bancoexemplo.juros.dominio.CodigoRejeicao;
import com.fasterxml.jackson.annotation.JsonInclude;

/**
 * Corpo de erro padrao. {@code codigo} e o codigo do legado (01 a 40) ou
 * ENTRADA_INVALIDA para requisicao estruturalmente invalida (ver DECISOES.md, D4).
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record ErroResponse(String codigo, String mensagem, String contrato) {

    public static final String ENTRADA_INVALIDA = "ENTRADA_INVALIDA";

    static ErroResponse de(CodigoRejeicao c, String contrato) {
        return new ErroResponse(c.codigo(), c.mensagem(), contrato);
    }
}
