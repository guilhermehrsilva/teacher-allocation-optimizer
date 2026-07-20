# OPTIMAL

O OPTIMAL é uma solução completa para apoio à alocação docente, combinando validação de dados, otimização com CP-SAT, auditoria, publicação de resultados e uma interface web para acompanhamento operacional.

## Visão geral

Este repositório reúne vários módulos do fluxo de alocação, incluindo:

- processamento e preparo de dados;
- validação de regras e inconsistências;
- motores de otimização e simulação de cenários;
- interface web para execução e análise;
- relatórios, evidências e artefatos de homologação.

## Principais capacidades

- Validação automática de planilhas e regras de negócio.
- Otimização combinatória para alocação docente.
- Geração de relatórios, evidências e auditoria.
- Simulação de cenários para análise de políticas.
- Interface web com fluxo de execução e dashboards.

## Estrutura do projeto

```text
pilotdev/
├── MOTOR/             # motor principal de alocação
├── OPTIMIZE/          # fluxo otimizado
├── scenario_engine/   # simulação de cenários
├── tela/              # frontend e backend da aplicação web
├── VALIDADOR/         # validação e checagem de dados
├── vbeta/             # versão experimental do pipeline
├── vbeta1.0/          # pacote local de produção / release
└── BASE_TESTE_AR/     # base de teste e validações
```

## Requisitos

- Python 3.11+ ou 3.12+
- Node.js 20+ para desenvolvimento da interface
- Git

## Início rápido

### 1) Preparação local

```powershell
cd pilotdev/vbeta1.0
python -m pip install -r requirements.txt
```

### 2) Execução da aplicação

Consulte os READMEs específicos de cada módulo para os comandos exatos de execução. A aplicação web e os motores de processamento estão concentrados principalmente em:

- [pilotdev/tela/README.md](pilotdev/tela/README.md)
- [pilotdev/vbeta1.0/README.md](pilotdev/vbeta1.0/README.md)
- [pilotdev/scenario_engine/README.md](pilotdev/scenario_engine/README.md)

## Fluxo de uso

1. Carregue uma planilha com os dados de entrada.
2. Valide regras e resolva inconsistências.
3. Execute o motor de otimização.
4. Analise os resultados, relatórios e auditoria.
5. Simule cenários e compare impactos antes de promover mudanças.

## Documentação

A documentação operacional e técnica está distribuída nos READMEs e subpastas de cada módulo. Recomendamos começar pelos diretórios abaixo:

- [pilotdev/vbeta1.0/README.md](pilotdev/vbeta1.0/README.md)
- [pilotdev/tela/README.md](pilotdev/tela/README.md)
- [pilotdev/scenario_engine/README.md](pilotdev/scenario_engine/README.md)

## Status do projeto

Este repositório representa um projeto de engenharia em evolução, com múltiplos módulos e versões experimentais, sendo mantido para fins de organização, rastreio e compartilhamento do trabalho.

## Licença

A definição de licença deste repositório deve ser ajustada conforme a política institucional ou o contexto de uso do projeto.
