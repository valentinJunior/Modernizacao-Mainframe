package br.com.bancoexemplo.juros.api;

import br.com.bancoexemplo.juros.aplicacao.ItemLote;
import com.fasterxml.jackson.annotation.JsonInclude;

import java.util.List;

public record LoteResponse(int quantidade, long calculados, long rejeitados, List<Item> itens) {

    public enum Status { CALCULADO, REJEITADO }

    @JsonInclude(JsonInclude.Include.NON_NULL)
    public record Item(String numeroContrato, Status status, CalculoResponse resultado, ErroResponse erro) {
    }

    static LoteResponse de(List<ItemLote> itens) {
        List<Item> convertidos = itens.stream().map(i -> i.foiCalculado()
                ? new Item(i.numeroContrato(), Status.CALCULADO, CalculoResponse.de(i.resultado()), null)
                : new Item(i.numeroContrato(), Status.REJEITADO, null,
                        ErroResponse.de(i.rejeicao(), i.numeroContrato()))).toList();
        long calculados = itens.stream().filter(ItemLote::foiCalculado).count();
        return new LoteResponse(itens.size(), calculados, itens.size() - calculados, convertidos);
    }
}
