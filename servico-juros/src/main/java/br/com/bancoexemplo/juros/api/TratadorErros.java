package br.com.bancoexemplo.juros.api;

import br.com.bancoexemplo.juros.dominio.RejeicaoException;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.stream.Collectors;

@RestControllerAdvice
public class TratadorErros {

    /** Contrato rejeitado: codigo e HTTP do legado (secao 6 do spec). */
    @ExceptionHandler(RejeicaoException.class)
    public ResponseEntity<ErroResponse> rejeicao(RejeicaoException e) {
        return ResponseEntity.status(e.codigo().statusHttp())
                .body(ErroResponse.de(e.codigo(), e.numeroContrato()));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErroResponse> validacao(MethodArgumentNotValidException e) {
        String campos = e.getBindingResult().getFieldErrors().stream()
                .map(f -> f.getField() + " " + f.getDefaultMessage())
                .collect(Collectors.joining("; "));
        return ResponseEntity.badRequest()
                .body(new ErroResponse(ErroResponse.ENTRADA_INVALIDA, campos, null));
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<ErroResponse> jsonInvalido(HttpMessageNotReadableException e) {
        return ResponseEntity.badRequest()
                .body(new ErroResponse(ErroResponse.ENTRADA_INVALIDA, "JSON invalido ou mal formado", null));
    }
}
