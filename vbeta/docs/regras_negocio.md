# Regras de negócio

## Carga semanal por etapa

Cada transmissão representa 2 horas semanais. O módulo possui duas etapas de cinco semanas:

| `ORDEM` | Primeira etapa | Segunda etapa |
|---|---:|---:|
| `1ª` | 2 h | 0 h |
| `2ª` | 0 h | 2 h |
| `ESTENDIDA` | 2 h | 2 h |

A capacidade letiva e os choques de horário são verificados separadamente nas duas etapas. Por isso, uma disciplina de `1ª` e uma de `2ª` podem reutilizar a mesma capacidade e o mesmo horário; uma `ESTENDIDA` ocupa ambos.

Na aba `DOCENTES`:

- `QTD_DISCIPLINAS_1ª_ETAPA` e `QTD_DISCIPLINAS_2ª_ETAPA` contam as disciplinas presentes em cada etapa;
- `UTILIZAÇÃO_1ª_ETAPA` e `UTILIZAÇÃO_2ª_ETAPA` dividem a carga da etapa por `CH_LETIVA`;
- `UTILIZAÇÃO` geral é a média simples dos percentuais das duas etapas;
- `CH_ALOCADA` representa a carga semanal média no módulo;
- `QTD_TRANSMISSÕES` preserva a quantidade de disciplinas efetivamente alocadas.

## Elegibilidade

Um docente é candidato quando, simultaneamente:

- está ativo;
- possui ao menos um perfil compatível com a disciplina;
- tem capacidade disponível em todas as etapas ocupadas;
- não possui choque no mesmo dia, horário e etapa.

Perfis separados por vírgula são alternativas: uma interseção exata após normalização é suficiente.

Docentes Stricto (`PROFESSOR DE ENSINO SUPERIOR PRESENCIAL`) usam a regra especial de no máximo duas disciplinas no módulo, mesmo quando `CH_LETIVA` está zerada na base.

## Otimização e auditoria

O motor usa CP-SAT em fases lexicográficas para priorizar cobertura e, sem perder o ótimo anterior, melhorar distribuição, aproveitamento de capacidade e atendimento de ofertas escassas. O GRASP pode gerar uma solução inicial, enquanto o CP-SAT permanece responsável pela prova e canonicalização final.

Antes da publicação, uma auditoria independente recalcula compatibilidade, capacidade por etapa, choques, cargas, limite Stricto, status e explicações. Uma solução reprovada não é publicada como concluída.

## Modelo de contrato publicado

O contrato da saída deriva exclusivamente de `NM_FUNCAO` do docente alocado:

| Função do docente | `MODELO_CONTRATO` |
|---|---|
| `PROFESSOR DE ENSINO SUPERIOR EAD` | `CLT EAD` |
| `PROFESSOR REGENTE` | `CLT EAD` |
| `PROFESSOR DE ENSINO SUPERIOR PRESENCIAL` | `CLT STRICTO` |
| Disciplina não alocada | `A DEFINIR` |

Nenhum valor anterior de contrato é comparado ou exposto na saída da vbeta.
