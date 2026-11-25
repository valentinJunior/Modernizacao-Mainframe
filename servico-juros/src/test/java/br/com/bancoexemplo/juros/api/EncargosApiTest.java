package br.com.bancoexemplo.juros.api;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Timeout;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Testes de API com a aplicacao inteira no ar (H2 + Flyway com a carga inicial).
 */
@SpringBootTest
@AutoConfigureMockMvc
class EncargosApiTest {

    private static final String EXEMPLO = """
            {
              "numeroContrato": "000012345678",
              "codigoProduto": "CDC",
              "rating": "B",
              "saldoDevedor": 100000.00,
              "dataUltimaApuracao": "2026-10-25",
              "dataVencimento": "2026-11-14",
              "dataReferencia": "2026-11-24"
            }
            """;

    @Autowired
    MockMvc mvc;

    private ResultActions calcular(String json) throws Exception {
        return mvc.perform(post("/v1/encargos/calcular").contentType(MediaType.APPLICATION_JSON).content(json));
    }

    @Test
    void exemploDaDocumentacao() throws Exception {
        calcular(EXEMPLO)
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.taxaAplicada").value(2.05))
                .andExpect(jsonPath("$.dias").value(30))
                .andExpect(jsonPath("$.diasAtraso").value(10))
                .andExpect(jsonPath("$.emAtraso").value(true))
                .andExpect(jsonPath("$.jurosRemuneratorios").value(2050.00))
                .andExpect(jsonPath("$.jurosMora").value(333.33))
                .andExpect(jsonPath("$.multa").value(2000.00))
                .andExpect(jsonPath("$.totalEncargos").value(4383.33))
                .andExpect(jsonPath("$.saldoAtualizado").value(104383.33))
                .andExpect(jsonPath("$.regraVersao").value("JURS0100-equivalente-1.0"));
    }

    @Test
    void saldoEnviadoComoTextoTambemEAceito() throws Exception {
        calcular(EXEMPLO.replace("100000.00", "\"100000.00\""))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.totalEncargos").value(4383.33));
    }

    @Test
    void ratingInvalidoDevolveCodigo40() throws Exception {
        calcular(EXEMPLO.replace("\"B\"", "\"X\""))
                .andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.codigo").value("40"))
                .andExpect(jsonPath("$.mensagem").value("Rating de risco nao reconhecido"))
                .andExpect(jsonPath("$.contrato").value("000012345678"));
    }

    @Test
    void produtoSemTaxaDevolveCodigo01() throws Exception {
        calcular(EXEMPLO.replace("\"CDC\"", "\"XYZ\""))
                .andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.codigo").value("01"));
    }

    @Test
    void produtoComTaxaCadastradaInvalidaDevolveCodigo10() throws Exception {
        calcular(EXEMPLO.replace("\"CDC\"", "\"ERR\""))
                .andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.codigo").value("10"));
    }

    @Test
    void saldoNaoNumericoDevolveCodigo21() throws Exception {
        calcular(EXEMPLO.replace("100000.00", "\"ABC\""))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.codigo").value("21"));
    }

    /** Achado de revisao externa (D12): antes, 44 s de CPU e HTTP 500. */
    @ParameterizedTest
    @ValueSource(strings = {"\"1E+50000000\"", "\"1E+999999999\"", "1E+999999999", "1E+3"})
    @Timeout(10)
    void saldoEmNotacaoCientificaERecusadoNaHoraComCodigo21(String saldo) throws Exception {
        calcular(EXEMPLO.replace("100000.00", saldo))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.codigo").value("21"));
    }

    @Test
    void saldoComMaisDe13DigitosInteirosERecusadoNaApi() throws Exception {
        // DIVERGENCIAS.md, V1: o dominio truncaria como o MOVE; a API recusa
        calcular(EXEMPLO.replace("100000.00", "\"12345678901234.00\""))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.codigo").value("ENTRADA_INVALIDA"));
    }

    @Test
    void saldoNoLimiteDe13DigitosInteirosEAceito() throws Exception {
        calcular(EXEMPLO.replace("100000.00", "\"0009999999999999.99\""))
                .andExpect(status().isOk());
    }

    @Test
    void dataInexistenteDevolveCodigo30() throws Exception {
        calcular(EXEMPLO.replace("2026-10-25", "2026-02-30"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.codigo").value("30"));
    }

    @Test
    void dataDeReferenciaInvalidaDevolveCodigo33() throws Exception {
        calcular(EXEMPLO.replace("2026-11-24", "24/11/2026"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.codigo").value("33"));
    }

    @Test
    void taxaUsadaEAVigenteNaDataDeReferencia() throws Exception {
        // em marco/2026 o CDC tinha 1,95% a.m. (primeira vigencia da carga inicial)
        calcular(EXEMPLO.replace("2026-10-25", "2026-02-15")
                        .replace("2026-11-14", "2026-04-15")
                        .replace("2026-11-24", "2026-03-15"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.taxaAplicada").value(2.20));
    }

    @Test
    void requisicaoSemContratoEEntradaInvalida() throws Exception {
        calcular(EXEMPLO.replace("\"000012345678\"", "\"\""))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.codigo").value("ENTRADA_INVALIDA"));
    }

    @Test
    void loteComContratoInvalidoNoMeioCalculaOsDemais() throws Exception {
        String invalido = EXEMPLO.replace("000012345678", "000000000002").replace("\"B\"", "\"X\"");
        String terceiro = EXEMPLO.replace("000012345678", "000000000003");
        String lote = "{\"contratos\": [" + EXEMPLO + "," + invalido + "," + terceiro + "]}";

        mvc.perform(post("/v1/encargos/calcular-lote").contentType(MediaType.APPLICATION_JSON).content(lote))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.quantidade").value(3))
                .andExpect(jsonPath("$.calculados").value(2))
                .andExpect(jsonPath("$.rejeitados").value(1))
                .andExpect(jsonPath("$.itens[0].status").value("CALCULADO"))
                .andExpect(jsonPath("$.itens[0].resultado.totalEncargos").value(4383.33))
                .andExpect(jsonPath("$.itens[1].status").value("REJEITADO"))
                .andExpect(jsonPath("$.itens[1].erro.codigo").value("40"))
                .andExpect(jsonPath("$.itens[2].status").value("CALCULADO"));
    }

    @Test
    void loteComSaldoAcimaDaCapacidadeRecusaSoAqueleContrato() throws Exception {
        String grande = EXEMPLO.replace("000012345678", "000000000002").replace("100000.00", "\"12345678901234.00\"");
        String lote = "{\"contratos\": [" + EXEMPLO + "," + grande + "]}";

        mvc.perform(post("/v1/encargos/calcular-lote").contentType(MediaType.APPLICATION_JSON).content(lote))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.calculados").value(1))
                .andExpect(jsonPath("$.itens[1].status").value("REJEITADO"))
                .andExpect(jsonPath("$.itens[1].erro.codigo").value("ENTRADA_INVALIDA"));
    }

    @Test
    void consultaDeTaxaRespeitaVigencia() throws Exception {
        mvc.perform(get("/v1/taxas/CDC").param("data", "2026-11-24"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.taxaMensal").value(1.80));
        mvc.perform(get("/v1/taxas/CDC").param("data", "2026-03-01"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.taxaMensal").value(1.95));
        mvc.perform(get("/v1/taxas/XYZ").param("data", "2026-11-24"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.codigo").value("01"));
    }

    @Test
    void healthEstaNoAr() throws Exception {
        mvc.perform(get("/actuator/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"));
    }

    @Test
    void openApiEstaPublicado() throws Exception {
        mvc.perform(get("/v3/api-docs"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.paths['/v1/encargos/calcular']").exists());
    }
}
