# Glossário

**Alocação:** associação entre uma oferta e um docente.

**ALOCADA:** oferta com docente definido.

**Baseline ou rodada-base:** execução concluída do motor principal usada como referência de cenário.

**Candidato elegível:** docente que atende aos requisitos básicos de atividade, função, capacidade mínima, perfil e agenda válida. A alocação final ainda depende das restrições globais.

**Candidato único:** oferta com exatamente um docente elegível.

**Canonicalização:** fase final que escolhe uma solução estável entre alternativas com os mesmos valores ótimos.

**CH:** carga horária.

**CH_CONTRATADA:** carga contratada informada na base.

**CH_LETIVA:** carga semanal disponível para atividade letiva.

**CH utilizável no Dashboard:** CH_LETIVA arredondada para baixo ao múltiplo da duração de uma transmissão.

**Cluster:** agrupamento temático ou de negócio usado para análise e simulação.

**CONCLUIDA:** pipeline finalizado e publicado.

**CP-SAT:** solver de programação por restrições do Google OR-Tools.

**Delta de CH:** demanda da etapa menos capacidade letiva ativa utilizável. Positivo indica déficit bruto.

**ESTENDIDA:** oferta que consome carga na primeira e na segunda etapa.

**FEASIBLE:** o solver encontrou solução, mas não provou que é ótima.

**GRASP:** heurística opcional usada para gerar uma solução inicial para o CP-SAT.

**Guardrail:** condição obrigatória para confiar ou promover um cenário.

**Homologar ou promover:** selecionar o resultado de um cenário como oficial para seu módulo.

**Manifesto:** JSON com versões, configuração, fases, métricas, hashes e artefatos.

**MOTIVO:** explicação da não alocação.

**MOTIVO_ALOCACAO:** explicação da escolha quando houve alocação.

**Motor principal:** solver imutável da rodada oficial.

**Motor de cenários:** solver separado que aceita políticas de simulação.

**NAO_ALOCADA:** oferta sem docente após a otimização.

**Oferta:** linha elegível do mapa pedagógico que representa uma transmissão a alocar.

**OPTIMAL:** prova do CP-SAT de que o melhor valor do objetivo foi alcançado.

**ORDEM:** campo canônico que define 1ª, 2ª ou ESTENDIDA.

**Override de cluster:** flexibilização controlada de perfil exato dentro do cluster, exclusiva de Cenários.

**PARCIAL:** resultado com uma ou mais ofertas não alocadas.

**Perfil:** competência ou área usada para compatibilizar oferta e docente.

**Primeira etapa:** primeiras cinco semanas do módulo.

**RPA/NF:** forma externa de contratação usada apenas como classificação/proxy; a aplicação não calcula custo monetário.

**Rodada:** pasta imutável de uma execução do pipeline.

**Segunda etapa:** últimas cinco semanas do módulo.

**Snapshot:** cópia e registro das entradas e políticas efetivamente processadas.

**Stricto/presencial:** docente com função PROFESSOR DE ENSINO SUPERIOR PRESENCIAL, limitado a duas disciplinas por módulo no solver.

**Transmissão:** unidade de oferta que representa 2 horas semanais.

**WAL:** modo de journal do SQLite que melhora concorrência e recuperação.

