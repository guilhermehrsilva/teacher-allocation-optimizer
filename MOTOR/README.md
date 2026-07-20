# Motor de alocação docente

Primeiro modelo combinatório para alocação das transmissões EAD ao vivo. O
problema foi modelado no Google OR-Tools CP-SAT como uma atribuição com tamanho
de tarefas e restrições de escala, com uma camada GRASP multi-start opcional.

O CP-SAT resolve e prova os ótimos lexicográficos. O GRASP permanece disponível
como warm start opcional para instâncias futuras maiores, com busca local
incremental, mas fica desligado por padrão porque o CP-SAT puro é mais eficiente
nas bases atuais. Cada fase CP-SAT recebe como hint a solução da fase anterior.
Depois de fixar os quatro objetivos, uma busca canônica de um worker e sem hints
seleciona de forma repetível uma das soluções igualmente ótimas.

## Regras implementadas

- Apenas linhas `Curso único` e `Curso Responsável`, com `FORMATO_AULA = AO VIVO`,
  são transmissões que precisam de docente.
- Linhas `Sinérgica` acompanham outra transmissão e não consomem carga adicional.
- Cada transmissão consome 2 horas semanais da `CH_LETIVA` em cada etapa em
  que ocorre: `1ª` somente na primeira, `2ª` somente na segunda e `ESTENDIDA`
  nas duas etapas.
- O docente deve estar `ATIVO` e possuir pelo menos um dos perfis da disciplina.
- Um docente não pode receber duas transmissões no mesmo
  `DIA_AULA + HORÁRIO` quando elas coexistem na mesma etapa. Assim, uma `1ª` e
  uma `2ª` podem reutilizar a mesma faixa; uma `ESTENDIDA` ocupa ambas.
- A soma das horas semanais de cada etapa não pode superar a `CH_LETIVA`.
- `MODELO_CONTRATO` da disciplina é um dado histórico para comparação e não
  restringe os docentes candidatos.
- O modelo sugerido é definido pela função do docente escolhido: professores
  EAD/regentes sugerem `CLT EAD` e professores presenciais sugerem `CLT STRICTO`.
- Cada docente presencial pode receber até duas disciplinas no módulo, mesmo
  com `CH_CONTRATADA = 0` e `CH_LETIVA = 0`; esses valores originais continuam
  zerados na aba `DOCENTES` do resultado.
- O objetivo primário minimiza transmissões não alocadas.
- O primeiro `SWITCH` mantém essa cobertura e maximiza docentes ativos com pelo
  menos uma alocação.
- O segundo `SWITCH` mantém os dois ótimos anteriores e favorece atribuições aos
  docentes com maior `CH_LETIVA`, reduzindo a ociosidade dos maiores contratos.
- O terceiro `SWITCH` preserva os ótimos anteriores e protege exclusivamente
  transmissões com um único docente elegível.

Quando uma transmissão elegível permanece sem docente, o motivo é detalhado em
`CAPACIDADE_LETIVA_ESGOTADA`, `CHOQUE_DE_HORARIO` ou
`CAPACIDADE_E_HORARIO_COMBINADOS`.

Perfis separados por vírgula são tratados como alternativas, conforme o contrato
inicial do validador.

Neste primeiro ciclo, `19:00` e `20:40` são faixas distintas. As 2 horas letivas
representam consumo de carga, não duas horas-relógio a partir do horário inicial.
Essa premissa deve ser alterada para intervalos sobrepostos caso a operação trate
as duas faixas como conflitantes.

## Execução

```powershell
pip install -r MOTOR/requirements.txt
python MOTOR/alocar_docentes.py BASES_TESTE/BASE_SINTETICA_PERFIL_DOCENTE.xlsx --saida MOTOR/resultado
```

Por padrão não há limite de tempo no CP-SAT. Um limite somente é aplicado quando
`--tempo-limite SEGUNDOS` é informado. A intensidade do GRASP pode ser controlada
com `--iteracoes-grasp` e `--alpha-grasp`; os padrões são 0 (desligado) e 0,25.

Cada execução cria automaticamente uma subpasta sequencial, como
`MOTOR/resultado/rodada_002`. O motor gera `resultado_alocacao.xlsx`, com resumo,
alocações e a aba `DOCENTES`, e `resumo_alocacao.json`, destinado à futura
integração com a aplicação.

A aba `ALOCACOES` usa `MOTIVO` para explicar pendências e
`MOTIVO_ALOCACAO` para justificar escolhas realizadas nas fases do modelo.
`MODELO_CONTRATO_ORIGEM` preserva o histórico da disciplina, enquanto
`MODELO_CONTRATO` apresenta a sugestão calculada pela função do docente alocado.
O resumo JSON replica os dois valores em cada decisão e agrega a comparação
origem → sugestão em `contract_model_comparison`.
O indicador legado `allocated_hours` continua sendo duas horas por transmissão
distinta. Para a visão semanal, o JSON expõe `allocated_stage_hours` e
`average_weekly_allocated_hours`, também apresentados na aba `RESUMO`.
As justificativas usam categorias textuais estáveis; a quantidade numérica de
alternativas fica separada em `CANDIDATOS_ELEGÍVEIS`. O JSON também registra
cada decisão individualmente, além dos agregados, para permitir auditoria e
integração sem depender da leitura da planilha.

A aba `DOCENTES` mantém todos os registros originais, inclusive inativos, e
acrescenta carga alocada, saldo, utilização e situação. Ela não apresenta
modelo de contrato; essa comparação fica exclusivamente na aba `ALOCACOES`.
Também apresenta `QTD_DISCIPLINAS_1ª_ETAPA`, `UTILIZAÇÃO_1ª_ETAPA`,
`QTD_DISCIPLINAS_2ª_ETAPA` e `UTILIZAÇÃO_2ª_ETAPA`. Disciplinas
`ESTENDIDA` entram nas duas contagens. A coluna geral `UTILIZAÇÃO` é a média
das utilizações das duas etapas; `CH_ALOCADA` e `CH_DISPONÍVEL` seguem a mesma
carga semanal média ponderada pelas dez semanas do módulo.
Como a base Stricto preserva `CH_LETIVA = 0` e aplica um limite especial de duas
disciplinas, seus três percentuais permanecem em 0%, `CH_DISPONÍVEL` permanece
zero e `CH_ALOCADA` conserva a carga bruta atribuída.

`ORDEM` é a fonte de verdade para essa classificação temporal. O motor rejeita
valores diferentes de `1ª`, `2ª` e `ESTENDIDA`, mesmo que a coluna
`METODOLOGIA` contenha outra descrição.

Na aba `ALOCACOES`, o modelo de contrato calculado segue:

- professor EAD ou professor regente alocado: `CLT EAD`;
- professor presencial alocado: `CLT STRICTO`;
- docente sem alocação: `A DEFINIR`.

## Próximas regras candidatas

- Preferências de gestor, curso ou cluster.
- Indisponibilidades individuais além dos choques criados pela própria solução.
- Relação explícita entre cada curso sinérgico e sua transmissão responsável.
- Histórico de carga já comprometida antes deste processo.

## Referências técnicas

- [Assignment with Task Sizes](https://developers.google.com/optimization/assignment/assignment_cp)
- [Employee Scheduling](https://developers.google.com/optimization/scheduling/employee_scheduling)
- [CP-SAT Solver](https://developers.google.com/optimization/cp/cp_solver)
- [Greedy randomized adaptive search procedures](https://optimization-online.org/2001/09/371/)
