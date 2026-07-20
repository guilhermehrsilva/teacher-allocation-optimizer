# Ferramenta de Alocação Docente — versão 1.0

Versão de produção local para operação individual em Windows e apresentação executiva. O pacote
reúne validação da planilha, alocação CP-SAT auditável, Dashboard, Insights e um
motor secundário isolado para simulação de cenários.

## Início rápido no Windows

1. Instale Python 3.12 ou 3.13 estável, 64 bits.
2. Execute `scripts\instalar.ps1` uma única vez.
3. Execute `iniciar.ps1`.
4. O navegador abrirá em `http://127.0.0.1:8000`.

O frontend já está compilado. Node.js só é necessário para desenvolvimento da
interface, não para executar a versão de apresentação. Para recompilar, use
Node.js 20.19+ ou 22.12+.

## Fluxo de uso

1. Em **Processamento**, selecione explicitamente o módulo e envie a planilha.
2. Corrija bloqueios ou confirme ressalvas da validação.
3. Execute o motor principal e acompanhe validação, otimização, auditoria e publicação da rodada-base.
4. Consulte **Dashboard** e **Insights** usando somente resultados publicados.
5. Em **Cenários**, crie uma simulação isolada, altere premissas, reprocesse, compare e promova somente quando os guardrails aprovarem. A promoção torna o cenário a referência oficial do módulo; a rodada-base não é oficial por si só.

## Arquitetura do pacote

```text
vbeta1.0/
├── backend/              API FastAPI, SQLite e orquestração
├── frontend/             React/TypeScript e build pronto em dist/
├── engines/primary/      solver principal preservado
├── engines/scenarios/    solver secundário exclusivo de cenários
├── docs/                 documentação executiva, funcional e técnica
├── scripts/              instalação e testes
├── data/                 marcador; dados reais ficam fora do pacote
├── executar.py           launcher local de produção
└── iniciar.ps1           atalho de execução no Windows
```

Os motores são deliberadamente separados. A aba Cenários nunca modifica nem
substitui automaticamente o solver principal.

## Documentação

Comece por [Visão executiva](docs/00_VISAO_EXECUTIVA.md) e
[Instalação e operação](docs/06_INSTALACAO_E_OPERACAO.md). As regras de negócio,
arquitetura, solvers, API, interface, segurança, homologação e solução de
problemas estão detalhadas no diretório `docs`.

## Segurança

Esta versão foi desenhada para uso local em `127.0.0.1`. Ela não possui
autenticação nem TLS e não deve ser publicada em rede. Planilhas e resultados
podem conter dados pessoais; consulte a documentação de segurança antes de
copiar, compartilhar ou reter os artefatos.

## Verificação

```powershell
.\scripts\testar.ps1
```

O release registra versão, testes, hashes e limitações conhecidas nos documentos
de qualidade e homologação. Consulte também as [evidências de QA](docs/evidencias/README.md)
e os [avisos de terceiros](THIRD_PARTY_NOTICES.md).

Para conferir se nenhum arquivo do pacote foi alterado depois da homologação:

```powershell
python .\scripts\integridade_release.py --verificar
```
