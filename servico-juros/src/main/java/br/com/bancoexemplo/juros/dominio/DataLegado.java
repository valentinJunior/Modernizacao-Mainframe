package br.com.bancoexemplo.juros.dominio;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.time.format.ResolverStyle;
import java.util.Optional;

/**
 * Conversao de datas AAAA-MM-DD com a mesma rigidez do paragrafo
 * 1110-CONVERTER-DATA-ISO: separadores '-', so digitos e data existente no
 * calendario (FUNCTION TEST-DATE-YYYYMMDD). 2026-02-30 e invalida.
 */
public final class DataLegado {

    private static final DateTimeFormatter ISO_ESTRITO =
            DateTimeFormatter.ofPattern("uuuu-MM-dd").withResolverStyle(ResolverStyle.STRICT);

    private DataLegado() {
    }

    /** @return a data, ou vazio se o texto for nulo, mal formatado ou inexistente. */
    public static Optional<LocalDate> converter(String texto) {
        if (texto == null || !texto.matches("\\d{4}-\\d{2}-\\d{2}")) {
            return Optional.empty();
        }
        try {
            return Optional.of(LocalDate.parse(texto, ISO_ESTRITO));
        } catch (DateTimeParseException e) {
            return Optional.empty();
        }
    }
}
