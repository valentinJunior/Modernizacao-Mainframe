package br.com.bancoexemplo.juros.api;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Size;

import java.util.List;

public record LoteRequest(
        @NotEmpty @Size(max = LoteRequest.MAXIMO_CONTRATOS) List<@Valid CalculoRequest> contratos) {

    public static final int MAXIMO_CONTRATOS = 1000;
}
