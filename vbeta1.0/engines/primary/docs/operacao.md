# Operação da vbeta

## Preparação

Instale as versões homologadas das dependências:

```powershell
python -m pip install -r vbeta/requirements.txt
```

Coloque exatamente um `.xlsx` em `vbeta/entrada/` ou use `--base` para indicar um arquivo explícito. Arquivos temporários do Excel iniciados por `~$` são ignorados.

## Execução

```powershell
python vbeta/executar_pipeline.py
```

Exemplo com caminhos explícitos:

```powershell
python vbeta/executar_pipeline.py --base C:\dados\base.xlsx --resultado C:\dados\resultados --modulo 52
```

O caminho padrão é calculado a partir da própria pasta `vbeta`, portanto o comando também funciona quando chamado por caminho absoluto a partir de outro diretório.

## Códigos de saída

| Código | Significado |
|---:|---|
| 0 | Rodada concluída, auditada e publicada |
| 10 | Erro de configuração ou seleção da entrada |
| 20 | Validação reprovada ou não concluída |
| 30 | Solver ou gravação da alocação falhou |
| 31 | Solução utilizável, mas sem prova `OPTIMAL` obrigatória |
| 40 | Auditoria falhou ou reprovou a solução |
| 50 | Erro interno inesperado |

## Evidências da rodada

`status.json` registra a sequência operacional. `manifesto.json` registra versão da aplicação, contrato de validação, ambiente, configuração, fingerprints do código, métricas de cada fase e SHA-256/tamanho de todos os artefatos estáveis.

Cada execução cria `rodada_001`, `rodada_002` e assim por diante. Rodadas existentes não são sobrescritas.

## Verificação antes de compartilhar

Confirme no manifesto:

- validação `APROVADO` ou `APROVADO_COM_RESSALVAS` sem bloqueios;
- solver `OPTIMAL`, salvo uso consciente de `--permitir-nao-otimo`;
- auditoria `APROVADO` e zero ocorrências;
- estado final `CONCLUIDA` e código 0.

Execute também a suíte automatizada:

```powershell
python -m unittest discover -s vbeta/tests -p test_*.py -v
```
