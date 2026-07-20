# Evidências de QA da versão 1.0

Este diretório mantém o recibo técnico da release `1.0.0`. Dados operacionais,
bancos SQLite e resultados completos não são distribuídos; os recibos detalhados
permanecem no diretório de homologação ignorado pelo Git.

## Verificação final de 16/07/2026

Ambiente usado: Windows, Python `3.13.12` estável de 64 bits, Node.js `22.23.1`,
npm `10.9.8`, OpenPyXL `3.1.5`, OR-Tools `9.15.6755`, FastAPI `0.136.1`,
HTTPX `0.28.1`, Uvicorn `0.46.0` e Vite `7.3.6`.

| Verificação | Resultado |
|---|---:|
| Backend | 22/22 testes aprovados |
| Motor principal | 68/68 testes aprovados |
| Motor de cenários | 75/75 testes aprovados |
| Release, backup e restauração | 16/16 testes aprovados |
| Total Python | 181/181 testes aprovados |
| TypeScript e build Vite | Aprovados |
| Auditoria npm | 0 vulnerabilidades |
| `pip check` | Nenhuma dependência quebrada |
| Verificação estrutural do launcher | Aprovada |
| Manifesto de release | 128 arquivos com SHA-256 válido |
| ZIP determinístico e `.sha256` | Gerados em `release/` |

Comandos reproduzíveis:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\testar.ps1
Set-Location .\frontend
npm ci
npm run build
npm audit --audit-level=moderate
Set-Location ..
python .\scripts\integridade_release.py --verificar
python .\scripts\empacotar_release.py
```

## Rodada demonstrativa de referência

A homologação final usou
`exemplos/BASE_DEMONSTRACAO_ANONIMIZADA_M52.xlsx`, cujo SHA-256 é
`7af0267a486ff6b8ea8de510c108faf788658bb21d2c35c7d2e7f7a807b59e9b`.

| Métrica | Resultado |
|---|---:|
| Estado do job principal | `CONCLUIDA` |
| Solver principal | `OPTIMAL` |
| Auditoria | `APROVADO` |
| Ofertas | 402 |
| Alocadas | 377 |
| Não alocadas | 25 |
| Disciplinas totalmente descobertas | 24 |
| Docentes utilizados | 222 |

Todos os artefatos publicados pelo job foram baixados pela API e reconciliados:
manifesto, status, cópia da fonte, validação, pendências, auditoria, planilha de
alocação e resumo.

## Homologação web e cenários

O E2E de 16/07, executado a partir de um diretório de dados vazio, registrou:

- upload e validação da base anonimizada;
- job principal `CONCLUIDA`, `OPTIMAL` e `APROVADO`;
- Dashboard, Insights, paginação e downloads coerentes;
- cenário com política `FIXAR` executado como `CONCLUIDA` e `OPTIMAL`;
- guardrails elegíveis para promoção;
- cenário promovido para `HOMOLOGADO`;
- cenário registrado como resultado oficial do módulo 52.

O recibo detalhado foi gravado em
`data/homologacao-final-1.0/e2e_receipt.json` e não integra o pacote por conter
identificadores e caminhos do ambiente de execução.

## Backup e restauração

Com a aplicação encerrada, o diretório de homologação foi exportado para um ZIP
verificado com 31 arquivos. A restauração ocorreu em um diretório vazio, atualizou
7 referências internas do SQLite e foi aberta por uma nova instância da API.
Nessa instância foram revalidados o job principal, seus artefatos, o cenário
`HOMOLOGADO` e os guardrails de promoção.

## Limites deste recibo

Este recibo comprova o gate técnico automatizável da release local mono-usuário.
Continuam externos: aprovação acadêmica das regras, teste em outra máquina Windows
limpa, revisão humana completa de acessibilidade e navegadores, e assinatura
digital quando exigida pela política corporativa. A aplicação permanece restrita
a `127.0.0.1` e não deve ser publicada em rede sem autenticação e nova arquitetura
de segurança.
