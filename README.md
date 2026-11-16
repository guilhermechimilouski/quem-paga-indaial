# Quem paga, Indaial?

**https://quempagaindaial.com.br**

Monitor independente dos 13 vereadores de Indaial (SC), legislatura 2025–2028: quanto cada um custa (salário, assessores, diárias, encargos), presença, como vota, o que propõe e quais pedidos se repetem.

Tudo vem de fontes oficiais e públicas:

- API de dados abertos da Câmara Municipal de Indaial (proposições, sessões)
- Relatórios do painel eletrônico de votação (PDF por sessão)
- Atas das sessões publicadas no site da Câmara
- Portal da Transparência da Câmara (folha de pagamento, diárias, despesas)

O site não dá nota, não apoia partido nem candidato e não recebe dinheiro de ninguém. Encontrou um erro? Escreva para **contato@quempagaindaial.com.br**.

## Como funciona

```
docs/                 site (GitHub Pages): index.html lê data.json
  data.json           todos os números do site, gerado automaticamente
coletor/              programa que coleta e calcula
  coletar.py          baixa API, PDFs de votação e atas
  agregar.py          transforma o que foi coletado em números
  importar.py         lê as planilhas de folha e diárias do Portal da Transparência
  paginas.py          gera as páginas dos vereadores e o sitemap
  montar.py           gera docs/data.json
dados/
  vereadores.json     lista oficial, partidos e links
  gabinetes.json      qual assessor trabalha com qual vereador (fonte: perfis oficiais)
  correcoes.json      registro público de correções
  manual/             planilhas mensais do Portal da Transparência
  brutos/             dados intermediários
.github/workflows/    vigia diário e atualização de reserva
```

## Atualização

- **Todo dia (automática):** uma tarefa agendada no computador do responsável coleta sessões, votações, atas e proposições novas, recalcula o site e envia ao GitHub. A coleta roda num computador e não no GitHub porque o site da Câmara bloqueia os servidores do GitHub Actions.
- **Uma vez por mês (semiautomática):** folha de pagamento e diárias. O Portal da Transparência pede a verificação "Confirme que é humano" em cada consulta, então o responsável confirma a verificação e o script baixa o resto.
- **Vigia:** o workflow `vigia.yml` confere todo dia se os dados foram atualizados. Se passar de 2 dias sem atualização, ele falha e o GitHub avisa por e-mail.
- **Páginas para o Google:** a cada atualização, `coletor/paginas.py` gera uma página estática por vereador (`/vereador/<nome>/`), o `sitemap.xml` e as marcações para buscadores.

Para rodar no computador:

```bash
pip install -r requirements.txt
cp .env.example .env          # cole o token da API em RADAR_TOKEN
python -m coletor.coletar atualizar
python -m testes.test_coletor # testes sem internet
```

## Correções

Pedidos de correção são respondidos em até 2 dias úteis. Cada correção entra em `dados/correcoes.json` com data e aparece na página "Quem faz" do site.

## Responsável

Guilherme Patrick Chimilouski Glatz · contato@quempagaindaial.com.br

Código sob licença MIT. Os dados são públicos e podem ser reutilizados citando a fonte original.
