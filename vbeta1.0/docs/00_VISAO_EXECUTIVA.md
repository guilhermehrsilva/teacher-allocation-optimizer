# Visão executiva

Versão documentada: **1.0.0**.

## Propósito

A Ferramenta de Alocação Docente vBeta 1.0 transforma uma planilha acadêmica em uma proposta de alocação rastreável, auditada e pronta para análise gerencial. Ela foi desenhada para reduzir o trabalho manual, tornar as restrições explícitas e permitir que decisões futuras sejam simuladas sem modificar o motor principal.

A aplicação atende quatro momentos:

1. validar a qualidade da base;
2. executar e publicar uma rodada-base;
3. explicar o resultado em Dashboard e Insights;
4. simular alternativas na aba Cenários e, quando aprovadas, promovê-las a resultado oficial.

## Valor para a decisão

A solução responde, de forma integrada:

- quais ofertas foram alocadas e quais continuam sem docente;
- por que uma oferta não foi alocada;
- como demanda, capacidade e cobertura se distribuem por etapa, dia, horário, curso e cluster;
- onde há concentração de risco ou escassez de docentes elegíveis;
- quais mudanças de capacidade, agenda, compatibilidade ou prioridade melhorariam o resultado;
- se um cenário respeita validação, otimalidade e auditoria antes de ser homologado.

O sistema não substitui a decisão acadêmica. Ele organiza evidências e aplica as regras configuradas de forma consistente.

## Jornada da aplicação

| Aba | Objetivo | Saída principal |
|---|---|---|
| Processamento | Receber, validar e processar a planilha | Rodada-base com artefatos auditáveis |
| Dashboard | Monitorar cobertura, demanda e capacidade | KPIs e gráficos filtráveis |
| Insights | Identificar lacunas, concentração e oportunidades | Diagnósticos acionáveis |
| Cenários | Testar mudanças sem alterar o solver oficial | Comparação com a rodada-base e opção de homologação |

## Controles de confiança

Cada rodada-base segue quatro portões:

1. **Validação:** verifica contrato, consistência e qualidade da planilha.
2. **Otimização:** usa CP-SAT para buscar a melhor solução segundo prioridades lexicográficas.
3. **Auditoria independente:** recalcula elegibilidade, carga, conflitos e coerência da saída.
4. **Publicação:** grava planilha, resumo, manifesto, status e hashes sem sobrescrever rodadas anteriores.

Publicar uma rodada-base não a torna automaticamente a referência oficial do módulo. Essa referência nasce quando um cenário elegível é promovido. O motor de Cenários é separado do motor principal; regras experimentais só existem no motor secundário e não alteram a lógica do solver principal.

## O que a vBeta 1.0 entrega

- upload de arquivo XLSX de até 50 MB;
- seleção dos módulos 51 a 54;
- planilha XLSX de pendências de validação;
- confirmação explícita quando há ressalvas;
- alocação CP-SAT com explicação por oferta;
- preservação das rodadas;
- filtros combináveis no Dashboard;
- análise de todos os cursos e identificação de dia e horário nas lacunas;
- cenários com alterações controladas e políticas de negócio;
- comparação entre cenário e baseline;
- promoção apenas de cenário validado, ótimo e auditado;
- exclusão do último registro ou de todos, com proteção durante execução.

## Limites da leitura executiva

- A aplicação mede horas, cobertura e concentração; o indicador de Pareto informa quantos docentes concentram 80% das horas alocadas.
- Não há fonte financeira nem cálculo monetário na versão atual.
- Não existe fonte de Planejado versus Realizado; as análises refletem a base e o resultado do algoritmo.
- O sistema é local, sem autenticação, e deve permanecer acessível apenas no computador que o executa.
- Um resultado de alocação “PARCIAL” pode ser matematicamente “OPTIMAL”: significa que o solver provou que não é possível alocar mais ofertas sob as restrições vigentes.
- Cenários representam hipóteses. A promoção registra a escolha gerencial, mas não altera retroativamente a rodada-base.

## Roteiro sugerido para apresentação à diretoria

1. Abrir Processamento e mostrar o contrato de entrada e a validação.
2. Explicar que ressalvas exigem confirmação e bloqueios impedem a execução.
3. Abrir uma rodada concluída e apresentar cobertura, pendências e artefatos.
4. No Dashboard, filtrar na ordem: ORDEM, DIA, HORÁRIO, CLUSTER e CURSO.
5. Mostrar demanda por cluster e agenda por dia.
6. Em Insights, demonstrar cursos, dias e horários com maior lacuna.
7. Criar um cenário a partir da rodada-base.
8. Aplicar uma alteração simples ou a política de alocação por cluster.
9. Executar o motor secundário e comparar o antes e o depois.
10. Mostrar os portões de homologação e explicar que o solver principal permaneceu intacto.

## Checklist antes da reunião

- [ ] Aplicação iniciada e health check aprovado.
- [ ] Base exemplos/BASE_DEMONSTRACAO_ANONIMIZADA_M52.xlsx confirmada.
- [ ] MANIFESTO_RELEASE.json verificado.
- [ ] Uma rodada-base concluída e auditada.
- [ ] Um cenário previamente testado.
- [ ] Navegador em zoom de 100% e resolução de apresentação verificada.
- [ ] Planilha de pendências e resultado final disponíveis.
- [ ] Plano alternativo com capturas ou vídeo, caso o ambiente de apresentação falhe.
- [ ] Nenhum nome, chapa ou arquivo real exposto sem autorização.
