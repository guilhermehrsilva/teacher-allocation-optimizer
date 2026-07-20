# Avisos de terceiros

## Escopo

Este documento registra as dependências diretas observadas na vBeta 1.0. O pacote final deve incluir os textos integrais das licenças aplicáveis e um inventário das dependências transitivas.

As versões efetivas de frontend são as registradas no package-lock.json. As dependências Python diretas estão fixadas em requirements.txt.

## Runtime Python

| Componente | Versão contratada/observada | Licença |
|---|---|---|
| openpyxl | 3.1.5 | MIT |
| Google OR-Tools | 9.15.6755 | Apache License 2.0 |
| FastAPI | 0.136.1 | MIT |
| HTTPX | 0.28.1 | BSD 3-Clause |
| Uvicorn | 0.46.0 | BSD 3-Clause |
| python-multipart | 0.0.27 | Apache License 2.0 |

OR-Tools traz dependências transitivas como absl-py, immutabledict, numpy, pandas, protobuf e typing-extensions. FastAPI e Uvicorn também possuem dependências transitivas. Todas devem constar no SBOM e na pasta de licenças da distribuição.

## Frontend e build

| Componente | Versão observada no lock | Licença |
|---|---:|---|
| React | 19.2.7 | MIT |
| React DOM | 19.2.7 | MIT |
| Vite | 7.3.6 | MIT |
| TypeScript | 5.9.3 | Apache License 2.0 |
| @vitejs/plugin-react | 4.7.0 | MIT |
| @types/react | 19.2.17 | MIT |
| @types/react-dom | 19.2.3 | MIT |

Vite, TypeScript, plugin e pacotes de tipos são ferramentas de build. Seus avisos ainda devem ser preservados no material de desenvolvimento e no SBOM de build.

## Plataforma

Se uma distribuição Python for incluída no pacote, inclua a Python Software Foundation License e os avisos do runtime.

SQLite é fornecido pelo runtime Python. Seus avisos devem ser confirmados conforme a distribuição escolhida.

## Fonte Ubuntu

O CSS declara Ubuntu, mas os arquivos da fonte não foram observados no pacote revisado. O Windows usa Segoe UI como fallback.

Se a fonte Ubuntu for incorporada, inclua a Ubuntu Font Licence e confirme que a forma de distribuição respeita seus termos.

## Navegadores

Edge e Chrome são clientes externos esperados e não são redistribuídos com a aplicação.

## Licença do produto

A licença da Ferramenta de Alocação Docente não foi definida nos arquivos revisados. Antes da distribuição, o responsável deve escolher e registrar:

- uso interno/proprietário; ou
- licença de código aplicável.

Não presuma que a licença de uma dependência define a licença do produto.

## Processo de release

Antes de publicar:

1. criar ambiente limpo;
2. instalar exatamente as dependências do lock;
3. gerar SBOM em formato legível por máquina;
4. gerar relatório de licenças;
5. revisar licenças desconhecidas ou copyleft;
6. copiar textos obrigatórios para licenses;
7. registrar versão e hash do inventário;
8. anexar este aviso ao pacote.

Este documento é um inventário técnico e não constitui parecer jurídico.
