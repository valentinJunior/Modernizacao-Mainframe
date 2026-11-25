package br.com.bancoexemplo.juros.dominio;

import java.math.BigDecimal;

/**
 * Bloco JUR-ENTRADA do copybook JURCCALC.
 *
 * <p>Saldo e datas chegam como texto, do jeito que o COBOL os recebe, para que a
 * propria calculadora faca as validacoes 21, 30, 31 e 33 na mesma ordem do
 * JURS0100. As taxas ja vem tipadas porque saem do repositorio, nao do cliente.
 *
 * @param numeroContrato     JUR-E-NR-CONTRATO
 * @param rating             JUR-E-CD-RATING (sem os espacos de preenchimento do COBOL)
 * @param saldoDevedor       JUR-E-VL-SALDO, em texto
 * @param taxaBase           JUR-E-PC-TAXA-BASE (% a.m.)
 * @param taxaMora           JUR-E-PC-MORA (% a.m.)
 * @param percentualMulta    JUR-E-PC-MULTA (%)
 * @param dataUltimaApuracao JUR-E-DT-ULT-APURACAO (AAAA-MM-DD)
 * @param dataVencimento     JUR-E-DT-VENCIMENTO (AAAA-MM-DD)
 * @param dataReferencia     JUR-E-DT-REFERENCIA (AAAA-MM-DD)
 */
public record EntradaCalculo(
        String numeroContrato,
        String rating,
        String saldoDevedor,
        BigDecimal taxaBase,
        BigDecimal taxaMora,
        BigDecimal percentualMulta,
        String dataUltimaApuracao,
        String dataVencimento,
        String dataReferencia) {
}
