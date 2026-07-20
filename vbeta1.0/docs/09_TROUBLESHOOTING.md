# Troubleshooting

## A aplicação não abre

1. Confirme que o processo do backend está ativo.
2. Abra http://127.0.0.1:8000/api/health.
3. Verifique se a porta 8000 está livre.
4. Confirme que frontend/dist existe.
5. Consulte stderr do servidor.

Se a API responde mas a tela não abre, refaça o build do frontend.

## Health check indica motor indisponível

Confirme se os diretórios engines/primary e engines/scenarios existem no pacote e se a configuração aponta para a raiz correta.

Não copie somente backend e frontend; os dois motores são parte do runtime.

## A porta 8000 está ocupada

Encerre a instância anterior ou o processo que usa a porta. Não inicie duas instâncias apontando para o mesmo SQLite.

Um launcher de produção deve detectar essa condição antes de inicializar.

## O módulo não pode ser selecionado

A tela deve exibir Selecione o Módulo. Escolha 51, 52, 53 ou 54 antes de enviar o arquivo.

Se a opção foi escolhida e o erro continua, atualize a página e repita o upload.

## Upload recusado

Verifique:

- extensão XLSX;
- tamanho até 50 MB;
- arquivo não corrompido;
- permissão no diretório de dados;
- nome da planilha e cabeçalhos.

Feche o Excel se ele estiver mantendo arquivo temporário ou bloqueio.

## Validação REPROVADO

Baixe pendencias_validacao.xlsx e corrija primeiro itens de severidade alta ou bloqueante.

Não tente contornar o bloqueio alterando o banco.

## APROVADO_COM_RESSALVAS não inicia

É necessário confirmar as ressalvas no fluxo de Processamento. Leia a orientação antes de confirmar.

## A planilha de pendências parece técnica

Atualize a página e gere novamente o download. A coluna DETALHES deve ser linguagem humana. Se estruturas de programação aparecerem, registre o código da pendência e preserve somente um exemplo anonimizado.

## Job em INTERROMPIDA

O servidor foi reiniciado durante QUEUED ou RUNNING.

1. consulte status e logs;
2. confirme que não há processo do solver ativo;
3. preserve artefatos para diagnóstico;
4. inicie nova rodada.

Não marque manualmente como concluída.

## Solver PARCIAL

PARCIAL significa que há não alocadas. Verifique também solver_status:

- OPTIMAL: o máximo sob as regras foi provado;
- FEASIBLE: existe solução, mas o ótimo não foi provado;
- outros estados: investigar diagnóstico.

Use motivos de não alocação e Cenários para avaliar alternativas.

## OTIMO_NAO_COMPROVADO

A execução tinha exigência de ótimo e alguma fase não foi provada.

Possíveis ações:

- remover limite de tempo;
- evitar outras tarefas pesadas;
- conferir versão do OR-Tools;
- executar novamente;
- revisar se o cenário adicionou prioridade inviável.

Não homologar como resultado oficial sem decisão explícita de governança.

## AUDITORIA_REPROVADA

A auditoria detectou divergência entre solução e regras.

Preserve:

- manifesto;
- auditoria_alocacao.json;
- resumo;
- status;
- logs.

Não use a planilha como resultado final. A falha exige correção técnica e nova execução.

## Cenário não permite configurar

Confirme:

- existe uma rodada principal CONCLUIDA;
- a baseline é do tipo PRIMARY;
- o cenário está RASCUNHO;
- o catálogo foi carregado;
- o cenário não está EXECUTANDO ou HOMOLOGADO.

Ofertas exibidas são somente as ofertas efetivamente presentes na baseline, não todas as linhas do mapa.

## Oferta ou docente difícil de localizar

Use o campo digitável acima do seletor.

Para oferta, busque nome, código ou curso. Para docente, busque nome, chapa, função, status ou perfil.

## Política de cluster não encontra solução

ALOCAR_CLUSTER flexibiliza perfil exato, mas não ignora:

- status ativo;
- função reconhecida;
- capacidade;
- agenda;
- limite Stricto;
- relação de perfil com o cluster.

Verifique também se o cluster selecionado possui a oferta esperada.

## Prioridade torna o cenário inviável

PRIORIDADE exige cobertura. Se não houver docente que respeite as demais restrições, o cenário falhará. Ajuste capacidade, agenda ou compatibilidade antes de repetir.

## Cenário não pode ser homologado

Confirme os guardrails:

- validação aceitável;
- solver OPTIMAL;
- auditoria APROVADO;
- execução concluída.

FEASIBLE não satisfaz a promoção atual.

## Reset retorna conflito

Existe job afetado em QUEUED ou RUNNING. Aguarde ou encerre corretamente a execução antes de repetir.

Rodada-base pode ter cenários dependentes; a interface deve informar a exclusão em cascata.

## Artefato não encontrado

1. confirme que a rodada foi criada;
2. verifique manifesto.json;
3. confira a chave do artefato;
4. valide caminho relativo e hash;
5. restaure backup se arquivos foram movidos.

Não edite caminhos diretamente no SQLite sem plano de recuperação.

## Dashboard ou Insights não atualizam

- selecione outra rodada e retorne;
- remova filtros;
- use atualização forçada do navegador;
- confirme que o job está CONCLUIDA;
- verifique se resultado_alocacao.xlsx e resumo existem;
- consulte erro da API.

## Layout diferente na apresentação

A fonte Ubuntu pode não estar instalada. O fallback Windows é Segoe UI.

Confirme zoom, resolução e navegador. Use a mesma máquina da homologação sempre que possível.

## Coleta segura para suporte

Compartilhe somente:

- versão;
- estado;
- mensagem;
- manifesto anonimizado;
- trecho necessário do log;
- passos para reproduzir.

Remova nomes, chapas, caminhos de usuário e conteúdo acadêmico não necessário.

