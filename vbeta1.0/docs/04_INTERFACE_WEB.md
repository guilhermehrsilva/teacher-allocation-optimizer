# Interface web

## Princípios

A interface organiza a decisão em uma sequência única:

    Processar → Entender → Diagnosticar → Simular

Ela usa linguagem de negócio, mantém estados de carregamento e erro visíveis e evita que o usuário precise acessar arquivos técnicos para interpretar a rodada.

## Navegação

O menu superior contém:

1. Processamento;
2. Dashboard;
3. Insights;
4. Cenários.

A rota é mantida no fragmento da URL, permitindo atualizar a página sem exigir configuração especial no servidor.

## Processamento

### Seleção de módulo

A tela inicia com Selecione o Módulo. Nenhum módulo deve ser presumido visualmente. As opções são 51, 52, 53 e 54.

### Upload e validação

O usuário:

1. seleciona o módulo;
2. envia um XLSX;
3. recebe o resultado da validação;
4. baixa pendencias_validacao.xlsx quando precisa corrigir a base;
5. confirma ressalvas quando aplicável;
6. inicia a alocação.

A coluna DETALHES da planilha de pendências deve apresentar explicação humana e acionável, não estruturas JSON ou nomes internos de programação.

### Acompanhamento

O frontend consulta periodicamente o job enquanto ele não é terminal. A tela apresenta:

- estado atual;
- mensagem;
- histórico das fases;
- resumo da solução;
- artefatos para download;
- tabela paginada de alocações;
- busca por disciplina, docente ou chapa.

### Rodadas

O histórico permite escolher uma rodada. Zerar rodadas-base oferece:

- somente o último;
- zerar todos;
- cancelar.

Cenários dependentes também são removidos e isso deve ser informado antes da confirmação.

## Dashboard

O Dashboard é recalculado a partir da planilha de resultado e do manifesto da rodada escolhida.

### Filtros

A ordem é ORDEM, DIA, HORÁRIO, CLUSTER e CURSO.

- múltiplos valores na mesma dimensão usam OU;
- dimensões diferentes usam E;
- Limpar filtros volta ao recorte completo;
- opções extensas possuem busca;
- o total de ofertas do recorte deve permanecer visível.

### KPIs

O contrato atual inclui:

- cobertura percentual;
- ofertas alocadas e total;
- não alocadas;
- uso de docentes;
- docentes ativos, usados e sem alocação;
- quantidade por 1ª, 2ª e ESTENDIDA;
- demanda da primeira e da segunda etapa;
- delta demanda menos capacidade por etapa;
- capacidade letiva ativa utilizável.

Delta positivo indica déficit bruto. A nota metodológica precisa permanecer próxima do KPI.

### Gráficos

**Disciplinas e professores por dia:** barras lado a lado com valores explícitos.

**Horas demandadas por cluster:** barras horizontais ranqueadas com valor e participação de todos os clusters. Não há categoria Outros.

**Diagnósticos complementares:** motivos de não alocação, horas por etapa e demais cartões devem conservar unidade e fonte.

## Insights

Insights aprofunda a interpretação da rodada sem modificar os dados.

### Indicadores

Os KPIs de destaque são:

- cobertura;
- cursos abaixo de 90%;
- disciplinas sem cobertura;
- horas de demanda não alocada;
- alocações de candidato único;
- horas em RPA/NF como proxy.

Estatísticas adicionais de capacidade, concentração, utilização, risco, outliers e Pareto sustentam oportunidades e diagnósticos do serviço, mesmo quando não aparecem como cartões principais.

### Cobertura por curso e disciplina

O gráfico de cursos deve mostrar todos os cursos, não apenas um top 12. Para cada curso, exibe alocadas e não alocadas, com identificação dos dias associados às lacunas.

O gráfico de horários mais críticos complementa essa leitura e inclui:

- dia e horário;
- quantidade de lacunas;
- cursos afetados;
- curso mais recorrente;
- perfil mais recorrente.

### Diagnósticos

A tela apresenta:

- distribuição de carga docente;
- risco docente;
- composição por cluster, dia, coordenação e contrato;
- motivos das lacunas;
- oportunidades priorizadas;
- insights automáticos;
- metodologia e limitações.

Horas externas não devem ser apresentadas como custo monetário.

## Cenários

### Passos visuais

1. escolher rodada-base;
2. criar cenário com nome e objetivo;
3. escolher movimento;
4. configurar alterações ou políticas;
5. executar simulação;
6. comparar;
7. homologar, se elegível.

### Busca

Seletores extensos de ofertas e docentes possuem campo digitável. A busca por oferta considera disciplina, código, curso e linha; a busca por docente considera nome, chapa, função, status e perfil.

### Movimentos

- Reforçar ou reduzir capacidade;
- Reorganizar agenda;
- Ampliar compatibilidade;
- Alocar docentes do cluster;
- Proteger prioridades acadêmicas;
- Fixar decisões.

### Comparação

A comparação deve deixar claro:

- baseline;
- cenário;
- variação absoluta e percentual;
- ofertas alteradas;
- guardrails de validação, solver e auditoria;
- elegibilidade para homologação.

### Resets

A aba possui controles separados para rodadas-base e cenários salvos. Cada controle oferece último, todos ou cancelar.

## Estados e mensagens

Estados mínimos:

- vazio;
- carregando;
- sucesso;
- atenção;
- erro recuperável;
- erro terminal;
- ação desabilitada com justificativa.

Mensagens devem dizer o que aconteceu e qual ação o usuário pode tomar. Códigos internos podem aparecer em documentação técnica, mas não como explicação principal.

## Acessibilidade

O frontend atual inclui:

- link para pular ao conteúdo;
- foco visível;
- labels em campos;
- texto oculto para leitores de tela;
- navegação por teclado em elementos nativos;
- redução de animações conforme preferência do sistema;
- layouts responsivos.

Antes de cada release, validar teclado completo, zoom de 200%, contraste, leitura das legendas, tabelas em tela estreita e anúncio de erros.

## Identidade visual

A paleta usa azul institucional, verde para resultado saudável, âmbar para atenção, vermelho para risco e cinza para estado neutro.

Ubuntu é a primeira fonte declarada, com Segoe UI como fallback. Se Ubuntu não for distribuída, a apresentação no Windows usará a fonte disponível no sistema.
