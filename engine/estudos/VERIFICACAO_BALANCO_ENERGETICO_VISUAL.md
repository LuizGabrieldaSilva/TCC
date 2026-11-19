# Balanço energético visual — potências no eixo

Implementado e verificado em **11/11/2026**, correspondente ao bloco 2 da
lista agrupada de melhorias didáticas. Checkpoint:
`checkpoints/balanco_energetico_visual_2026-11-11/`.

## Uso e apresentação

Na aba **Ciclo**, abrir **Balanço energético visual — potências no eixo**.
O gráfico em cascata apresenta produção da turbina, retirada para acionar o
compressor e saldo líquido. Os nomes, valores e sinais acompanham as cores;
a retirada também usa hachura.

A equação aparece com os valores do caso, em kW. A parcela consumida pelo
compressor é identificada como BWR, sem confundi-la com eficiência térmica.
O controle **Mostrar valores, bases e conversão para potência** revela os
trabalhos específicos, bases de massa, vazões e potências, além das relações:

`Wdot_t = mdot_g w_t`, `Wdot_c = mdot_a w_c`,
`Wdot_liq = Wdot_t − Wdot_c` e
`w_liq,a = (mdot_g/mdot_a) w_t − w_c`.

O painel explica que kg/s × kJ/kg = kW. O trabalho da turbina está por kg de
gases; o do compressor e o líquido do ciclo, por kg de ar. Não se subtraem
diretamente trabalhos específicos de bases distintas.

## Fonte dos valores e alcance

O novo `webapp/energy_balance.py` lê os campos do ciclo já resolvido e
acoplado à vazão de combustível. Produção e consumo são os trabalhos
específicos do ciclo multiplicados pelas respectivas vazões; o saldo exibido
é `ciclo.W_líq`, preservado como resultado principal.

Não há novo modelo, recalculo termodinâmico ou substituição do resultado do
ciclo pelo dos meanlines. O painel de fechamento existente continua mostrando
essas diferenças. A prioridade de escolha dos candidatos não foi alterada.

O balanço é de potências no eixo, com transmissão mecânica ideal, sem gerador
ou consumos auxiliares; a potência líquida não é uma previsão de potência
elétrica. O calor do combustor e as eficiências continuam nos painéis próprios.

O resíduo usando os valores completos é disponibilizado nos detalhes.
Valores arredondados aparecem com aproximação na equação. Conferir essa
identidade do próprio modelo não é validação experimental.

## Verificações

- Seis casos do ciclo/combustor: razões de pressão 6, 8 e 12, com vazões de
  ar de 15 e 16 kg/s. Potências, bases, conversões e alturas das barras
  conferidas diretamente com os dados de origem.
- BWR conferido com o indicador do ciclo e resíduos menores que 1e-7 W nos
  casos testados. Objetos serializados antes/depois: nenhuma mutação.
- Renderizador exercitado com saldo zero e negativo por dados artificiais,
  sem declarar esses dados como novos casos físicos aceitos pelo núcleo.
- Figura do caso de referência renderizada e inspecionada: aproximadamente
  6.808,6 kW produzidos, 4.575,3 kW consumidos e 2.233,2 kW líquidos.
- AppTest aprovado: abertura dos detalhes, tabela com as bases corretas,
  preservação dos avisos/potência de referência e ausência de mutação ao
  consultar o painel.
- Alteração para 16 kg/s e TIT de 1100 K submetida no formulário: tabela
  atualizada com a nova potência e vazões. Retorno ao caso de referência
  automático preservou os metadados completos da seleção de candidatos.
  Sensibilidade sem erro de execução.

Script reproduzível: `verificar.py` na pasta de checkpoint, executado a partir
de `NEW`. Evidências: `dados.json`, `interface.json`, `interface.log` e
`balanco_referencia.png`. AppTest não substitui inspeção visual completa no
navegador ou validação física da máquina.

## Retorno

O checkpoint preserva `streamlit_app.py` e a matriz de rastreabilidade, com
caminhos relativos e hashes SHA-256 em `manifesto.json`. Para retornar,
encerrar o Streamlit e copiar esses dois arquivos para os caminhos em
`NEW/engine/`. Os novos `webapp/energy_balance.py` e este relatório podem ser
removidos após a restauração, se desejado. Não é necessário resetar o Git.
