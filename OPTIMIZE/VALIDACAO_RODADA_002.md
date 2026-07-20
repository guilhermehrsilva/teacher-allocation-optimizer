# Validação da rodada 002

## Mudanças avaliadas

- `MOTIVO_ALOCACAO` incluído na aba `ALOCACOES`.
- Justificativas derivadas das soluções intermediárias do CP-SAT.
- Proteção de escassez limitada a disciplinas com exatamente um candidato.
- Disciplinas com dois ou mais candidatos não recebem peso de escassez.

## Resultado

- Status CP-SAT: `OPTIMAL`.
- Transmissões: 402.
- Alocadas: 363.
- Não alocadas: 39.
- Docentes utilizados: 196.
- Score de ocupação por CH: 3256.
- Casos pendentes com candidato único: 5.
- Tempo total: 1,595 s.
- Tempo CP-SAT: 1,353 s.

## Distribuição das justificativas

| Justificativa | Quantidade |
| --- | ---: |
| Priorizado pela maior CH letiva | 186 |
| Alternativas igualmente ótimas | 141 |
| Único docente elegível | 21 |
| Regra Stricto | 11 |
| Ampliação da cobertura de docentes | 4 |

Todas as 363 alocações possuem justificativa. As 39 pendências mantêm
`MOTIVO_ALOCACAO` vazio e continuam explicadas pela coluna `MOTIVO`.

## Efeito da nova regra de escassez

A rodada 001 e a rodada 002 mantiveram os mesmos três objetivos anteriores:
363 alocações, 196 docentes utilizados e score de CH igual a 3256. Em ambas,
cinco disciplinas com candidato único permaneceram pendentes. Isso demonstra
que esses cinco casos não podem ser resgatados sem sacrificar um objetivo que
tem prioridade anterior.

Pendências por quantidade de candidatos:

| Candidatos | Rodada 001 | Rodada 002 |
| ---: | ---: | ---: |
| 0 | 12 | 12 |
| 1 | 5 | 5 |
| 2 | 6 | 9 |
| 3 | 3 | 3 |
| 4 | 8 | 9 |
| 5 | 4 | 1 |
| 8 | 1 | 0 |

O aumento de pendências com dois candidatos é esperado: elas deixaram de ser
artificialmente favorecidas. A cobertura total não foi reduzida.

## Cinco casos insubstituíveis ainda pendentes

- `BEM-ESTAR EM ANIMAIS DE PRODUÇÃO`: choque de horário.
- `GEOLOGIA E PALEONTOLOGIA`: capacidade letiva esgotada.
- `BOAS PRÁTICAS DE GOVERNANÇA DE TI`: choque de horário.
- `IMERSÃO PROFISSIONAL: PROJETO DE BOAS PRÁTICAS EM GOVERNANÇA DE TI`:
  choque de horário.
- `GO - PROJETO DE VIDA`: choque de horário.

## Auditoria

- Nenhuma violação de perfil.
- Nenhum excesso de capacidade.
- Nenhum choque de horário nas alocações.
- Docentes presenciais com no máximo uma disciplina.
- 17 testes automatizados aprovados.
