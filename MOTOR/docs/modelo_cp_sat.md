# Formulação CP-SAT

## Conjuntos

- `T`: transmissões, formadas por `Curso único` e `Curso Responsável` ao vivo.
- `P`: docentes ativos.
- `E(t)`: docentes cujo perfil intersecta os perfis aceitos pela transmissão `t`.
- `S`: faixas definidas por `DIA_AULA + HORÁRIO`.
- `H = {primeira, segunda}`: etapas de cinco semanas do módulo.
- `H(t)`: etapas ocupadas por `t`; `1ª` ocupa a primeira, `2ª` a segunda e
  `ESTENDIDA` ambas.

As linhas `Sinérgica` não entram em `T`: elas acompanham uma transmissão
responsável e, nesta versão, não geram consumo adicional.

## Camada GRASP

Opcionalmente, antes da resolução exata, o motor executa uma busca multi-start
GRASP. Nas bases atuais ele fica desligado por padrão, pois o CP-SAT puro chega
ao ótimo mais rapidamente:

1. construção adaptativa que prioriza transmissões com poucos candidatos;
2. seleção randomizada em uma lista restrita controlada por `alpha`;
3. preferência inicial por docentes ainda ociosos e, depois, maior CH letiva;
4. busca local por inserção direta e trocas 1-por-1;
5. retenção da melhor solução segundo os mesmos critérios lexicográficos.

A solução GRASP, quando solicitada, é adicionada ao modelo como hint. Ela não
substitui nem relaxa as restrições do CP-SAT. Depois de cada objetivo
lexicográfico, o hint é substituído pela melhor solução da própria fase.

## Variáveis

- `x[t,p] ∈ {0,1}`: docente `p` transmite `t`.
- `u[t] ∈ {0,1}`: transmissão `t` ficou sem docente.
- `carga[p,h]`: horas letivas semanais atribuídas ao docente `p` na etapa `h`.
- `usado[p] ∈ {0,1}`: indica se o docente recebeu ao menos uma transmissão.

São criadas variáveis `x[t,p]` apenas para pares elegíveis por agenda, status,
perfil e capacidade, reduzindo o espaço de busca. O contrato histórico não
participa desse filtro.

## Restrições rígidas

1. Cobertura ou não alocação: `Σp x[t,p] + u[t] = 1`.
2. Capacidade semanal por etapa:
   `carga[p,h] = 2 × Σt:h∈H(t) x[t,p] ≤ CH_LETIVA[p]`.
3. Choque: para todo docente, etapa e faixa,
   `Σt:h∈H(t),t_na_faixa x[t,p] ≤ 1`.
4. Perfil e status: controlados pela própria criação dos pares elegíveis.
5. Docentes presenciais possuem capacidade especial de duas disciplinas no
   módulo inteiro, mesmo que ocorram em etapas diferentes, sem alterar as cargas
   zeradas da base docente.

Com essa formulação, uma disciplina de `1ª` e outra de `2ª` podem reutilizar a
mesma capacidade e faixa de um docente. Uma `ESTENDIDA` consome capacidade e
ocupa sua faixa nas duas etapas.

O contrato registrado na disciplina é histórico e não participa da
elegibilidade. Após a escolha do docente, sua função determina a sugestão
`CLT EAD` ou `CLT STRICTO` exibida no resultado.

## Objetivo lexicográfico

O problema é resolvido em quatro fases:

1. minimizar `Σt u[t]`;
2. `SWITCH 1`: fixar a cobertura e maximizar `Σp usado[p]`;
3. `SWITCH 2`: fixar cobertura e docentes usados e maximizar
   `Σt,p CH_LETIVA[p] × x[t,p]`;
4. `SWITCH 3`: fixar todos os ótimos anteriores e minimizar a quantidade de
   transmissões não alocadas que possuam exatamente um docente elegível.

Isso impede que os `SWITCHS` sacrifiquem uma transmissão que poderia ser alocada.
Primeiro reduzimos docentes sem nenhuma atribuição; depois, as transmissões
restantes são deslocadas para docentes com maior capacidade letiva.
O terceiro SWITCH não relaxa perfil, carga ou horário: ele protege somente casos
insubstituíveis entre soluções igualmente ótimas. Disciplinas com dois ou mais
candidatos não recebem prioridade apenas pela contagem de candidatos.

Depois das quatro fases, os valores ótimos são fixados, o objetivo e os hints
paralelos são removidos e uma busca de satisfação com um único worker escolhe a
solução canônica. Essa etapa não altera nenhuma métrica de negócio; ela apenas
evita que empates produzam docentes diferentes em execuções com a mesma base e
os mesmos parâmetros.

## Resultado do piloto

### Rodada 001 — modelo inicial

- 402 transmissões identificadas;
- 359 alocadas, correspondendo a 718 horas letivas;
- 43 não alocadas: 29 por competição de carga/horário, 13 sem docente elegível e
  1 por agenda inválida;
- solução `OPTIMAL` nas duas fases do modelo inicial;
- nenhuma violação de perfil, carga ou choque na auditoria do arquivo final.

### Rodada 002 — SWITCHS e base AR123

- fonte: `BASE_TESTE_AR/BASE_SINTETICA_PERFIL_DOCENTE_AR123.xlsx`;
- 402 transmissões identificadas;
- 360 alocadas, correspondendo a 720 horas letivas;
- 42 não alocadas: 29 por competição de carga/horário e 13 sem docente elegível;
- 182 dos 183 docentes ativos receberam alocação;
- o único docente ativo sem alocação não possui transmissão compatível com seu
  perfil nesta base;
- as três fases retornaram `OPTIMAL`;
- nenhuma violação de status, perfil, carga ou choque na auditoria final.

### Rodada 003 — resgate por escassez

- mesma fonte AR123 e os mesmos ótimos principais: 360 transmissões alocadas e
  182 docentes ativos utilizados;
- 42 não alocadas: 13 sem docente elegível, 5 com capacidade letiva esgotada,
  19 por choque de horário e 5 por combinação de carga e horário;
- penalidade de escassez reduzida de 414 para 395 em relação à rodada 002;
- o SWITCH preservou mais transmissões com apenas 1 ou 2 candidatos;
- as quatro fases retornaram `OPTIMAL`;
- nenhuma violação de status, perfil, carga ou choque na auditoria final.

### Rodada 004 — GRASP + CP-SAT sem limite temporal

- 200 construções GRASP com `alpha = 0,25`;
- o GRASP já encontrou 360 alocações, mas utilizava 178 docentes, score de CH
  3275 e penalidade de escassez 408;
- o CP-SAT refinou para 182 docentes utilizados, score de CH 3341 e penalidade
  de escassez 395;
- resultado final mantido em 360 alocações e 42 pendências;
- as quatro fases CP-SAT retornaram `OPTIMAL`, sem limite de tempo configurado;
- nenhuma violação de status, perfil, carga ou choque na auditoria final.

## Premissas pendentes

- Perfis separados por vírgula são alternativas.
- Os horários `19:00` e `20:40` são faixas distintas e não se sobrepõem.
- `CH_LETIVA` representa a capacidade semanal disponível em cada etapa para este
  processo.
- Ainda não existe uma chave explícita ligando cada linha sinérgica à transmissão
  responsável; por isso a saída lista apenas as transmissões.
