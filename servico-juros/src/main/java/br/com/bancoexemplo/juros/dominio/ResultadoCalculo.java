package br.com.bancoexemplo.juros.dominio;

import java.math.BigDecimal;

/**
 * Bloco JUR-SAIDA do copybook JURCCALC (retorno '00').
 *
 * @param numeroContrato      numero do contrato calculado
 * @param saldoDevedor        saldo considerado no calculo (escala 2)
 * @param taxaAplicada        JUR-S-PC-TAXA-APLICADA (escala 4)
 * @param dias                JUR-S-QT-DIAS
 * @param diasAtraso          JUR-S-QT-DIAS-ATRASO
 * @param emAtraso            JUR-S-FL-ATRASO = 'S'
 * @param jurosRemuneratorios JUR-S-VL-JUROS-REMUN
 * @param jurosMora           JUR-S-VL-JUROS-MORA
 * @param multa               JUR-S-VL-MULTA
 * @param totalEncargos       JUR-S-VL-TOTAL-ENCARGOS
 * @param saldoAtualizado     JUR-S-VL-SALDO-ATUALIZ
 */
public record ResultadoCalculo(
        String numeroContrato,
        BigDecimal saldoDevedor,
        BigDecimal taxaAplicada,
        long dias,
        long diasAtraso,
        boolean emAtraso,
        BigDecimal jurosRemuneratorios,
        BigDecimal jurosMora,
        BigDecimal multa,
        BigDecimal totalEncargos,
        BigDecimal saldoAtualizado) {
}
