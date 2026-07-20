# Interface web da Ferramenta de Alocação

Primeira entrega vertical da aplicação. A interface mantém a `vbeta` como fonte única das regras de validação, otimização CP-SAT, auditoria e publicação.

## Estrutura

```text
tela/
├── backend/       API FastAPI e gerenciador de execuções
├── frontend/      React + TypeScript + Vite
└── data/          dados locais de execução (ignorado pelo Git)
```

O backend preserva as saídas em `tela/data/resultados/rodada_###` e mantém apenas os metadados operacionais em SQLite. Cada execução do solver ocorre em um processo Python separado e a fila inicial executa uma rodada por vez.

## Backend

Requer Python 3.11 ou superior.

```powershell
python -m pip install -r tela/backend/requirements.txt
python tela/backend/run.py
```

A API ficará disponível em `http://127.0.0.1:8000` e a documentação em `http://127.0.0.1:8000/docs`.

Testes:

```powershell
Set-Location tela/backend
python -m unittest discover -s tests -p "test_*.py" -v
```

## Frontend

Requer Node.js compatível com o Vite 7.

```powershell
Set-Location tela/frontend
npm install
npm run dev
```

Durante o desenvolvimento, o Vite encaminha `/api` para o backend em `127.0.0.1:8000`.

Para gerar a versão de produção:

```powershell
npm run build
```

Após o build, reinicie o backend. Ele detectará `tela/frontend/dist` e servirá a aplicação junto com a API.

## Fluxo implementado

1. upload e validação imediata do `.xlsx`;
2. confirmação explícita quando existem ressalvas;
3. execução da `vbeta` em processo separado;
4. acompanhamento pelos estados reais de `status.json`;
5. consulta paginada das decisões e download dos artefatos;
6. dashboard dinâmico com seleção múltipla nos filtros de ordem, curso, cluster,
   dia e horário (`OU` dentro de cada dimensão e `E` entre dimensões);
7. KPIs de demanda e delta de CH por metade do módulo, além de gráficos de
   agenda e composição da demanda por cluster;
8. aba de insights focada em cobertura por curso e disciplina, eficiência,
   escassez, capacidade interna e exposição a RPA/NF;
9. estrutura de cenários orientada aos movimentos esperados da diretoria.

Os insights são calculados sob demanda a partir da planilha de resultado e do
manifesto auditado da rodada. A metodologia adapta as análises dos notebooks
SIAP para o contrato atualmente disponível, mantendo explícitas duas lacunas:
Planejado × Realizado e valores financeiros de RPA só serão habilitados quando
essas fontes passarem a integrar os artefatos da aplicação.

A interface usa a paleta institucional azul/cinza e a família tipográfica Ubuntu
como referência da identidade visual oficial da UniCesumar. A linguagem visual
é compartilhada entre as abas: azul para informação, verde para resultado
saudável, âmbar para atenção, vermelho para risco e cinza para estado neutro.

O mecanismo de cenários ainda é apenas a próxima etapa visível da interface. Ele será implementado depois do fluxo principal ser homologado.
