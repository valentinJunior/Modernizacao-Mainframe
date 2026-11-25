package br.com.bancoexemplo.juros.aplicacao;

/**
 * Dados de um contrato como chegam do cliente (equivalente ao registro JURCCONT).
 * Saldo e datas em texto: quem valida e o dominio, com os codigos do legado.
 */
public record SolicitacaoCalculo(
        String numeroContrato,
        String codigoProduto,
        String rating,
        String saldoDevedor,
        String dataUltimaApuracao,
        String dataVencimento,
        String dataReferencia) {
}
