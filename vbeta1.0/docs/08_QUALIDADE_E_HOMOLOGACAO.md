# Qualidade e homologação

## Objetivo

Uma release só está pronta quando código, regra de negócio, experiência visual, dados de demonstração e pacote Windows foram verificados como conjunto.

## Inventário automatizado

O código revisado possui:

| Camada | Testes definidos |
|---|---:|
| Motor principal | 68 |
| Motor de cenários | 75 |
| Backend | 22 |
| Release, backup e restauração | 16 |
| Frontend | nenhum teste automatizado dedicado |

São **181 testes Python** no total. A contagem não substitui o recibo de
execução: cada release precisa registrar data, ambiente, comando, quantidade
aprovada e falhas.

O recibo técnico mais recente está em [evidências de QA](evidencias/README.md).

## Comandos

Execução consolidada recomendada:

    .\scripts\testar.ps1

O script executa backend, motor principal, motor de cenários, release/backup/restauração, verificação estrutural e, quando presente, MANIFESTO_RELEASE.json.

Motor principal:

    python -m unittest discover -s engines\primary\tests -p "test_*.py" -v

Motor de cenários:

    python -m unittest discover -s engines\scenarios\tests -p "test_*.py" -v

Backend:

    Set-Location backend
    python -m unittest discover -s tests -p "test_*.py" -v

Release, backup e restauração:

    python -m unittest discover -s scripts\tests -p "test_*.py" -v

Frontend:

    Set-Location frontend
    npm ci
    npm run build

## Cobertura esperada dos motores

- contrato e fórmulas proibidas;
- seleção de entrada;
- carga por etapas;
- elegibilidade;
- limite Stricto;
- colisão de agenda;
- objetivos lexicográficos;
- canonicalização;
- GRASP;
- auditoria;
- reporting;
- integridade do manifesto;
- execução por caminho independente do diretório atual;
- políticas exclusivas de cenário.

## Homologação integrada

O teste E2E mínimo deve executar:

1. iniciar a aplicação com diretório de dados vazio;
2. selecionar módulo;
3. enviar base anonimizada;
4. baixar pendências XLSX;
5. confirmar ressalvas, se houver;
6. executar motor principal;
7. esperar conclusão;
8. validar resumo e artefatos;
9. aplicar filtros do Dashboard;
10. verificar todos os cursos e horários em Insights;
11. criar cenário;
12. configurar alteração de docente ou oferta;
13. executar cenário;
14. comparar;
15. homologar cenário elegível;
16. confirmar que ele aparece como oficial nas análises;
17. testar reset do último cenário;
18. testar reset da última rodada em ambiente descartável.

## Evidência de referência

A base de demonstração oficial desta versão é:

    exemplos\BASE_DEMONSTRACAO_ANONIMIZADA_M52.xlsx

O conjunto agregado de homologação associado apresentou:

| Métrica | Resultado |
|---|---:|
| Ofertas | 402 |
| Alocadas | 377 |
| Não alocadas | 25 |
| Docentes utilizados | 222 |
| Solver | OPTIMAL |
| Auditoria | APROVADO |
| Estado final | CONCLUIDA |

A validação teve ressalvas de qualidade da entrada. O resultado de alocação foi PARCIAL, mas matematicamente OPTIMAL.

Esses números servem somente como referência daquele conjunto. Não são meta fixa para outro módulo.

## Verificação de artefatos

Para cada item estável do manifesto:

1. resolver o caminho relativo dentro da rodada;
2. confirmar existência;
3. comparar tamanho;
4. recalcular SHA-256;
5. registrar resultado.

O manifesto também deve ter fonte, versões, configuração, fases e outcome coerentes.

## Integridade do pacote

O manifesto de release não é o mesmo manifesto de uma rodada. Para gerar:

    python scripts\integridade_release.py --gerar

Para verificar:

    python scripts\integridade_release.py --verificar

MANIFESTO_RELEASE.json deve declarar a versão 1.0.0 e validar tamanho e SHA-256 de todos os arquivos distribuíveis. Dados reais permanecem fora do pacote, em LocalAppData, e não integram o manifesto.

## Qualidade de dados

Antes de aprovar a rodada:

- cabeçalhos completos e sem duplicação;
- módulo coerente;
- CHAPA única;
- cargas inteiras não negativas;
- ORDEM suportada;
- agenda válida nas ofertas;
- nenhuma fórmula em campos de dados;
- bloqueios iguais a zero;
- ressalvas compreendidas pelo responsável.

## Matriz visual

Validar pelo menos:

| Cenário | Verificação |
|---|---|
| Desktop 1920×1080 | Leitura para apresentação |
| Notebook 1366×768 | Sem corte de controles |
| Largura 760 px | Reorganização responsiva |
| Largura 320–375 px | Sem overflow destrutivo |
| Zoom 200% | Conteúdo e ações acessíveis |
| Teclado | Ordem de foco e operação completa |
| Movimento reduzido | Transições desativadas |
| Edge e Chrome | Layout e downloads |

Gráficos precisam de texto ou aria-label equivalente. Cores não podem ser a única forma de distinguir estado.

## Casos de falha

- extensão inválida;
- XLSX acima de 50 MB;
- arquivo corrompido;
- planilha ou coluna ausente;
- módulo divergente;
- validação reprovada;
- ressalva sem confirmação;
- porta 8000 ocupada;
- diretório de dados sem permissão;
- reinício no meio da execução;
- ótimo não comprovado;
- auditoria reprovada;
- baseline excluída;
- cenário sem política válida;
- reset durante job;
- caminho com espaço e acento;
- artefato ausente ou hash divergente.

## Homologação Windows

O candidato deve ser testado em máquina limpa, sem depender do repositório original, Node global ou pacotes Python globais.

Validar:

- primeira inicialização;
- diretório de dados;
- launcher e encerramento;
- firewall sem exposição externa;
- abertura do navegador;
- execução dos dois motores;
- downloads;
- backup e restauração;
- desinstalação sem excluir dados sem confirmação.

## Gate para diretoria

- [ ] Regras validadas pelo responsável acadêmico.
- [x] Solver principal não alterado por políticas de cenário.
- [x] Todos os testes Python aprovados (181/181 em 16/07/2026).
- [x] Build frontend aprovado com Node.js 22.23.1 e Vite 7.3.6.
- [x] E2E local principal e de cenário aprovado em 16/07/2026.
- [x] Base de demonstração anonimizada.
- [x] Nome da base confirmado como BASE_DEMONSTRACAO_ANONIMIZADA_M52.xlsx.
- [x] MANIFESTO_RELEASE.json aprovado por integridade_release.py.
- [x] Manifesto e hashes válidos.
- [ ] Interface revisada em resolução de apresentação.
- [x] Limitações conhecidas explicadas.
- [x] Backup e restauração da homologação comprovados.
- [x] Licenças e avisos presentes.
- [x] Versão 1.0.0 e checksum SHA-256 do pacote registrados em `release/`.
