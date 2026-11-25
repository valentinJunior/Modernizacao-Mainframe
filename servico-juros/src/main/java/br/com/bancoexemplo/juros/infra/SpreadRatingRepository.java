package br.com.bancoexemplo.juros.infra;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDate;
import java.util.List;

public interface SpreadRatingRepository extends JpaRepository<SpreadRating, Long> {

    @Query("""
            select s from SpreadRating s
             where s.inicioVigencia <= :data
               and s.fimVigencia >= :data
            """)
    List<SpreadRating> buscarVigentes(@Param("data") LocalDate data);
}
