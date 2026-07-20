# Notas da versão

## Ferramenta de Alocação Docente 1.0.0

Status: release técnica para produção local mono-usuário em Windows.

Esta versão consolida o motor oficial, a experiência web e o ambiente isolado de simulação.

## Destaques

### Processamento

- seleção explícita de módulo;
- validação antes da otimização;
- pendências em XLSX;
- detalhes de validação em linguagem acionável;
- confirmação de ressalvas;
- estados e mensagens de execução;
- tabela pesquisável de decisões;
- downloads dos artefatos.

### Dashboard

- filtros na ordem ORDEM, DIA, HORÁRIO, CLUSTER e CURSO;
- seleção múltipla com OU interno e E entre dimensões;
- capacidade baseada em CH_LETIVA utilizável em transmissões completas;
- CH ímpar arredondada para baixo, como 9h para 8h;
- deltas por primeira e segunda metade;
- agenda por dia;
- todos os clusters, sem agrupamento em Outros;
- diagnóstico de não alocadas;
- cobertura por etapa.

### Insights

- KPI de alocações com candidato único;
- cobertura de todos os cursos;
- identificação de dias das lacunas;
- horários críticos com cursos e perfis relacionados;
- fila de recuperação por disciplina;
- oportunidades de cobertura, escassez, capacidade e exposição externa;
- metodologia e limitações visíveis.

### Cenários

- motor secundário separado do solver principal;
- baseline obrigatoriamente principal e concluída;
- alterações de capacidade, agenda e perfil;
- busca digitável de ofertas e docentes;
- alocação flexível por cluster;
- proteção de prioridades;
- fixação de decisões;
- comparação baseline versus cenário;
- promoção condicionada a guardrails;
- resultado oficial por módulo.

### Governança

- reset do último item ou de todos;
- reset disponível nas abas de análise;
- exclusão em cascata de cenários dependentes;
- bloqueio de reset durante execução;
- manifesto, hashes e auditoria.

### Experiência

- estados de carregamento consistentes;
- badges de status e contexto;
- textos orientados à ação;
- foco visível, skip link e movimento reduzido;
- layout responsivo;
- frontend compilado servido pela própria API.

## Compatibilidade

- entrada XLSX com MAPA PEDAGÓGICO e DOCENTES;
- módulos 51 a 54;
- execução local em Windows;
- Edge e Chrome como navegadores alvo;
- schema de saída 2 nos motores atuais.

## Limitações conhecidas

- sem autenticação; uso somente em localhost;
- sem valores financeiros reais de RPA/NF;
- sem fonte de Planejado versus Realizado;
- frontend ainda sem suíte automatizada dedicada;
- dependências Python estão travadas com hashes e possuem SBOM transitivo; o pacote não inclui wheelhouse e a instalação inicial requer acesso ao índice configurado do pip;
- SQLite mantém referências de arquivo e requer backup conjunto;
- Ubuntu não é distribuída no pacote atual;
- o release é um ZIP com checksum SHA-256, sem MSI nem assinatura digital;

## Dados de demonstração

Somente exemplos/BASE_DEMONSTRACAO_ANONIMIZADA_M52.xlsx pode acompanhar esta versão. Resultados anteriores com nomes, chapas ou caminhos locais não pertencem ao pacote. Dados reais são gravados em %LOCALAPPDATA%\UniCesumar\AlocacaoDocente\vbeta1.0.

## Gates técnicos desta release

Executados em 16/07/2026:

- testes Python aprovados;
- build frontend aprovado;
- E2E principal e de cenário aprovado;
- backup e restauração íntegros;
- documentação revisada;
- base de demonstração aprovada;
- checksum gerado;
- MANIFESTO_RELEASE.json verificado por scripts/integridade_release.py;
- limitações comunicadas.

Continuam como aprovações externas: validação acadêmica das regras, teste em outra máquina Windows limpa, revisão humana completa de acessibilidade/navegadores e assinatura digital quando exigida pela política corporativa.

## Próximas evoluções candidatas

- autenticação e operação multiusuário;
- trilha de auditoria por usuário;
- valores financeiros de capacidade externa;
- ingestão de realizado;
- testes E2E e acessibilidade automatizados;
- migração versionada do SQLite;
- instalador e atualização assistida;
- políticas adicionais de cenário após validação de negócio.
