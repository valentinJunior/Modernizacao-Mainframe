package br.com.bancoexemplo.juros.aplicacao;

import br.com.bancoexemplo.juros.dominio.CalculadoraEncargos;
import br.com.bancoexemplo.juros.dominio.CodigoRejeicao;
import br.com.bancoexemplo.juros.dominio.DataLegado;
import br.com.bancoexemplo.juros.dominio.EntradaCalculo;
import br.com.bancoexemplo.juros.dominio.RejeicaoException;
import br.com.bancoexemplo.juros.dominio.ResultadoCalculo;
import br.com.bancoexemplo.juros.dominio.TabelaSpread;
import br.com.bancoexemplo.juros.infra.SpreadRating;
import br.com.bancoexemplo.juros.infra.SpreadRatingRepository;
import br.com.bancoexemplo.juros.infra.TaxaProduto;
import br.com.bancoexemplo.juros.infra.TaxaProdutoRepository;
import io.micrometer.core.instrument.MeterRegistry;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Papel do programa JURB0100 para um contrato: localizar a taxa vigente do
 * produto, montar a area JURCCALC e chamar a calculadora (o antigo CALL JURS0100).
 */
@Service
@Transactional(readOnly = true)
public class CalculoEncargosService {

    private static final Logger LOG = LoggerFactory.getLogger(CalculoEncargosService.class);
    /** Inteiros que cabem em S9(13)V99, o saldo da area JURCCALC. */
    private static final int DIGITOS_INTEIROS_LEGADO = 13;
    /** Decimal simples; o grupo 1 sao os inteiros sem zeros a esquerda. */
    private static final Pattern SALDO_DECIMAL = Pattern.compile("-?0*(\\d{1,18})(\\.\\d{1,9})?");

    private final TaxaProdutoRepository taxas;
    private final SpreadRatingRepository spreads;
    private final MeterRegistry metricas;

    public CalculoEncargosService(TaxaProdutoRepository taxas, SpreadRatingRepository spreads,
                                  MeterRegistry metricas) {
        this.taxas = taxas;
        this.spreads = spreads;
        this.metricas = metricas;
    }

    public ResultadoCalculo calcular(SolicitacaoCalculo solicitacao) {
        return calcular(solicitacao, new HashMap<>());
    }

    /**
     * Lote: um contrato rejeitado nao interrompe os demais, como no batch.
     * A tabela de spread e lida uma vez por data de referencia.
     */
    public List<ItemLote> calcularLote(List<SolicitacaoCalculo> solicitacoes) {
        Map<LocalDate, TabelaSpread> cacheSpread = new HashMap<>();
        return solicitacoes.stream().map(s -> {
            try {
                return ItemLote.calculado(calcular(s, cacheSpread));
            } catch (RejeicaoException e) {
                return ItemLote.rejeitado(s.numeroContrato(), e.codigo());
            }
        }).toList();
    }

    /** Equivalente ao UNLOAD do STEP020 para um produto. */
    public Optional<TaxaProduto> buscarTaxaVigente(String produto, LocalDate data) {
        List<TaxaProduto> vigentes = taxas.buscarVigentes(produto, data);
        if (vigentes.size() > 1) {
            // No legado, o JURB0100 aborta com RC 16 ao achar produto duplicado na tabela.
            throw new IllegalStateException("Mais de uma taxa vigente para o produto " + produto + " em " + data);
        }
        return vigentes.stream().findFirst();
    }

    private ResultadoCalculo calcular(SolicitacaoCalculo s, Map<LocalDate, TabelaSpread> cacheSpread) {
        String contrato = s.numeroContrato();
        try {
            // Borda da API (DIVERGENCIAS.md, V1): o dominio trunca como o MOVE do COBOL,
            // mas uma interface nova nao deve aceitar um valor que seria corrompido.
            if (saldoExcedeCapacidade(s.saldoDevedor())) {
                throw new RejeicaoException(CodigoRejeicao.SALDO_ACIMA_DA_CAPACIDADE, contrato);
            }

            // A data de referencia define a vigencia da taxa e do spread (risco n. 2):
            // sem ela valida nao ha como buscar a taxa, entao o 33 vem antes do 01.
            LocalDate referencia = DataLegado.converter(s.dataReferencia())
                    .orElseThrow(() -> new RejeicaoException(CodigoRejeicao.DATA_REFERENCIA_INVALIDA, contrato));

            TaxaProduto taxa = buscarTaxaVigente(s.codigoProduto(), referencia)
                    .orElseThrow(() -> new RejeicaoException(CodigoRejeicao.PRODUTO_SEM_TAXA, contrato));

            TabelaSpread tabela = cacheSpread.computeIfAbsent(referencia, this::carregarSpreads);

            EntradaCalculo entrada = new EntradaCalculo(contrato, s.rating(), s.saldoDevedor(),
                    taxa.getTaxaMensal(), taxa.getMoraMensal(), taxa.getMulta(),
                    s.dataUltimaApuracao(), s.dataVencimento(), s.dataReferencia());

            ResultadoCalculo resultado = CalculadoraEncargos.calcular(entrada, tabela);
            metricas.counter("juros.calculos").increment();
            LOG.info("contrato={} retorno=00", contrato);
            return resultado;
        } catch (RejeicaoException e) {
            metricas.counter("juros.rejeicoes", "codigo", e.codigo().codigo()).increment();
            LOG.info("contrato={} retorno={}", contrato, e.codigo().codigo());
            throw e;
        }
    }

    /**
     * Verdadeiro quando o saldo e um decimal valido com mais de 13 digitos inteiros
     * significativos. Texto fora do formato segue para o dominio, que devolve o 21.
     */
    static boolean saldoExcedeCapacidade(String saldo) {
        if (saldo == null || saldo.length() > 64) {
            return false;
        }
        Matcher m = SALDO_DECIMAL.matcher(saldo.trim());
        return m.matches() && m.group(1).length() > DIGITOS_INTEIROS_LEGADO;
    }

    private TabelaSpread carregarSpreads(LocalDate data) {
        Map<String, BigDecimal> porRating = new HashMap<>();
        for (SpreadRating s : spreads.buscarVigentes(data)) {
            porRating.put(s.getRating().trim(), s.getSpreadMensal());
        }
        return rating -> Optional.ofNullable(porRating.get(rating));
    }
}
