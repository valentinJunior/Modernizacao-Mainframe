package br.com.bancoexemplo.juros.aplicacao;

import br.com.bancoexemplo.juros.dominio.CodigoRejeicao;
import br.com.bancoexemplo.juros.dominio.ResultadoCalculo;

/**
 * Resultado de um contrato dentro de um lote: calculado (arquivo JUROSOUT)
 * ou rejeitado (arquivo REJEITOS). Exatamente um dos dois e preenchido.
 */
public record ItemLote(String numeroContrato, ResultadoCalculo resultado, CodigoRejeicao rejeicao) {

    public static ItemLote calculado(ResultadoCalculo resultado) {
        return new ItemLote(resultado.numeroContrato(), resultado, null);
    }

    public static ItemLote rejeitado(String numeroContrato, CodigoRejeicao rejeicao) {
        return new ItemLote(numeroContrato, null, rejeicao);
    }

    public boolean foiCalculado() {
        return resultado != null;
    }
}
