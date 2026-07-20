# Motor secundário de cenários

Este pacote executa exclusivamente as simulações da aba **Cenários**.

- O processamento principal continua usando `vbeta/executar_pipeline.py`.
- Cenários usa `scenario_engine/executar_cenario.py` em outro processo.
- O código do solver foi derivado do motor principal em 15/07/2026 e é mantido
  como uma cópia independente para que futuras políticas de simulação não
  alterem a alocação oficial.
- Entradas e resultados de cenário ficam fora deste pacote, sob `tela/data/cenarios`.

## Contrato

O motor recebe uma planilha XLSX já materializada com as premissas do cenário,
valida a cópia, executa CP-SAT, audita o resultado e publica os mesmos artefatos
básicos do motor principal. A linhagem da simulação é mantida pelo backend.

O limite confirmado para docentes Stricto/presencial é de duas disciplinas por
módulo (`STRICTO_MAX_DISCIPLINES_PER_MODULE = 2`).

Políticas exclusivas podem ser recebidas por `--politicas`: alocação flexível
dentro do cluster, proteção de cursos/ofertas e fixação de alocações da baseline.
Cada política permanece registrada em `alteracoes.json` e no manifesto da rodada.
