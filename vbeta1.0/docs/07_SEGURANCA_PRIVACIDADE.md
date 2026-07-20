# Segurança e privacidade

## Classificação dos dados

As planilhas podem conter:

- nome e chapa de docentes;
- função, status e carga horária;
- gestor;
- perfis de atuação;
- decisões de alocação;
- dados acadêmicos e de coordenação.

Esses dados devem ser tratados como informação pessoal e institucional restrita.

## Princípio de implantação

A vBeta 1.0 foi projetada para execução local. O servidor escuta em 127.0.0.1 e não deve ser alterado para 0.0.0.0 em produção sem projeto adicional de segurança.

A versão atual não possui:

- login;
- perfis de acesso;
- autorização por operação;
- TLS;
- criptografia própria do banco;
- trilha de auditoria de usuários;
- mecanismo de sessão.

Portanto, a segurança depende do controle de acesso ao computador e ao diretório de dados.

No Windows, o diretório padrão de dados reais é:

    %LOCALAPPDATA%\UniCesumar\AlocacaoDocente\vbeta1.0

A pasta data incluída no pacote é apenas estrutural e não deve receber bases reais quando LocalAppData estiver disponível.

## Controles implementados

- limite de upload de 50 MB;
- somente extensão XLSX;
- bloqueio de fórmulas em campos de dados;
- validação antes do solver;
- cópia da fonte e verificação SHA-256;
- auditoria independente da solução;
- caminhos de download contidos na rodada;
- chaves estrangeiras no SQLite;
- reset bloqueado durante jobs afetados;
- separação entre motor oficial e motor de cenários;
- vinculação de cenário à baseline;
- promoção condicionada a validação, ótimo e auditoria.

## Riscos residuais

| Risco | Conduta |
|---|---|
| Pessoa com acesso ao computador chama rotas destrutivas | Restringir acesso ao perfil Windows e manter localhost |
| Cópia indevida de XLSX ou SQLite | Permissões de pasta e política de retenção |
| Backup incompleto | Copiar SQLite e arquivos como conjunto |
| Exposição em apresentação | Usar base anonimizada |
| Malware ou usuário local altera arquivos | Verificar hashes e proteger diretório |
| Instalação movida quebra caminhos absolutos do banco | Usar diretório de dados estável |
| Dependência vulnerável | Lock, SBOM e revisão antes de release |
| Porta local acessada por processo malicioso | Não executar software não confiável e considerar token local futuro |

## LGPD e minimização

Antes de processar:

- confirme a finalidade institucional;
- use apenas colunas necessárias;
- restrinja acesso a pessoas autorizadas;
- defina prazo de retenção;
- evite copiar dados para canais pessoais;
- registre quem aprovou o uso da base de demonstração.

Para apresentações, prefira dados sintéticos ou anonimizados. Trocar somente o nome não basta se chapa, gestor, curso ou combinações ainda identificarem a pessoa.

## Retenção sugerida

Defina formalmente:

- prazo para uploads reprovados;
- prazo para rodadas de teste;
- prazo para resultados oficiais;
- prazo para cenários não homologados;
- procedimento de descarte de backups.

O botão de reset é uma ferramenta operacional, não uma política automática de retenção.

## Compartilhamento

Ao compartilhar resultado:

- envie apenas os artefatos necessários;
- verifique destinatários;
- proteja o arquivo conforme política institucional;
- não envie o diretório de dados completo;
- não inclua logs se eles não forem necessários;
- use manifesto e checksum para integridade.

## Logs

stdout e stderr podem conter nomes de arquivo, estados e mensagens técnicas. Trate logs como restritos e revise antes de anexá-los a chamados.

Não registrar:

- credenciais;
- tokens;
- conteúdo integral da base;
- dados pessoais desnecessários;
- caminhos de usuário em documentação pública.

## Incidente

Em caso de exposição:

1. encerre a aplicação;
2. preserve evidências necessárias sem ampliar a cópia;
3. identifique arquivos e pessoas potencialmente afetadas;
4. informe os responsáveis de segurança e privacidade;
5. revogue acessos ao diretório ou dispositivo;
6. siga o processo institucional de incidente.

## Requisitos antes de uso em rede

Qualquer implantação multiusuário exige, no mínimo:

- autenticação corporativa;
- autorização por perfil;
- TLS;
- proteção CSRF quando aplicável;
- trilha de auditoria;
- gestão de segredos;
- banco e armazenamento protegidos;
- política de backup;
- testes de segurança;
- revisão LGPD.

Essa evolução está fora do escopo da vBeta 1.0 local.
