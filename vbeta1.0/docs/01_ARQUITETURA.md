# Arquitetura

## Visão geral

A vBeta 1.0 é uma aplicação web local composta por frontend React, API FastAPI, persistência SQLite/arquivos e dois motores Python independentes.

    Navegador
        |
        | HTTP em 127.0.0.1
        v
    FastAPI
        |-----------------------|
        |                       |
        v                       v
    SQLite + arquivos      Processos de solver
                            |             |
                            v             v
                     Motor principal   Motor de cenários
                            |             |
                            |-------------|
                                  |
                                  v
                     Manifesto, auditoria e XLSX

Não há integração obrigatória com serviço externo. O navegador, a API e os motores podem operar no mesmo computador.

## Componentes

| Componente | Responsabilidade |
|---|---|
| frontend | Interface, navegação, filtros, gráficos, polling e downloads |
| backend/app/main.py | Rotas HTTP, validação de requisições e entrega do frontend |
| backend/app/database.py | Estado operacional em SQLite |
| backend/app/services/uploads.py | Recepção da planilha e geração de pendências XLSX |
| backend/app/services/jobs.py | Fila e execução do motor principal, Dashboard e artefatos |
| backend/app/services/insights.py | Diagnósticos derivados da rodada |
| backend/app/services/scenarios.py | Configuração, materialização, execução e comparação de cenários |
| backend/app/services/resets.py | Exclusão controlada de rodadas e cenários |
| engines/primary | Validação, solver oficial, auditoria e publicação |
| engines/scenarios | Cópia isolada adaptada para políticas de simulação |

## Fluxo da rodada principal

1. A API grava o upload em uma pasta identificada por UUID.
2. O validador lê a cópia e produz relatório JSON, ocorrências e planilha XLSX de pendências.
3. Se a base puder avançar, o backend cria um job em fila.
4. Um processo Python separado executa o pipeline principal.
5. O pipeline reserva uma nova rodada, copia a fonte e confere SHA-256.
6. Validação, CP-SAT, auditoria e publicação atualizam o status da rodada.
7. O backend lê os artefatos para Processamento, Dashboard e Insights.

O executor do motor principal processa um job por vez. Reiniciar o servidor marca jobs em fila ou execução como INTERROMPIDA.

## Fluxo do cenário

1. O usuário escolhe uma rodada principal concluída como baseline.
2. Alterações e políticas são registradas no SQLite.
3. O backend materializa uma cópia da planilha de origem com as alterações.
4. Um arquivo de linhagem registra baseline, alterações e políticas.
5. O motor secundário é executado em processo separado.
6. O cenário é validado, otimizado, auditado e publicado em área própria.
7. A API compara as decisões da baseline com as do cenário.
8. Somente cenário elegível pode ser promovido a oficial para o módulo.

O executor de cenários também processa um job por vez. Como as filas principal e de cenários são independentes, a operação deve evitar iniciar cálculos pesados simultâneos em máquinas com poucos recursos.

## Isolamento dos motores

O motor principal é a fonte da alocação oficial. Políticas experimentais não são adicionadas a ele.

O motor de cenários preserva o mesmo domínio, validação, loader, GRASP e reporting, mas possui solver e auditoria próprios para reconhecer políticas simuladas. As diferenças devem permanecer explícitas e cobertas por testes.

Regra de manutenção:

- correções gerais de contrato ou segurança devem ser avaliadas nos dois motores;
- políticas de simulação pertencem apenas ao motor secundário;
- qualquer divergência intencional deve ser registrada nas notas da versão;
- uma mudança em capacidade ou etapas deve ser refletida em solver, auditoria e relatório do respectivo motor.

## Persistência

O SQLite usa modo WAL e chaves estrangeiras. As tabelas são:

| Tabela | Conteúdo |
|---|---|
| uploads | Arquivo recebido, módulo e validação |
| jobs | Execuções principais e de cenário |
| scenarios | Definição e estado do cenário |
| scenario_changes | Mudanças de campo na cópia da base |
| scenario_policies | Restrições adicionais do motor secundário |
| scenario_runs | Relação entre cenário, job e arquivos materializados |
| official_results | Resultado escolhido como oficial por módulo |

Arquivos grandes não são gravados no SQLite. Uploads, logs, resultados, manifestos e planilhas ficam no diretório de dados.

## Estrutura de dados de execução

    data/
    ├── app.sqlite3
    ├── uploads/
    ├── jobs/
    ├── resultados/
    └── cenarios/
        ├── jobs/
        └── resultados/

O diretório deve ser estável e possuir permissão de leitura e escrita. Na distribuição Windows, o padrão é:

    %LOCALAPPDATA%\UniCesumar\AlocacaoDocente\vbeta1.0

ALOCACAO_DATA_DIR pode substituir esse local. Dados reais nunca devem ser gravados dentro dos arquivos versionados do pacote.

## Estados

### Jobs

- QUEUED: aguardando executor;
- RUNNING: processo do motor iniciado;
- CONCLUIDA: pipeline concluído;
- INTERROMPIDA: servidor reiniciado durante a execução;
- estados FALHA_*: falha em etapa identificada;
- OTIMO_NAO_COMPROVADO: solução utilizável sem a prova exigida;
- AUDITORIA_REPROVADA: solução não liberada pela auditoria.

### Cenários

- RASCUNHO: pode receber alterações;
- EXECUTANDO: motor secundário ativo;
- CONCLUIDO: simulação disponível para comparação;
- FALHA: simulação não concluída;
- HOMOLOGADO: cenário promovido a oficial.

## Rastreabilidade

Cada rodada mantém:

- cópia da fonte;
- status e histórico;
- versão do pipeline e do contrato;
- configuração;
- fingerprints do código;
- métricas por fase;
- caminho relativo, tamanho e SHA-256 dos artefatos.

O manifesto é a referência para verificar integridade. Caminhos locais não devem ser usados como prova externa; para compartilhamento, use nomes relativos e hashes.

## Implantação local

O frontend de produção é compilado para arquivos estáticos e servido pela própria API. Node.js é necessário para o build, não para o uso normal.

A API deve escutar apenas em 127.0.0.1. O diretório frontend/dist precisa existir antes da inicialização da versão de apresentação.

MANIFESTO_RELEASE.json é separado dos manifestos de rodada. Ele registra tamanho e SHA-256 dos arquivos distribuíveis da aplicação e é gerado ou verificado por scripts/integridade_release.py.
