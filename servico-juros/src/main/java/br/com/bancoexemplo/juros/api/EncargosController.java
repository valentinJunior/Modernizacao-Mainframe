package br.com.bancoexemplo.juros.api;

import br.com.bancoexemplo.juros.aplicacao.CalculoEncargosService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/v1/encargos")
@Tag(name = "Encargos", description = "Calculo de juros, mora e multa (equivalente ao JURB0100 + JURS0100)")
public class EncargosController {

    private final CalculoEncargosService servico;

    public EncargosController(CalculoEncargosService servico) {
        this.servico = servico;
    }

    @PostMapping("/calcular")
    @Operation(summary = "Calcula os encargos de um contrato",
            description = "Rejeicoes devolvem o codigo do legado (01 a 40) no corpo do erro.")
    public CalculoResponse calcular(@Valid @RequestBody CalculoRequest requisicao) {
        return CalculoResponse.de(servico.calcular(requisicao.paraSolicitacao()));
    }

    @PostMapping("/calcular-lote")
    @Operation(summary = "Calcula ate 1.000 contratos",
            description = "Um contrato rejeitado nao interrompe o lote, como no batch.")
    public LoteResponse calcularLote(@Valid @RequestBody LoteRequest requisicao) {
        return LoteResponse.de(servico.calcularLote(
                requisicao.contratos().stream().map(CalculoRequest::paraSolicitacao).toList()));
    }
}
