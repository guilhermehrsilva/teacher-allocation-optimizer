# Ferramenta de Alocação Docente — vbeta

Versão beta autônoma do algoritmo validado de alocação docente. A execução faz, obrigatoriamente, as quatro etapas completas: validação da base, otimização CP-SAT, auditoria independente e publicação dos resultados.

Todo o código necessário está dentro desta pasta. A aplicação não importa arquivos de outras versões do repositório.

## Uso rápido

Requer Python 3.11 ou superior. No PowerShell, a partir da raiz do repositório:

```powershell
python -m pip install -r vbeta/requirements.txt
python vbeta/executar_pipeline.py
```

Por padrão, o programa procura exatamente um arquivo `.xlsx` em `vbeta/entrada/`, valida o módulo 52 e grava uma nova pasta em `vbeta/resultados/rodada_###`.

Também é possível informar a base e o módulo explicitamente:

```powershell
python vbeta/executar_pipeline.py --base C:\caminho\base.xlsx --modulo 52
```

Opções disponíveis:

```text
--base ARQUIVO
--entrada DIRETORIO
--resultado DIRETORIO
--modulo NUMERO
--workers NUMERO
--tempo-limite SEGUNDOS
--permitir-nao-otimo
```

Sem `--permitir-nao-otimo`, somente uma solução comprovadamente `OPTIMAL` é publicada. Não há limite de tempo padrão.

## Contrato de dados

A planilha deve seguir a mesma estrutura da base sintética usada na homologação, com as abas `MAPA PEDAGÓGICO` e `DOCENTES`. O contrato completo está em [docs/contrato_entrada.md](docs/contrato_entrada.md).

A coluna `MODELO_CONTRATO` da entrada é aceita apenas para compatibilidade estrutural e seu conteúdo é ignorado. O algoritmo calcula o contrato com base no docente alocado. Na saída:

- `ALOCACOES` contém somente `MODELO_CONTRATO`, calculado pela ferramenta;
- `MODELO_CONTRATO_ORIGEM` não existe;
- `DOCENTES` não contém coluna de modelo de contrato;
- o JSON não publica campos de comparação com valores anteriores.

## Regras principais

O módulo é dividido em duas etapas de cinco semanas. Disciplinas `1ª` consomem carga apenas na primeira etapa, disciplinas `2ª` apenas na segunda e disciplinas `ESTENDIDA` nas duas. A capacidade e os choques de horário são controlados separadamente por etapa. Veja [docs/regras_negocio.md](docs/regras_negocio.md).

## Resultado de cada rodada

Cada execução reserva uma pasta nova e nunca sobrescreve uma rodada anterior:

```text
resultados/rodada_###/
├── fonte/                  cópia imutável da base processada
├── validacao/              relatório JSON e ocorrências CSV
├── auditoria/              auditoria independente da solução
├── alocacao/               planilha e resumo JSON finais
├── manifesto.json          configuração, versões, hashes e métricas
└── status.json             histórico operacional da execução
```

Instruções detalhadas e códigos de saída estão em [docs/operacao.md](docs/operacao.md).

## Testes

```powershell
python -m unittest discover -s vbeta/tests -p test_*.py -v
```

Os testes cobrem validação, carga por etapa, elegibilidade, CP-SAT, GRASP, auditoria, relatórios e pipeline completo.
