# API e dados

## Convenções

- Base local: http://127.0.0.1:8000
- Formato padrão: JSON
- Upload: multipart/form-data
- Downloads: XLSX, JSON ou artefato registrado
- Documentação interativa em desenvolvimento: /docs
- Erros usam o campo detail

Não há autenticação na vBeta 1.0. A API não deve ser exposta em rede.

## Endpoints de operação

| Método | Rota | Finalidade |
|---|---|---|
| GET | /api/health | Verificar API, motores e diretório de dados |
| POST | /api/uploads | Enviar e validar XLSX |
| GET | /api/uploads/{upload_id}/validation.xlsx | Baixar pendências de validação |
| POST | /api/jobs | Criar rodada principal |
| GET | /api/jobs | Listar rodadas principais |
| GET | /api/analysis-jobs | Listar resultados concluídos analisáveis |
| DELETE | /api/jobs/primary?scope=latest ou all | Excluir rodada-base |
| GET | /api/jobs/{job_id} | Consultar estado da execução |
| GET | /api/jobs/{job_id}/validation | Consultar validação |
| GET | /api/jobs/{job_id}/summary | Consultar resumo sem decisões detalhadas |
| GET | /api/jobs/{job_id}/allocations | Consultar decisões paginadas |
| GET | /api/jobs/{job_id}/artifacts/{artifact_key} | Baixar artefato |
| GET | /api/dashboard/{job_id} | Gerar Dashboard filtrado |
| GET | /api/insights/{job_id} | Gerar Insights |

## Endpoints de Cenários

| Método | Rota | Finalidade |
|---|---|---|
| POST | /api/scenarios | Criar cenário |
| GET | /api/scenarios | Listar cenários |
| DELETE | /api/scenarios?scope=latest ou all | Excluir cenários |
| GET | /api/scenarios/{scenario_id} | Consultar cenário |
| GET | /api/scenarios/{scenario_id}/catalog | Listar ofertas, docentes, cursos e clusters da baseline |
| POST | /api/scenarios/{scenario_id}/changes | Criar ou substituir alteração de campo |
| DELETE | /api/scenarios/{scenario_id}/changes/{change_id} | Remover alteração |
| POST | /api/scenarios/{scenario_id}/policies | Criar ou substituir política |
| DELETE | /api/scenarios/{scenario_id}/policies/{policy_id} | Remover política |
| POST | /api/scenarios/{scenario_id}/runs | Executar simulação |
| GET | /api/scenarios/{scenario_id}/comparison | Comparar cenário e baseline |
| POST | /api/scenarios/{scenario_id}/promote | Homologar cenário |

## Upload

Campos:

| Campo | Tipo | Regra |
|---|---|---|
| file | XLSX | Obrigatório, até 50 MB |
| module | inteiro | 51 a 54 |

O backend não aceita extensão diferente de XLSX. O arquivo é salvo como fonte.xlsx em diretório próprio.

## Criação de job

Corpo:

    {
      "upload_id": "identificador",
      "confirm_warnings": true,
      "require_optimal": true,
      "time_limit_seconds": null
    }

APROVADO_COM_RESSALVAS exige confirm_warnings. REPROVADO não pode seguir.

## Paginação

/allocations aceita:

- page, mínimo 1;
- page_size, entre 10 e 200;
- status;
- reason;
- search.

A busca percorre currículo, código e nome da disciplina, chapa e nome do docente.

## Filtros do Dashboard

Parâmetros repetíveis:

- order;
- day;
- time;
- cluster;
- course.

Exemplo conceitual:

    /api/dashboard/{job_id}?order=1ª&day=SEGUNDA&cluster=SAÚDE

## Artefatos

artifact_key pode ser:

- manifest;
- status;
- qualquer chave existente em manifesto.artifacts, como source_copy, validation_report, validation_issues, audit_report, allocation_workbook e allocation_summary.

O backend resolve o caminho relativo ao diretório da rodada e bloqueia traversal para fora dele.

## Banco SQLite

### uploads

Registra nome original, arquivo salvo, módulo, status e caminhos da validação.

### jobs

Registra status, mensagem, módulo, exigência de ótimo, limite de tempo, rodada, PID, código de saída, tipo PRIMARY ou SCENARIO e cenário relacionado.

### scenarios

Registra baseline, nome, descrição, status e data de promoção.

### scenario_changes

Mantém uma alteração por cenário, entidade, linha e campo. Valores anterior e novo são serializados em JSON.

### scenario_policies

Mantém uma política por cenário, tipo, alvo e valor.

### scenario_runs

Relaciona cenário, job, planilha materializada e snapshot de alterações.

### official_results

Mantém um resultado oficial por módulo.

## Contrato da entrada

### MAPA PEDAGÓGICO

Campos esperados:

1. CURSO
2. NOME_CURSO
3. CURRÍCULO
4. COD_DISCIPLINA
5. NOME_DISCIPLINA
6. PERFIL_DISCIPLINA
7. MATRIZ
8. MÓD
9. ANO
10. ORDEM
11. VALIDADO
12. METODOLOGIA
13. FORMATO
14. PROVA
15. ENTURMAÇÃO
16. PERFIL
17. CLUSTER
18. COORDENADOR
19. MODELO_CONTRATO
20. SINERGIA
21. DIA_AULA
22. HORÁRIO
23. FORMATO_AULA

### DOCENTES

Campos esperados:

1. NOME
2. CHAPA
3. NM_FUNCAO
4. CH_CONTRATADA
5. CH_LETIVA
6. GESTOR
7. STATUS
8. PERFIL_DISCIPLINA

CHAPA deve ser única. Cargas devem ser inteiros não negativos.

## Saída

A planilha final inclui abas de ALOCACOES e DOCENTES. O resumo JSON contém métricas e decisões usadas pela API.

Campos críticos da decisão:

- linha e identificadores da oferta;
- etapa, agenda, cluster e curso;
- status;
- docente e chapa quando alocada;
- contrato calculado;
- quantidade de candidatos;
- motivo da não alocação;
- motivo da alocação.

## Integridade

- fórmulas em campos de dados são bloqueadas pela validação;
- a fonte é copiada antes do processamento;
- hashes são verificados entre fases;
- artefatos possuem tamanho e SHA-256;
- rodadas não são sobrescritas;
- downloads são limitados ao diretório da rodada.

## Evolução de schema

O manifesto possui schema_version. Mudanças incompatíveis devem:

1. incrementar a versão;
2. preservar leitura das rodadas ainda suportadas;
3. atualizar API, frontend, testes e documentação;
4. definir migração do SQLite quando necessário.

