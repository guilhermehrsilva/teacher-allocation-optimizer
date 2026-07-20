# Regras de negócio

## Fonte e escopo

A rodada recebe uma planilha XLSX com as abas MAPA PEDAGÓGICO e DOCENTES. Os cabeçalhos são validados por nome; a ordem física das colunas pode variar.

A interface aceita módulos 51, 52, 53 e 54. Em cada execução, somente registros do módulo selecionado participam do problema.

## Ofertas consideradas

O solver trabalha apenas com linhas que atendem simultaneamente:

- SINERGIA igual a Curso Único ou Curso Responsável;
- FORMATO_AULA igual a AO VIVO;
- módulo igual ao módulo selecionado.

Linhas sinérgicas permanecem informativas e não são ofertas do problema. O catálogo de Cenários também é limitado às ofertas efetivamente presentes na rodada-base; não deve exibir todo o mapa pedagógico.

O grão esperado é CURRÍCULO + COD_DISCIPLINA. Cada oferta mantém sua linha de origem para rastreabilidade.

## Duração e etapas

Cada transmissão representa 2 horas semanais. O módulo é dividido em duas etapas de cinco semanas.

| ORDEM | Primeira etapa | Segunda etapa |
|---|---:|---:|
| 1ª | 2 h | 0 h |
| 2ª | 0 h | 2 h |
| ESTENDIDA | 2 h | 2 h |

ORDEM é a fonte canônica para a etapa. METODOLOGIA pode gerar alerta de divergência, mas não redefine a etapa no solver.

Uma oferta de 1ª e outra de 2ª podem reutilizar a mesma capacidade e o mesmo horário porque não ocorrem na mesma etapa. ESTENDIDA ocupa as duas.

## Candidatura e alocação

Um docente entra na lista básica de candidatos quando:

- está ATIVO;
- possui função reconhecida;
- possui pelo menos um perfil exatamente compatível após normalização;
- possui capacidade para ao menos uma transmissão;
- a oferta possui dia e horário utilizáveis.

A decisão final também precisa respeitar:

- capacidade em cada etapa;
- limite específico de Stricto;
- ausência de choque no mesmo dia, horário e etapa;
- políticas adicionais, somente quando o motor de cenários é usado.

Perfis separados por vírgula são alternativas. Não há correspondência parcial por texto.

## Funções reconhecidas

| NM_FUNCAO | Família |
|---|---|
| PROFESSOR DE ENSINO SUPERIOR EAD | EAD interno |
| PROFESSOR REGENTE | EAD interno |
| PROFESSOR DE ENSINO SUPERIOR PRESENCIAL | Stricto/presencial |

Outras funções não recebem alocação.

## Regra Stricto/presencial

No solver, PROFESSOR DE ENSINO SUPERIOR PRESENCIAL pode receber no máximo duas disciplinas distintas no módulo. Com 2 horas por transmissão, a capacidade operacional especial é de 4 horas para a decisão do solver.

Essa regra é aplicada mesmo quando CH_LETIVA está zerada na fonte. A planilha original não é reescrita para simular carga; a exceção existe no domínio, no solver e na auditoria.

O limite é por módulo, não por etapa. Duas disciplinas na primeira e duas na segunda excederiam o máximo de duas.

## Capacidade exibida no Dashboard

O Dashboard possui uma regra exclusivamente analítica:

- usa a CH_LETIVA registrada para todos os docentes ativos, inclusive presencial;
- considera apenas horas que formam transmissões completas;
- arredonda para baixo ao múltiplo de 2.

Exemplo: CH_LETIVA de 9 horas contribui com 8 horas de capacidade utilizável no Dashboard.

Essa capacidade é bruta. Ela não é reduzida por perfil, agenda ou cluster. Por isso, o delta de capacidade é um sinal gerencial e não uma prova de que todas as horas podem cobrir qualquer disciplina.

O solver principal continua usando sua própria regra de elegibilidade e, para Stricto, o limite de duas disciplinas. Não se deve usar o KPI do Dashboard como substituto da restrição do solver.

## Choque de horário

Há choque quando o mesmo docente é escolhido para duas ofertas com:

- mesmo dia;
- mesmo horário;
- pelo menos uma etapa em comum.

Dia NSA ou horário inválido impede a candidatura daquela oferta e deve aparecer como agenda inválida.

## Objetivos de negócio

O solver principal preserva a seguinte ordem:

1. minimizar ofertas não alocadas;
2. maximizar docentes ativos com alguma alocação;
3. favorecer alocações em docentes de maior CH_LETIVA;
4. proteger ofertas com exatamente um candidato elegível;
5. escolher uma solução canônica entre empates.

Uma prioridade posterior nunca pode piorar o ótimo fixado nas anteriores.

## Motivos da decisão

Para oferta alocada, MOTIVO_ALOCACAO descreve por que o docente foi escolhido.

Para oferta não alocada, MOTIVO deve distinguir pelo menos:

- AGENDA_INVALIDA;
- SEM_DOCENTE_COM_PERFIL_E_CARGA;
- CAPACIDADE_LETIVA_ESGOTADA;
- CHOQUE_DE_HORARIO;
- CAPACIDADE_E_HORARIO_COMBINADOS.

O número de candidatos elegíveis também é publicado.

## Contrato publicado

MODELO_CONTRATO na entrada é aceito apenas por compatibilidade e não influencia o solver.

| Docente selecionado | MODELO_CONTRATO de saída |
|---|---|
| Professor EAD ou Professor Regente | CLT EAD |
| Professor presencial | CLT STRICTO |
| Sem alocação | A DEFINIR |

MODELO_CONTRATO_ORIGEM não integra o contrato publicado.

## Filtros do Dashboard

A ordem visual é:

1. ORDEM;
2. DIA;
3. HORÁRIO;
4. CLUSTER;
5. CURSO.

Dentro do mesmo filtro, várias escolhas são combinadas por OU. Entre filtros diferentes, aplica-se E.

Todos os clusters devem aparecer no gráfico de demanda; não existe agregação em Outros.

## Regras de Cenários

Um cenário parte obrigatoriamente de uma rodada principal concluída.

### Reforçar ou reduzir capacidade

Permite alterar, na cópia:

- STATUS do docente;
- CH_LETIVA do docente.

### Reorganizar agenda

Permite alterar, na oferta:

- DIA_AULA;
- HORÁRIO;
- ORDEM.

### Ampliar compatibilidade

Permite alterar PERFIL_DISCIPLINA de docente ou oferta.

### Alocar docentes do cluster

Para um cluster escolhido, o motor secundário pode recuperar uma oferta mesmo sem compatibilidade exata de perfil quando:

- o docente está ativo;
- possui função reconhecida;
- possui capacidade;
- não possui choque;
- tem ao menos um perfil presente no conjunto de perfis daquele cluster.

É uma flexibilização de negócio, não uma nova regra do solver oficial. A auditoria do cenário reconhece e registra esse override.

### Proteger prioridades acadêmicas

Curso ou oferta marcada como prioridade não pode ficar sem cobertura no cenário. Se as demais restrições tornarem isso impossível, o cenário falha em vez de publicar uma solução inconsistente.

### Fixar decisões

Preserva a alocação da baseline para uma oferta e recalcula o restante. A fixação só é aceita para o docente efetivamente alocado e ainda elegível.

## Comparação e homologação

A comparação apresenta, entre outros:

- cobertura da baseline e do cenário;
- variação de ofertas alocadas e não alocadas;
- variação de docentes usados;
- variação de horas internas e externas;
- diferença por etapa;
- trocas de docente e status por oferta.

Um cenário só pode ser promovido quando:

- sua validação é aceitável;
- todas as fases lexicográficas exigidas são OPTIMAL;
- a auditoria é APROVADO;
- a execução foi concluída.

Há um único resultado oficial por módulo. Promover outro cenário substitui a referência oficial, sem apagar os artefatos anteriores.

## Exclusão de rodadas e cenários

Os controles permitem excluir somente o último item ou todos.

- Zerar cenários remove os cenários escolhidos e suas execuções.
- Zerar rodadas-base remove a rodada escolhida, seu upload e cenários dependentes.
- Nenhuma exclusão é permitida enquanto um item afetado estiver QUEUED ou RUNNING.

A ação é destrutiva e exige confirmação na interface.

