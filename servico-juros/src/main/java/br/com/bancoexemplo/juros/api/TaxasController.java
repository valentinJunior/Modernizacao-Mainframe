package br.com.bancoexemplo.juros.api;

import br.com.bancoexemplo.juros.aplicacao.CalculoEncargosService;
import br.com.bancoexemplo.juros.dominio.CodigoRejeicao;
import br.com.bancoexemplo.juros.dominio.DataLegado;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDate;

@RestController
@RequestMapping("/v1/taxas")
@Tag(name = "Taxas", description = "Taxas vigentes por produto (equivalente ao UNLOAD do STEP020)")
public class TaxasController {

    private final CalculoEncargosService servico;

    public TaxasController(CalculoEncargosService servico) {
        this.servico = servico;
    }

    @GetMapping("/{codigoProduto}")
    @Operation(summary = "Taxa, mora e multa vigentes do produto na data")
    public ResponseEntity<?> buscar(@PathVariable String codigoProduto, @RequestParam String data) {
        LocalDate dataVigencia = DataLegado.converter(data).orElse(null);
        if (dataVigencia == null) {
            CodigoRejeicao c = CodigoRejeicao.DATA_REFERENCIA_INVALIDA;
            return ResponseEntity.status(c.statusHttp()).body(ErroResponse.de(c, null));
        }
        return servico.buscarTaxaVigente(codigoProduto, dataVigencia)
                .<ResponseEntity<?>>map(t -> ResponseEntity.ok(TaxaResponse.de(t)))
                .orElseGet(() -> ResponseEntity.status(404)
                        .body(ErroResponse.de(CodigoRejeicao.PRODUTO_SEM_TAXA, null)));
    }
}
