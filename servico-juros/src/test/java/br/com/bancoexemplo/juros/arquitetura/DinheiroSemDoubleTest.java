package br.com.bancoexemplo.juros.arquitetura;

import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.regex.Pattern;
import java.util.stream.Stream;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Criterio de aceite 5: nenhum double/float no codigo de producao, exceto na
 * PotenciaFracionaria (unico ponto documentado em DECISOES.md, D2).
 */
class DinheiroSemDoubleTest {

    private static final Pattern PONTO_FLUTUANTE = Pattern.compile("\\b(double|float|Double|Float)\\b");
    private static final String EXCECAO_PERMITIDA = "PotenciaFracionaria.java";

    @Test
    void codigoDeProducaoNaoUsaPontoFlutuante() throws IOException {
        try (Stream<Path> arquivos = Files.walk(Path.of("src/main/java"))) {
            List<String> violacoes = arquivos
                    .filter(p -> p.toString().endsWith(".java"))
                    .filter(p -> !p.getFileName().toString().equals(EXCECAO_PERMITIDA))
                    .filter(DinheiroSemDoubleTest::usaPontoFlutuante)
                    .map(Path::toString)
                    .toList();
            assertThat(violacoes).as("arquivos com double/float").isEmpty();
        }
    }

    private static boolean usaPontoFlutuante(Path arquivo) {
        try {
            return Files.readAllLines(arquivo).stream()
                    .map(String::trim)
                    .filter(l -> !l.startsWith("*") && !l.startsWith("//"))
                    .anyMatch(l -> PONTO_FLUTUANTE.matcher(l).find());
        } catch (IOException e) {
            throw new IllegalStateException(e);
        }
    }
}
