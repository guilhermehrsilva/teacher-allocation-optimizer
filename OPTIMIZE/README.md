# Rodada otimizada

Esta pasta mantém a base, o executor e os resultados da versão otimizada do
motor. O núcleo compartilhado permanece em `MOTOR/src/motor_alocacao` para que
as regras de negócio não sejam duplicadas ou fiquem divergentes.

## Ajustes aplicados

- CP-SAT puro por padrão (`--iteracoes-grasp 0`).
- Solução de cada fase usada como hint da fase lexicográfica seguinte.
- GRASP preservado como opção e com busca local incremental.
- Mesmas restrições de perfil, carga, horário e contrato Stricto.
- Proteção de escassez restrita a disciplinas com um único candidato elegível.
- Coluna `MOTIVO_ALOCACAO` derivada das fases lexicográficas do CP-SAT.
- Quatro objetivos lexicográficos, preservando cobertura, docentes e ocupação.

## Execução

```powershell
python OPTIMIZE/alocar_docentes_otimizado.py
```

Para um benchmark opcional com GRASP:

```powershell
python OPTIMIZE/alocar_docentes_otimizado.py --iteracoes-grasp 20
```

Cada execução cria uma nova subpasta em `OPTIMIZE/resultado`.
