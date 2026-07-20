# Validação das bases de alocação docente

O validador é a porta de entrada do futuro algoritmo de alocação. Ele lê a
planilha sem modificá-la e produz dois arquivos: um JSON para integração com a
aplicação e um CSV amigável para correção pelos responsáveis da base.

## Execução

```powershell
python VALIDADOR/validar_dados.py BASES_TESTE/BASE_SINTETICA_PERFIL_DOCENTE.xlsx --saida BASES_TESTE/resultado_validacao
```

O processo retorna código `0` para `APROVADO` e `APROVADO_COM_RESSALVAS`.
Somente inconsistências marcadas como bloqueantes produzem `REPROVADO` e código
`2`, impedindo automaticamente a execução da alocação.

## Contrato inicial

- `MAPA PEDAGÓGICO`: uma linha por `CURRÍCULO + COD_DISCIPLINA`.
- `DOCENTES`: uma linha por `CHAPA`.
- Campos obrigatórios, tipos, domínios e chaves são verificados antes das regras
  cruzadas.
- Apenas docentes `ATIVO` contam para cobertura.
- Perfis separados por vírgula são tratados como alternativas. A oferta está
  coberta quando pelo menos um perfil coincide exatamente, ignorando apenas
  caixa e espaços excedentes.
- Somente `Curso Único` e `Curso Responsável` ao vivo entram no motor; linhas
  `Sinérgica` e `NSA` são contexto e não geram carga adicional.
- Aulas alocáveis sem dia ou horário utilizável são mantidas como ressalva para
  que o motor as registre explicitamente como `AGENDA_INVALIDA`.
- `MODELO_CONTRATO` é histórico: valores ausentes ou legados geram ressalva,
  mas não bloqueiam nem restringem a cobertura por docentes.
- Docentes presenciais possuem capacidade especial de duas disciplinas, sem
  alterar as cargas zeradas da base.

## Severidades

- `CRÍTICA`: estrutura, chave ou arquivo inviabiliza o uso seguro.
- `ALTA`: dado ausente/inválido ou regra necessária à alocação falhou.
- `MÉDIA`: provável inconsistência que exige confirmação de negócio.
- `BAIXA`: problema cosmético sem impacto direto no piloto.

As enumerações operacionais estão centralizadas em
`VALIDADOR/src/alocacao_docente/validation.py`. Se um novo valor legítimo
aparecer, o contrato deve ser atualizado junto com um teste. A exceção é
`MODELO_CONTRATO`, mantido como histórico e validado sem bloquear a execução.
