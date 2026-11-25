package br.com.bancoexemplo.juros.api;

import br.com.bancoexemplo.juros.aplicacao.SolicitacaoCalculo;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * Saldo e datas sao recebidos como texto de proposito: a validacao fica no
 * dominio e devolve os codigos 21, 30, 31 e 33 do legado (e, no lote, nao
 * derruba a requisicao inteira por causa de um contrato).
 */
public record CalculoRequest(
        @Schema(example = "000012345678") @NotBlank @Size(max = 12) String numeroContrato,
        @Schema(example = "CDC") @NotBlank @Size(max = 3) String codigoProduto,
        @Schema(example = "B") String rating,
        @Schema(type = "number", example = "100000.00") String saldoDevedor,
        @Schema(example = "2026-10-25") String dataUltimaApuracao,
        @Schema(example = "2026-11-14") String dataVencimento,
        @Schema(example = "2026-11-24") String dataReferencia) {

    SolicitacaoCalculo paraSolicitacao() {
        return new SolicitacaoCalculo(numeroContrato, codigoProduto, rating, saldoDevedor,
                dataUltimaApuracao, dataVencimento, dataReferencia);
    }
}
