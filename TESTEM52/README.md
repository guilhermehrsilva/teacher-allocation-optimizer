# Pipeline do módulo 52

Este diretório executa uma rodada rastreável: copia a fonte, valida o contrato,
resolve com CP-SAT, audita o resultado em memória e somente então publica a alocação.
`MOTOR/` e `VALIDADOR/` são reutilizados sem duplicação de regras.

## Preparação

```powershell
python -m pip install -r TESTEM52/requirements.txt
```

Coloque exatamente um arquivo `.xlsx` em `TESTEM52/entrada`. Arquivos temporários
do Excel iniciados por `~$` são ignorados. Como alternativa, indique a planilha:

```powershell
python TESTEM52/executar_pipeline.py --base C:\caminho\base_m52.xlsx
```

Para continuar a série auditável já existente em `TESTEM52/resultados`, use:

```powershell
python TESTEM52/executar_pipeline.py --base TESTEM52/BASE_SINTETICA_PERFIL_DOCENTE_COMPLETO.xlsx --resultado TESTEM52/resultados
```

Execução por descoberta automática:

```powershell
python TESTEM52/executar_pipeline.py
```

O padrão é CP-SAT puro, módulo esperado `52`, seed `42`, oito workers e exigência
de `OPTIMAL`. Um limite opcional pode ser informado com `--tempo-limite SEGUNDOS`.
Para aceitar uma solução `FEASIBLE` que tenha sido aprovada pela auditoria, use
`--permitir-nao-otimo`.

`MODELO_CONTRATO` da fonte é preservado como histórico em
`MODELO_CONTRATO_ORIGEM`, mas não restringe candidatos. O contrato sugerido no
resultado é calculado pela função do docente escolhido. Essa comparação aparece
na planilha somente na aba `ALOCACOES`; a aba `DOCENTES` não inclui modelo de
contrato. O resumo JSON preserva os mesmos dados para auditoria e integração.

`CH_LETIVA` é uma capacidade semanal. A coluna `ORDEM` define as duas etapas do
módulo: `1ª` consome carga e agenda na primeira metade, `2ª` na segunda e
`ESTENDIDA` nas duas. A aba `DOCENTES` informa quantidade e percentual de uso
em cada etapa e preserva `UTILIZAÇÃO` como a média das duas utilizações. A
classificação usa `ORDEM` como fonte de verdade, inclusive quando houver uma
ressalva de divergência com `METODOLOGIA` na validação.

As quatro fases de negócio usam o paralelismo para provar os ótimos. Em seguida,
o motor fixa esses quatro valores, remove os hints paralelos e executa uma busca
canônica de um worker. Assim, execuções idênticas preservam a mesma alocação sem
abrir mão da velocidade nas fases difíceis. `--workers 1` continua disponível
para diagnóstico totalmente sequencial, e o manifesto registra a escolha.

## Artefatos

Por padrão, cada tentativa cria `resultado/rodada_###` antes da validação. A
série operacional existente usa `resultados/rodada_###` por meio do argumento
`--resultado TESTEM52/resultados`. Nenhuma rodada é apagada em caso de falha. A
pasta contém:

- `status.json`: estado corrente e histórico, sempre substituído atomicamente;
- `manifesto.json`: SHA-256 da cópia e de cada componente do código,
  configuração, versões, fases e artefatos;
- `fonte/`: cópia imutável usada por todas as etapas;
- `validacao/`: relatório JSON e inconsistências CSV;
- `alocacao/`: planilha e resumo produzidos pelo motor;
- `auditoria/auditoria_alocacao.json`: verificação independente da solução.

Somente o status `REPROVADO` bloqueia a validação; `APROVADO_COM_RESSALVAS`
prossegue para o motor.

## Códigos de saída

| Código | Significado |
| ---: | --- |
| 0 | Sucesso auditado |
| 10 | Entrada ou configuração inválida |
| 20 | Validação reprovada ou não concluída |
| 30 | Solver sem solução utilizável ou falha na alocação |
| 31 | Solução auditada, mas sem `OPTIMAL` obrigatório |
| 40 | Auditoria reprovada ou não concluída |
| 50 | Erro interno inesperado |

## Testes

```powershell
python -m unittest discover -s TESTEM52/tests -p test_*.py -v
```
