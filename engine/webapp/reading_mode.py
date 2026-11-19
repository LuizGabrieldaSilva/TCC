"""Orientação de leitura; independente do cálculo e dos parâmetros submetidos."""

import streamlit as st
from engine.webapp.energy_indicators import _numero_br


def escolher_modo():
    modo = st.radio('Nível de detalhe', ['Guiado', 'Técnico'], key='modo_leitura', horizontal=True,
                    help='Muda somente a apresentação. Equações, verificações e limitações permanecem disponíveis nos dois modos.')
    st.caption('Guiado: orientações para acompanhar o projeto. Técnico: consulta direta dos resultados. '
               'Alterações nas entradas são aplicadas ao clicar em Calcular e atualizar gráficos.')
    return modo == 'Guiado'


GUIAS = {
    'Geometria 3D': (
        'Mostra a geometria das pás, de uma pá de referência ao componente multiestágio.',
        'Comece com uma pá e suas seções. Depois selecione um estágio ou o componente completo, '
        'ative a repetição circunferencial e gere a montagem. Arraste para girar e amplie com o mouse.',
        'A malha é uma representação das seções calculadas, não um sólido validado. '
        'A vista leve desenha uma amostra de pás; confira as contagens e as limitações abaixo.'),
    'Comparar projetos': (
        'Compara duas execuções e o efeito da discretização radial com os modelos existentes.',
        'Fixe o caso calculado como referência, altere as entradas e calcule outro caso. '
        'Confira as entradas modificadas, os resultados e as distribuições radiais. O estudo de seções roda somente ao solicitar.',
        'Mais seções refinam a amostragem. Mudanças de estágios automáticos também alteram o projeto; '
        'contagem de avisos e diferenças menores não garantem validade física.'),
    'Verificações': (
        'Reúne os avisos registrados no caso e as fontes/limitações dos critérios usados.',
        'Comece pelo resumo por componente, filtre os avisos e escolha um registro para consultar '
        'mensagem completa, interpretação e próxima análise. Use o catálogo para entender a natureza do critério.',
        'O catálogo não é uma lista de aprovações. Zero avisos e fechamento numérico não validam '
        'estabilidade, resistência ou fabricação. Os painéis locais continuam disponíveis.'),
    'Ciclo': (
        'O ciclo fornece os estados termodinâmicos globais e o balanço de potência.',
        'Comece pelas temperaturas e pressões das estações. Depois compare produção da turbina, '
        'consumo do compressor e saldo no painel Balanço energético visual.',
        'Eficiência sobre calor útil e eficiência sobre PCI usam denominadores diferentes. '
        'Confira as bases no painel de indicadores e os desvios dos estágios em Fechamento ciclo–meanline.'),
    'Combustor': (
        'Recebe as condições de saída do compressor calculadas pelo ciclo e aquece a mistura até a TIT informada.',
        'Acompanhe combustível → razão combustível/ar → vazão de gases enviada à turbina. '
        'Use os tooltips das tabelas e os painéis de equações para interpretar energia e dimensões.',
        'O Mach de entrada é prescrito. O difusor não é modelado e o comprimento é uma estimativa; '
        'o fechamento do balanço verifica as hipóteses usadas, não a combustão real.'),
    'Compressor': (
        'Distribui a compressão-alvo entre estágios e calcula o escoamento, os perfis e a geometria representativa.',
        'Confira estágios adotados e ψ efetivo; compare o resultado com o ciclo. '
        'Depois explore comparação entre estágios → distribuição radial → triângulos → perfil 2D e geometria.',
        'Meanline é o resultado no raio médio. Extremos radiais dependem das seções calculadas. '
        'Um aviso identifica um critério específico; ausência de avisos não comprova um compressor realizável.'),
    'Turbina': (
        'Distribui a expansão-alvo entre estágios e calcula o escoamento que produz potência no eixo.',
        'Confira estágios, carga efetiva e comparação com o ciclo. '
        'Explore reação, Mach, continuidade entre estágios, triângulos e perfis para relacionar os resultados.',
        'A vazão inclui ar e combustível. A seleção automática compara candidatos pela política do projeto; '
        'isso não certifica a máquina. As perdas entre fileiras e a resistência estrutural não são resolvidas.'),
    'Sensibilidade': (
        'Varia um parâmetro por vez ao redor das entradas submetidas, mantendo os demais conforme a referência desta execução.',
        'Leia o parâmetro no eixo horizontal e a resposta no vertical. A estrela marca o caso de referência; '
        'as faixas são comparações adotadas no projeto.',
        'No modo de estágios automáticos, cada ponto pode escolher outro número de estágios, gerando saltos. '
        'Linhas conectam casos calculados; não constituem um mapa experimental de operação.'),
    'Downloads': (
        'Reúne arquivos dos resultados e da geometria do caso calculado.',
        'Use o JSON de entradas para recuperar o caso e o relatório ZIP para guardar resultados e hipóteses. '
        'Use CSV para consultar tabelas, JSON para diagnósticos/indicadores e DXF para a geometria disponível. '
        'Confira as descrições e limitações junto a cada exportação.',
        'As exportações representam o modelo preliminar e suas hipóteses; não são documentação de fabricação.'),
}


def exibir_guia(aba, guiado):
    if not guiado:
        return
    objetivo, percurso, limite = GUIAS[aba]
    with st.expander(f'Como ler esta aba — {aba}', expanded=True):
        st.markdown(f'**O que você encontra.** {objetivo}\n\n'
                    f'**Por onde começar.** {percurso}\n\n'
                    f'**Ao interpretar.** {limite}')


def orientacao_formulario(guiado, texto):
    if guiado:
        st.caption(texto)


def interpretar_ciclo(ciclo, guiado):
    if guiado:
        st.info(f'Leitura do caso: para cada 100 unidades de calor útil transferido aos gases, '
                f'o ciclo calcula {_numero_br(100*ciclo.eta_ciclo, 2)} unidades de trabalho líquido. '
                f'O compressor consome {_numero_br(100*ciclo.BWR, 2)}% da potência produzida pela turbina. '
                'Essa parcela (BWR) é diferente da eficiência. As hipóteses e as bases estão nos painéis abaixo.')
