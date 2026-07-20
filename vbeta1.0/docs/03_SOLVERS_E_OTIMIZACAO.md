# Solvers e otimização

## Pipeline comum

Os dois motores executam:

1. seleção e cópia da entrada;
2. validação;
3. carga do problema;
4. otimização;
5. auditoria independente;
6. escrita de resultados;
7. atualização do manifesto e status.

O hash da fonte é conferido antes e depois da cópia e novamente entre fases relevantes. Uma alteração inesperada gera falha de snapshot.

## Modelo matemático principal

Para cada oferta e docente elegível existe uma variável binária de atribuição. Cada oferta possui também uma variável binária de não alocação.

Restrição fundamental:

    soma das atribuições elegíveis + não alocada = 1

O modelo também possui:

- carga total por docente;
- carga por docente e etapa;
- indicador de docente utilizado;
- restrição de capacidade por etapa;
- limite total de duas disciplinas para Stricto;
- no máximo uma oferta por docente, etapa, dia e horário.

## Otimização lexicográfica

O CP-SAT resolve objetivos sequenciais. Após cada fase, o melhor valor é fixado como restrição da fase seguinte.

| Fase | Objetivo |
|---|---|
| 1 | Minimizar ofertas não alocadas |
| 2 | Maximizar docentes ativos utilizados |
| 3 | Maximizar score ponderado por CH_LETIVA |
| 4 | Minimizar não alocadas com candidato único |
| Final | Canonicalizar uma solução com um worker |

A canonicalização remove o objetivo e os hints paralelos, mantendo todos os ótimos fixados. Isso reduz diferenças entre planilhas produzidas a partir da mesma entrada.

## Status PARCIAL e OPTIMAL

São dimensões diferentes:

- PARCIAL indica que pelo menos uma oferta ficou sem alocação;
- OPTIMAL indica que o CP-SAT provou os melhores valores das fases exigidas.

Assim, uma solução PARCIAL e OPTIMAL é válida: há pendências, mas não existe solução com maior cobertura sob as regras atuais.

## Limite de tempo

Não há limite padrão. Quando configurado, o tempo é repartido entre as fases.

Sem a opção de permitir não ótimo, uma solução FEASIBLE não é publicada como resultado oficial concluído. A interface principal solicita prova ótima.

## Paralelismo e determinismo

As fases de busca podem usar vários workers. A fase de canonicalização usa um worker e semente definida.

Paralelismo melhora a busca, mas tempos de execução podem variar conforme CPU, memória e outras tarefas. A prova matemática e os valores objetivos são mais importantes do que comparar somente tempo de parede.

## GRASP

O GRASP é uma heurística opcional para construir uma solução inicial. Quando ativado:

- executa um número configurado de iterações;
- usa alpha e semente registrados;
- oferece hints ao CP-SAT;
- não substitui restrições, prova de ótimo ou auditoria.

Na configuração corrente da aplicação web, a execução padrão não exige GRASP. O CP-SAT permanece responsável pelo resultado final.

## Auditoria independente

A auditoria não confia apenas nos diagnósticos do solver. Ela reconstrói:

- quantidade de decisões;
- compatibilidade de perfis;
- status e função do docente;
- capacidade por etapa;
- limite Stricto;
- choques de horário;
- cargas totais e por etapa;
- contagens de docentes;
- motivos e status;
- valor do objetivo de não alocação.

Resultado reprovado não deve ser homologado.

## Publicação

Uma rodada concluída contém:

    rodada_###/
    ├── fonte/
    ├── validacao/
    ├── auditoria/
    ├── alocacao/
    ├── manifesto.json
    └── status.json

O manifesto usa caminhos relativos para os artefatos e registra tamanho e SHA-256.

## Motor de cenários

O motor secundário começa com as mesmas restrições acadêmicas do principal, mas recebe um snapshot de políticas.

Políticas suportadas pela experiência atual:

- ALOCAR_CLUSTER;
- PRIORIDADE;
- FIXAR.

Mudanças de campos são materializadas na cópia XLSX antes da otimização. Políticas são restrições ou extensões do solver e permanecem no arquivo de linhagem.

### Override de cluster

ALOCAR_CLUSTER amplia o conjunto de candidatos somente no cluster alvo. O par oferta-docente flexibilizado é registrado para que a auditoria do cenário não o confunda com compatibilidade exata.

Capacidade, atividade, função reconhecida, agenda e limite Stricto continuam obrigatórios.

### Prioridade

PRIORIDADE fixa a variável de não alocação em zero para o curso ou oferta. A política não cria capacidade nem elimina choque.

### Fixação

FIXAR obriga uma variável específica de atribuição a valer um. Se o par não existir no conjunto elegível, o cenário é rejeitado.

## Separação obrigatória

O backend chama:

- engines/primary/executar_pipeline.py para rodadas oficiais;
- engines/scenarios/executar_cenario.py para simulações.

O motor de Cenários nunca deve importar o solver principal em tempo de execução nem modificar seus arquivos. Uma promoção altera a referência oficial no banco, não o código do motor principal.

## Parâmetros auditáveis

Devem permanecer no manifesto ou nos diagnósticos:

- versão do pipeline;
- versão do schema de saída;
- versão do contrato de validação;
- módulo;
- quantidade de workers;
- limite de tempo;
- exigência de ótimo;
- semente;
- iterações e alpha do GRASP;
- status de cada fase;
- tempo de CP-SAT e GRASP;
- score de capacidade;
- penalidade de candidato único;
- mapeamento de ORDEM para etapas;
- limite Stricto;
- fingerprints do código.

## Alterações que exigem homologação completa

- duração de uma transmissão;
- interpretação de ORDEM;
- capacidade ou limite Stricto;
- critérios de elegibilidade;
- ordem ou fórmula dos objetivos;
- regra de choque;
- critérios de promoção;
- novos overrides no motor secundário;
- mudança de schema dos artefatos.

Nesses casos, solver, auditoria, reporting, testes e documentação devem ser revisados juntos.

