# Contrato da planilha de entrada

A vbeta recebe um arquivo Excel `.xlsx` com duas abas obrigatórias. Os nomes das abas e dos cabeçalhos são exatos. A ordem das colunas pode variar, mas não pode haver cabeçalhos ausentes ou duplicados.

## Aba `MAPA PEDAGÓGICO`

Cabeçalhos esperados:

1. `CURSO`
2. `NOME_CURSO`
3. `CURRÍCULO`
4. `COD_DISCIPLINA`
5. `NOME_DISCIPLINA`
6. `PERFIL_DISCIPLINA`
7. `MATRIZ`
8. `MÓD`
9. `ANO`
10. `ORDEM`
11. `VALIDADO`
12. `METODOLOGIA`
13. `FORMATO`
14. `PROVA`
15. `ENTURMAÇÃO`
16. `PERFIL`
17. `CLUSTER`
18. `COORDENADOR`
19. `MODELO_CONTRATO`
20. `SINERGIA`
21. `DIA_AULA`
22. `HORÁRIO`
23. `FORMATO_AULA`

`MODELO_CONTRATO` é mantido no arquivo de entrada para compatibilidade com a base sintética, mas seu valor não é validado nem consumido pelo algoritmo. O contrato publicado é calculado a partir da função do docente selecionado.

Entram no problema de alocação apenas linhas com:

- `SINERGIA` igual a `Curso Único` ou `Curso Responsável`;
- `FORMATO_AULA` igual a `AO VIVO`.

Linhas `Sinérgicas` permanecem informativas. O grão esperado é `CURRÍCULO + COD_DISCIPLINA`.

`ORDEM` aceita `1ª`, `2ª` ou `ESTENDIDA`. `HORÁRIO` deve ser uma hora válida para ofertas alocáveis e o módulo em `MÓD` deve coincidir com `--modulo`.

## Aba `DOCENTES`

Cabeçalhos esperados:

1. `NOME`
2. `CHAPA`
3. `NM_FUNCAO`
4. `CH_CONTRATADA`
5. `CH_LETIVA`
6. `GESTOR`
7. `STATUS`
8. `PERFIL_DISCIPLINA`

`CHAPA` deve ser única. `CH_CONTRATADA` e `CH_LETIVA` devem ser inteiros não negativos.

Funções reconhecidas:

- `PROFESSOR DE ENSINO SUPERIOR EAD`;
- `PROFESSOR REGENTE`;
- `PROFESSOR DE ENSINO SUPERIOR PRESENCIAL`.

Somente docentes com `STATUS=ATIVO` podem receber alocações. Perfis separados por vírgula são alternativas normalizadas por caixa e espaços.

## Segurança e rastreabilidade

Fórmulas em dados são bloqueadas pela validação. A base é copiada para a rodada antes do processamento e seu SHA-256 é conferido entre as fases.
