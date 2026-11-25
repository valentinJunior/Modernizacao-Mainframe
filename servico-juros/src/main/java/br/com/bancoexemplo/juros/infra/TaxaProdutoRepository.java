package br.com.bancoexemplo.juros.infra;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDate;
import java.util.List;

public interface TaxaProdutoRepository extends JpaRepository<TaxaProduto, Long> {

    /**
     * Mesmo filtro do UNLOAD do STEP020:
     * DT_INI_VIGENCIA &lt;= data AND DT_FIM_VIGENCIA &gt;= data.
     * Consulta por produto, sem carregar a tabela inteira (risco n. 3).
     */
    @Query("""
            select t from TaxaProduto t
             where t.codigoProduto = :produto
               and t.inicioVigencia <= :data
               and t.fimVigencia >= :data
            """)
    List<TaxaProduto> buscarVigentes(@Param("produto") String produto, @Param("data") LocalDate data);
}
