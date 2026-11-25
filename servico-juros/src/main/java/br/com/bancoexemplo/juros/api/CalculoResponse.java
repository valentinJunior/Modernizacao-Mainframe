package br.com.bancoexemplo.juros.api;

import br.com.bancoexemplo.juros.dominio.CalculadoraEncargos;
import br.com.bancoexemplo.juros.dominio.ResultadoCalculo;

import java.math.BigDecimal;

public record CalculoResponse(
        String numeroContrato,
        BigDecimal taxaAplicada,
        long dias,
        long diasAtraso,
        boolean emAtraso,
        BigDecimal jurosRemuneratorios,
        BigDecimal jurosMora,
        BigDecimal multa,
        BigDecimal totalEncargos,
        BigDecimal saldoAtualizado,
        String regraVersao) {

    static CalculoResponse de(ResultadoCalculo r) {
        return new CalculoResponse(r.numeroContrato(), r.taxaAplicada(), r.dias(), r.diasAtraso(),
                r.emAtraso(), r.jurosRemuneratorios(), r.jurosMora(), r.multa(), r.totalEncargos(),
                r.saldoAtualizado(), CalculadoraEncargos.VERSAO_REGRA);
    }
}
