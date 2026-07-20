# Validação da rodada 001

## Resultado oficial

- Status CP-SAT: `OPTIMAL`.
- Transmissões: 402.
- Alocadas: 363.
- Não alocadas: 39.
- Docentes utilizados: 196.
- Tempo total: 1,740 s.
- Tempo GRASP: 0,000 s.
- Tempo CP-SAT: 1,501 s.
- Score de escassez: 373.

## Comparativo de configurações

| Configuração | Tempo total | Tempo GRASP | Resultado |
| --- | ---: | ---: | --- |
| CP-SAT puro | 1,896 s | 0,000 s | 363 / 196 / 373 |
| GRASP 1 | 3,066 s | 0,780 s | 363 / 196 / 373 |
| GRASP 5 | 6,544 s | 4,380 s | 363 / 196 / 373 |
| GRASP 20 | 16,724 s | 14,708 s | 363 / 196 / 373 |
| GRASP 200 anterior | 312,745 s | 310,880 s | 363 / 196 / 373 |

Os três números da coluna Resultado representam, respectivamente, transmissões
alocadas, docentes utilizados e penalidade de escassez. O GRASP não melhorou
nenhum objetivo nesta base.

## Auditoria

- 13 disciplinas Stricto alocadas a 13 docentes presenciais distintos.
- Máximo de uma disciplina por docente presencial.
- Cargas-base dos presenciais preservadas em zero.
- Nenhuma violação de perfil.
- Nenhum excesso de capacidade dos demais docentes.
- Nenhum choque de horário.
- Nenhuma alocação sem docente e nenhuma pendência com docente preenchido.

## Pendências

- 11 sem docente com perfil e carga.
- 19 por choque de horário.
- 4 por capacidade letiva esgotada.
- 4 por capacidade e horário combinados.
- 1 por agenda inválida.

Conclusão: CP-SAT puro é a configuração oficial recomendada para esta
escala. O GRASP permanece disponível apenas para benchmarks de instâncias futuras.
