"""Catálogo editorial. Não executa verificações nem define limites novos."""

import re
from engine import design_criteria as dc
from engine.webapp.energy_indicators import _numero_br


def catalogo_criterios():
    def n(v):return _numero_br(v, 6).rstrip('0').rstrip(',')
    def faixa(v):return f'{n(v[0])} a {n(v[1])}'
    def c(id, nome, componentes, natureza, criterio, fonte, alcance, interpretar, analisar):
        return dict(id=id, nome=nome, componentes=componentes, natureza=natureza,
                    criterio=criterio, fonte=fonte, alcance=alcance,
                    interpretar=interpretar, analisar=analisar)
    d='Dixon & Hall, 7ª ed., discussão de cascatas e triângulos de velocidade (referência contextual).'
    m='Mattingly, Elements of Gas Turbine Propulsion; referências do modelo de combustor.'
    projeto='Critério/hipótese adotado no projeto; não é uma exigência universal da literatura.'
    return [
        c('mach','Condição sônica e Mach local',('Compressor','Turbina'),'Definição física',
          f'M = {n(dc.MACH_SONICO)} define a condição sônica; aviso de Mach acima desse valor.',d,
          'Mach na estação e no referencial indicados pela mensagem; M relativo usa a velocidade vista pelo rotor.',
          'Ultrapassar 1 identifica escoamento supersônico local. Não prova, isoladamente, impossibilidade da máquina.',
          'Conferir estação, temperatura estática e triângulo; avaliar choques e perdas com um modelo apropriado se necessário.'),
        c('mach_bocal','Mach na saída do bocal',('Turbina',),'Escolha do projeto',
          f'Aviso acima de {n(dc.MACH_BOCAL_TURBINA)}.',projeto,
          'Mach absoluto M2 na saída do bocal; é distinto da definição de condição sônica.',
          'O valor é um limiar adotado de triagem, não um limite físico universal.',
          'Examinar aceleração no bocal e compressibilidade; o modelo não resolve choques.'),
        c('df','Fator de difusão de Lieblein',('Compressor',),'Critério empírico',
          f'Aviso para DF > {n(dc.DF_MAX)}; rotor e estator identificados separadamente.',d,
          'Triagem de difusão na cascata. O valor radial usa a solidez local construída.',
          'Um excesso sinaliza difusão elevada; o critério não prevê completamente separação, perdas ou estol.',
          'Conferir velocidades, solidez e seção crítica; avaliar cascata e perdas antes de atribuir estabilidade.'),
        c('reacao_comp_neg','Reação negativa no compressor',('Compressor',),'Escolha do projeto',
          f'Aviso para reação < {n(dc.REACAO_MIN)}.',projeto,
          'A definição e a localização da reação devem acompanhar o valor.',
          'No modelo, reação negativa indica rotor em aceleração. Não é uma proibição universal desse escoamento.',
          'Conferir a definição de reação, os triângulos e se a distribuição de carga corresponde à intenção de projeto.'),
        c('reacao_turb_lim','Reação da turbina fora de 0–1',('Turbina',),'Escolha do projeto',
          f'Avisos abaixo de {n(dc.REACAO_MIN)} ou acima de {n(dc.REACAO_MAX_TURBINA)}.',projeto,
          'Reação estática: queda de entalpia estática no rotor dividida pela queda estática no estágio. '
          'Dixon & Hall, Eq. 4.3a, p. 123, fundamenta a definição, não a universalidade destes limiares.',
          'O sinal e a magnitude podem indicar aumento de entalpia estática em uma fileira; exigem interpretação do estágio.',
          'Conferir as quedas estáticas e as velocidades de entrada/saída no painel de continuidade da turbina.'),
        c('reacao_comp','Reação comparativa do compressor',('Compressor',),'Faixa do projeto',
          faixa(dc.REACAO_COMP),projeto,'Faixa aplicada ao meanline. O mínimo radial da sensibilidade é outra grandeza.',
          'Estar fora da faixa não equivale à reação negativa nem à invalidação do caso.',
          'Comparar meanline e extremos radiais, mantendo suas definições e localizações.'),
        c('reacao_turb','Reação comparativa da turbina',('Turbina',),'Faixa do projeto',
          faixa(dc.REACAO_TURB),projeto,'Faixa comparativa aplicada à reação da turbina, inclusive nas seções radiais verificadas.',
          'Um desvio é uma comparação de projeto, não uma previsão de falha.',
          'Conferir o estágio e a seção extremos e a distribuição da expansão.'),
        c('camber_comp','Câmber do perfil do compressor',('Compressor',),'Hipótese geométrica',
          f'Aviso para |θ| > {n(dc.CAMBER_COMP_GRAUS)}°.',projeto,
          'Triagem da representação por arco circular; Carter é uma correlação empírica de desvio do compressor.',
          'O limite sinaliza dificuldade da aproximação geométrica, não uma validação aerodinâmica ou estrutural.',
          'Examinar ângulos metálicos e perfil 2D; considerar outra representação geométrica se necessária.'),
        c('camber_turb','Câmber do perfil da turbina',('Turbina',),'Hipótese geométrica',
          f'Aviso para |θ| > {n(dc.CAMBER_TURB_GRAUS)}°.',projeto,
          'Arco circular com incidência/desvio impostos como zero; Carter do compressor não é aplicado.',
          'O aviso se refere à aproximação do perfil; não demonstra que o estágio seja fisicamente impossível.',
          'Conferir a forma e as tangentes do perfil. Um modelo mais adequado de perfil/desvio pode ser necessário.'),
        c('espessura','Espessura relativa do perfil',('Compressor','Turbina'),'Hipótese geométrica',
          f'Aviso para t/c > {n(dc.ESPESSURA_RELATIVA_AVISO)}.',projeto,
          'Espessura parabólica simétrica, normal à linha de câmber.',
          'Limiar geométrico da ferramenta; não é dimensionamento de resistência ou espessura ótima.',
          'Examinar contornos, bordos e eventual interseção; resistência e fabricação exigem análises próprias.'),
        c('psi_comp','Carga ψ do compressor',('Compressor',),'Faixa do projeto',faixa(dc.PSI_COMP),projeto,
          'Trabalho por estágio normalizado por U²; conferir ψ solicitado e efetivo.',
          'O automático pode ajustar ψ e mudar a comparação com a faixa.',
          'Consultar a comparação de candidatos e a carga realmente adotada, sem usar somente a contagem de avisos.'),
        c('psi_turb','Carga ψ da turbina',('Turbina',),'Faixa do projeto',faixa(dc.PSI_TURB),projeto,
          'Queda de entalpia por estágio normalizada por U².',
          'Fora da faixa indica afastamento da orientação adotada, não uma reprovação universal.',
          'Conferir carga, reação, Mach e geometria conjuntamente. Na comparação de candidatos, '
          'observe o critério que determinou a escolha e os excessos que ainda permanecem.'),
        c('swirl','Swirl no escape da turbina',('Turbina',),'Escolha do projeto',
          f'Aviso para |Cθ/U| > {n(dc.SWIRL_ESCAPE_MAX)}.',projeto,
          'Verificação meanline somente na saída do último estágio.',
          'Velocidade tangencial residual acima do limiar adotado; não é uma verificação de todos os planos.',
          'Examinar o triângulo do último rotor e a intenção de descarga do projeto.'),
        c('fechamento','Desvio entre ciclo e meanline',('Ciclo','Sistema','Compressor','Turbina'),'Escolha do projeto',
          f'Limiar de aviso: {n(dc.FECHAMENTO_AVISO_PCT)}%.',projeto,
          'Compara alvos termodinâmicos e resultados das máquinas; desvios menores continuam visíveis.',
          'O limiar de aviso não é tolerância de projeto nem coincidência numérica.',
          'Consultar Fechamento ciclo–meanline e as interfaces; o combustor continua usando T02/P02 do ciclo.'),
        c('coincidencia','Coincidência numérica dos alvos',('Ciclo','Sistema'),'Identidade/comparação numérica',
          f'Tolerância relativa {dc.COINCIDENCIA_RTOL:.0e} e absoluta {dc.COINCIDENCIA_ATOL:.0e} nas unidades SI.',
          'Definição de comparação implementada nos diagnósticos do projeto.',
          'Usa os alvos e valores calculados disponíveis nesta execução.',
          'Igualdade dentro da tolerância verifica compatibilidade numérica, não validação física.',
          'Conferir resíduos e bases de massa; fechamento termodinâmico não comprova continuidade geométrica do difusor.'),
        c('balancos','Balanços e trabalho de Euler',('Ciclo','Combustor','Compressor','Turbina'),'Identidade/comparação numérica',
          'Conservação de massa/energia e relação de Euler; não há um limite de aprovação física único.',
          'Balanços: Saravanamuttoo e Mattingly (referências contextuais). '
          'Euler: Lakshminarayana, Eqs. 2.4–2.12, pp. 49–50.',
          'Os resíduos do caso ficam nos painéis de energia, triângulos e diagnósticos. Este catálogo não executa novamente os testes.',
          'Uma identidade satisfeita pode coexistir com hipóteses inadequadas ou limitações aerodinâmicas.',
          'Separar consistência algébrica, comparação com exemplos publicados e evidência experimental.'),
        c('phi_eq','Razão de equivalência global',('Combustor',),'Faixa do projeto',
          f'Rica: > {n(dc.PHI_EQ_RICA)}; pobre: < {n(dc.PHI_EQ_POBRE)}; comparação: {faixa(dc.PHI_EQ_COMBUSTOR)}.',m,
          'φ_eq = f/f_estequiométrico é uma definição; os limiares de aviso são adotados pelo projeto.',
          'A mistura é global. O modelo não prevê as zonas da chama, extinção, fuligem ou temperatura de parede.',
          'Conferir combustível, razão estequiométrica e balanço; estabilidade da chama exige modelo/ensaio apropriado.'),
        c('comb_f','Razão combustível/ar',('Combustor',),'Escolha do projeto',
          f'Aviso para f > {n(dc.COMBUSTIVEL_AR_MAX)}.',projeto,
          'f é obtido pelo balanço que inclui a massa de combustível nos gases de saída.',
          'É triagem de razão combustível/ar; o modelo assume propriedades constantes e não resolve química detalhada.',
          'Conferir TIT, condições de entrada, eficiência e propriedades do combustível.'),
        c('mach_comb','Mach prescrito no combustor',('Combustor',),'Orientação contextual',
          f'Aviso acima de {n(dc.MACH_ENTRADA_COMBUSTOR_AVISO)}.',
          'Mattingly, §10.6.6: orientação contextual para as condições estudadas; não limite universal.',
          'Entrada prescrita no formulário, não derivada do compressor; difusor não modelado.',
          'A orientação não comprova que o trecho compressor–combustor realize a desaceleração requerida.',
          'Conferir o uso no dimensionamento 1D e registrar a limitação do difusor.'),
        c('eta_comb','Eficiência de combustão',('Combustor',),'Faixa do projeto',faixa(dc.ETA_COMBUSTOR),
          'Faixa do projeto. Mattingly, exemplo 7.8, usa 0,99 como dado de um caso, não como faixa universal.',
          'Fração do PCI aproveitada no balanço simplificado.',
          'Não prevê a eficiência real por geometria, mistura ou condições locais.',
          'Consultar a fonte das propriedades do combustível e as bases dos indicadores energéticos.'),
        c('orientacao','Orientações de HTR, φ e DF alvo',('Compressor','Turbina'),'Faixa do projeto',
          f'HTR compressor: {faixa(dc.HTR_COMP)}; turbina: {faixa(dc.HTR_TURB)}; φ: {faixa(dc.PHI_MAQUINAS)}; DF alvo: {faixa(dc.DF_ALVO_COMP)}.',
          projeto,'Orientações de entrada, distintas do DF calculado e dos HTR locais resultantes.',
          'Não transformam toda combinação dentro da faixa em uma máquina adequada.',
          'Conferir geometrias, velocidades e resultados da combinação completa.'),
        c('dominio','Valor indefinido ou domínio numérico',('Ciclo','Sistema','Combustor','Compressor','Turbina'),
          'Domínio matemático','Valores finitos e condições admissíveis exigidas pelo modelo.',
          'Domínio das equações e validações implementadas no projeto.',
          'Depende da variável e da etapa identificadas na mensagem.',
          'Resultado indefinido não deve ser interpretado como um valor físico utilizável.',
          'Conferir entradas, estado da etapa e hipótese usada; evitar interpretar curvas ou geometria dessa parcela.'),
    ]


def criterio_do_aviso(aviso):
    """Associação conservadora por mensagem original. None significa não associado."""
    t=aviso.get('mensagem','').casefold();comp=aviso.get('componente')
    if re.search(r'\bnan\b|\bindefinid[oa]\b',t):return 'dominio'
    if 'θ_final' in t or 'câmber' in t or 'camber' in t:
        return 'camber_comp' if comp=='Compressor' else 'camber_turb' if comp=='Turbina' else None
    if 't/c' in t:return 'espessura'
    if 'm_entrada' in t:return 'mach_comb'
    if 'η_b' in t:return 'eta_comb'
    if 'φ_eq' in t:return 'phi_eq'
    if re.search(r'\bf\s*=',t):return 'comb_f'
    if 'swirl' in t:return 'swirl'
    if 'df_rotor' in t or 'df_estator' in t:return 'df'
    if 'r_c' in t or 'grau de reação' in t:
        if comp=='Compressor':return 'reacao_comp_neg' if re.search(r'<\s*0\b',t) else 'reacao_comp'
        if comp=='Turbina':return 'reacao_turb_lim' if re.search(r'<\s*0\b|>\s*1(?:\.0)?\b',t) else 'reacao_turb'
    if re.search(r'\bm2\b',t) and comp=='Turbina':return 'mach_bocal'
    if re.search(r'\bm[123]r?\b',t):return 'mach'
    if 'ψ' in t:return 'psi_comp' if comp=='Compressor' else 'psi_turb' if comp=='Turbina' else None
    if 'htr' in t or 'φ =' in t or 'df_alvo' in t:return 'orientacao'
    if 'ciclo' in t and ('difere' in t or 'saída calculada' in t or 'π_total' in t):return 'fechamento'
    return None


REFERENCIAS = [
    ('Saravanamuttoo, Cohen e Rogers — Gas Turbine Theory','Ciclo, difusão, equilíbrio radial e combustão.',
     'Exemplo 2.1, pp. 74–76; outros trechos registrados na matriz bibliográfica do projeto.'),
    ('Dixon & Hall — Fluid Mechanics and Thermodynamics of Turbomachinery, 7ª ed.',
     'Cascatas, Carter, reação, triângulos, continuidade e vórtice livre.',
     'Carter: Eqs. 3.34–3.35 e exemplo 3.1, pp. 86–87. Reação: Eq. 4.3a, p. 123; estágio repetitivo, pp. 125–127.'),
    ('Mattingly — Elements of Gas Turbine Propulsion','Balanço com combustível, equivalência, propriedades e escala do combustor.',
     'Exemplo com JP-4: p. 816 e Eq. 10-27. Escala: Eq. 10-34, p. 821; tabela 10-5, p. 822.'),
    ('Boyce — Gas Turbine Engineering Handbook, 2ª ed.','Eficiências, distribuição de trabalho, reação e balanço do combustor.',
     'Trechos registrados: p. 125, pp. 291–299 e pp. 371/373.'),
    ('Lakshminarayana — Fluid Dynamics and Heat Transfer of Turbomachinery',
     'Euler, referenciais de velocidade e limites da aproximação radial.',
     'Eqs. 2.4–2.12, pp. 49–50; Eq. 2.26, p. 63; Eqs. 4.97–4.100, pp. 300–304.'),
]
