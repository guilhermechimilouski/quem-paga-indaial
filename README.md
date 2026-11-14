# Quem paga, Indaial?

Painel independente que mostra **quanto custa cada vereador da Câmara Municipal de Indaial (SC)**, como vota, o que propõe e com que frequência comparece às sessões. Usa só dados públicos oficiais, cada número com a sua fonte.

> Status: **protótipo**. Os dados vão de jan/2025 (início do mandato) até out/2026.

## O que o painel mostra

- **Quanto custa:** subsídio, assessores e encargos de cada gabinete, mês a mês, e a folha da Câmara comparada com a do mandato anterior.
- **Como vota:** votos favoráveis e contrários, votações divididas e projetos rejeitados.
- **O que propõe:** indicações, requerimentos, moções e projetos de lei, cada tipo contado separadamente. Mais leis não significa mais produtividade.
- **Presença:** sessões com presença, faltas justificadas e não justificadas.
- **Pedidos repetidos:** ruas e temas que voltam às indicações várias vezes, sinal de problema que não foi resolvido.
- **Atas atrasadas:** sessões cujas atas ainda não foram publicadas e o que foi votado nelas.

## Fontes de dados

- API de dados abertos da Câmara Municipal de Indaial
- Relatórios do painel eletrônico de votação
- Atas publicadas no site da Câmara
- Portal da Transparência da Câmara (folha de pagamento, diárias e despesas)

## Como funciona

Hoje o projeto é uma página estática (`index.html`, HTML + CSS + JavaScript puro, sem dependências), com os dados já tratados embutidos em JSON. Funciona no celular e no computador.

## Próximos passos

- [ ] Coletor automatizado que busca e atualiza os dados nas fontes oficiais
- [ ] Separar os dados da página (arquivos JSON versionados)
- [ ] Atualização periódica automática
- [ ] Ranking com critérios públicos e documentados

## Aviso

Projeto independente, sem vínculo partidário. Não emite opinião, apenas organiza números públicos com a fonte indicada. Encontrou algum erro? Abra uma *issue*.
