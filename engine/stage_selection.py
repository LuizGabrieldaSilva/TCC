"""Seleção discreta de estágios por critérios explícitos do projeto.

Não é um otimizador físico universal. Cada candidato fecha o trabalho do ciclo;
os modelos meanline, radial e de perfis existentes fornecem as verificações.
"""

import contextlib
import io
import math
from engine import design_criteria as dc


def vizinhos(estimativa):
    if not math.isfinite(estimativa) or estimativa <= 0:
        raise ValueError("Estimativa de estágios deve ser finita e positiva.")
    return sorted({max(1, math.floor(estimativa)), max(1, math.ceil(estimativa))})


def _valores(dados):
    if isinstance(dados, dict):
        return [x for v in dados.values() for x in _valores(v)]
    if isinstance(dados, (list, tuple)):
        return [x for v in dados for x in _valores(v)]
    if dados is None or not math.isfinite(dados):
        raise ValueError("Candidato com métrica não finita ou não calculada.")
    return [float(dados)]


def _superior(valores, limite):
    return max(0., max(valores) / limite - 1.)


def _faixa(valores, minimo, maximo):
    return max(0., (minimo-min(valores))/(maximo-minimo),
               (max(valores)-maximo)/(maximo-minimo))


def avaliar_criterios(modelo, radial, perfis, compressor):
    """Pior excesso por família; repetições em estágios/seções não somam votos.

    Excesso superior: max(0, valor/limite-1). Faixas: distância dividida
    pela largura da faixa. Pesos/prioridades são política explícita do projeto.
    """
    reacao = _valores(radial.R_c) + _valores(modelo.grau_reacao)
    aero = {"reacao_negativa": max(0., dc.REACAO_MIN-min(reacao))}
    if compressor:
        aero.update(
            Mach_relativo=_superior(_valores(radial.M1R)+_valores(modelo.M1R), dc.MACH_SONICO),
            DF_rotor=_superior(_valores(radial.DF_rotor)+_valores(modelo.DF_rotor), dc.DF_MAX),
            DF_estator=_superior(_valores(radial.DF_estator)+_valores(modelo.DF_estator), dc.DF_MAX),
        )
        faixa_psi, faixa_reacao, limite_camber = dc.limites_componente(True)
        # No compressor, a faixa comparativa de reação é verificada no meanline.
        reacao_faixa = _valores(modelo.grau_reacao)
    else:
        aero.update(
            reacao_acima_de_um=max(0., max(reacao)-dc.REACAO_MAX_TURBINA),
            Mach_relativo=_superior(_valores(radial.M3R)+_valores(modelo.M3R), dc.MACH_SONICO),
            Mach_bocal=_superior(_valores(radial.M2)+_valores(modelo.M2), dc.MACH_BOCAL_TURBINA),
        )
        faixa_psi, faixa_reacao, limite_camber = dc.limites_componente(False)
        reacao_faixa = reacao
    cambers = [abs(p.theta_final) for est in perfis.values()
               for sec in est.values() for p in sec.values()]
    geometria = {"camber": _superior(_valores(cambers), limite_camber)}
    faixas = {
        "psi": _faixa([modelo.psi_efetivo], *faixa_psi),
        "reacao": _faixa(reacao_faixa, *faixa_reacao),
    }
    if not compressor:
        faixas["swirl_escape"] = max(0., abs(modelo.v3[-1]/modelo.U)/dc.SWIRL_ESCAPE_MAX-1.)
    resumo = dict(
        excesso_aero_max=max(aero.values()), excesso_aero_soma=sum(aero.values()),
        excesso_camber=geometria['camber'],
        excesso_faixas_max=max(faixas.values()), excesso_faixas_soma=sum(faixas.values()),
    )
    return dict(aerodinamica=aero, geometria=geometria, faixas=faixas, **resumo)


def chave_classificacao(candidato):
    """Menor é preferido; arredondamento a 12 casas evita decidir por ruído."""
    campos = ('excesso_aero_max', 'excesso_aero_soma', 'excesso_camber',
              'excesso_faixas_max', 'excesso_faixas_soma', 'afastamento_psi_relativo')
    return tuple(round(candidato[k], 12) for k in campos) + (candidato['n_estagios'],)


def detalhar_criterios(modelo, radial, perfis, compressor, criterios):
    """Metadados para interpretar os índices, sem participar da classificação.

    Para faixas, escolhe a maior distância assinada à faixa. Quando todos os
    valores estão dentro dela, isso identifica o extremo mais próximo de uma
    borda. Limites inferiores usam o mínimo; superiores usam o máximo.
    """
    def amostras(campo, fileira=None, posicao=None, incluir_radial=True):
        pontos = []
        if incluir_radial:
            for i, secoes in enumerate(getattr(radial, campo)):
                for secao, valor in secoes.items():
                    pontos.append(dict(valor=valor, localizacao=dict(
                        modelo='radial', estagio=i+1, secao=secao,
                        fileira=fileira, posicao=posicao)))
        campo_meanline = 'grau_reacao' if campo == 'R_c' else campo
        for i, valor in enumerate(getattr(modelo, campo_meanline)):
            pontos.append(dict(valor=valor, localizacao=dict(
                modelo='meanline', estagio=i+1, secao=None,
                fileira=fileira, posicao=posicao)))
        return pontos

    detalhes = []

    def registrar(grupo, criterio, pontos, inferior=None, superior=None, unidade='adimensional'):
        if inferior is None:
            avaliar = lambda p: p['valor'] - superior
        elif superior is None:
            avaliar = lambda p: inferior - p['valor']
        else:
            avaliar = lambda p: max(inferior-p['valor'], p['valor']-superior)
        extremo = max(pontos, key=avaliar)
        detalhes.append(dict(grupo=grupo, criterio=criterio,
                             valor=float(extremo['valor']), unidade=unidade,
                             limite_inferior=inferior, limite_superior=superior,
                             localizacao=extremo['localizacao'],
                             excesso_normalizado=criterios[grupo][criterio]))

    reacoes = amostras('R_c', posicao='Reação do estágio')
    registrar('aerodinamica', 'reacao_negativa', reacoes, inferior=dc.REACAO_MIN)
    if compressor:
        registrar('aerodinamica', 'Mach_relativo',
                  amostras('M1R', 'rotor', 'Entrada · estação local 1'), superior=dc.MACH_SONICO)
        registrar('aerodinamica', 'DF_rotor',
                  amostras('DF_rotor', 'rotor', 'Estações locais 1 → 2'), superior=dc.DF_MAX)
        registrar('aerodinamica', 'DF_estator',
                  amostras('DF_estator', 'estator', 'Estações locais 2 → 3'), superior=dc.DF_MAX)
        faixa_psi, faixa_reacao, limite_camber = dc.limites_componente(True)
        reacoes_faixa = amostras('R_c', posicao='Reação do estágio', incluir_radial=False)
    else:
        registrar('aerodinamica', 'reacao_acima_de_um', reacoes, superior=dc.REACAO_MAX_TURBINA)
        registrar('aerodinamica', 'Mach_relativo',
                  amostras('M3R', 'rotor', 'Saída · estação local 3'), superior=dc.MACH_SONICO)
        registrar('aerodinamica', 'Mach_bocal',
                  amostras('M2', 'bocal', 'Saída · estação local 2'), superior=dc.MACH_BOCAL_TURBINA)
        faixa_psi, faixa_reacao, limite_camber = dc.limites_componente(False)
        reacoes_faixa = reacoes
    cambers = [dict(valor=abs(perfil.theta_final), localizacao=dict(
        modelo='perfil', estagio=int(estagio), secao=secao, fileira=fileira,
        posicao='Câmber metálico em módulo'))
        for estagio, secoes in perfis.items()
        for secao, fileiras in secoes.items()
        for fileira, perfil in fileiras.items()]
    registrar('geometria', 'camber', cambers, superior=limite_camber, unidade='°')
    registrar('faixas', 'psi', [dict(valor=modelo.psi_efetivo, localizacao=dict(
        modelo='meanline', estagio=None, secao=None, fileira=None,
        posicao='Carga uniforme em todos os estágios'))], *faixa_psi)
    registrar('faixas', 'reacao', reacoes_faixa, *faixa_reacao)
    if not compressor:
        registrar('faixas', 'swirl_escape', [dict(valor=abs(modelo.v3[-1]/modelo.U),
            localizacao=dict(modelo='meanline', estagio=modelo.n_estagios,
                             secao=None, fileira='rotor', posicao='Escape · estação local 3'))], superior=dc.SWIRL_ESCAPE_MAX)
    return detalhes


def selecionar_estagios(modelo, componente):
    """Substitui o estado do objeto pela solução escolhida, só no modo automático."""
    compressor = componente == 'Compressor'
    from engine.aero.radial_compressor_4_main import RadialCompressor
    from engine.aero.radial_turbina_3_main import RadialTurbina
    from engine.geometry.airfoil4 import gerar_perfis_compressor, gerar_perfis_turbina
    radial_cls = RadialCompressor if compressor else RadialTurbina
    gerar = gerar_perfis_compressor if compressor else gerar_perfis_turbina
    entrada = modelo._entrada_selecao
    estimativa, psi_pedido = modelo.n_estagios_estimado, modelo.psi
    registros, solucoes = [], {}
    for n in vizinhos(estimativa):
        registro = dict(n_estagios=n, calculavel=False, selecionado=False)
        try:
            psi = modelo.delta_Tt_total * modelo.cp / (n * modelo.U**2)
            kwargs = {**entrada, 'n_estagios': n, 'psi': psi}
            with contextlib.redirect_stdout(io.StringIO()):
                candidato = type(modelo)(**kwargs)
            # Não há recursão: o candidato é calculado com n e psi explícitos.
            stdout_meanline = io.StringIO()
            with contextlib.redirect_stdout(stdout_meanline):
                candidato.resolver()
            alvo_T = modelo.T02r_alvo if compressor else entrada['ciclo'].T04r
            alvo_P = modelo.P02_alvo if compressor else entrada['ciclo'].P04
            if not (math.isclose(candidato.Tt_saida[-1], alvo_T, rel_tol=dc.COINCIDENCIA_RTOL, abs_tol=dc.COINCIDENCIA_ATOL)
                    and math.isclose(candidato.Pt_saida[-1], alvo_P, rel_tol=dc.COINCIDENCIA_RTOL, abs_tol=dc.COINCIDENCIA_ATOL)):
                raise ValueError("Candidato não fechou temperatura/pressão com o alvo do ciclo.")
            with contextlib.redirect_stdout(io.StringIO()):
                radial = radial_cls(candidato, n_secoes=modelo.n_secoes_avaliacao)
                radial.resolver()
                perfis = gerar(radial)
            criterios = avaliar_criterios(candidato, radial, perfis, compressor)
            registro.update(calculavel=True, psi_efetivo=psi,
                            afastamento_psi_relativo=abs(psi/psi_pedido-1.),
                            criterios=criterios,
                            residuo_T_K=candidato.Tt_saida[-1]-alvo_T,
                            residuo_P_Pa=candidato.Pt_saida[-1]-alvo_P,
                            **{k:v for k,v in criterios.items() if k.startswith('excesso_')})
            registro['atende_criterios_comparados'] = all(
                registro[k] <= 1e-12 for k in ('excesso_aero_max', 'excesso_camber', 'excesso_faixas_max'))
            registro['detalhes_criterios'] = detalhar_criterios(candidato, radial, perfis, compressor, criterios)
            solucoes[n] = candidato, stdout_meanline.getvalue()
        except (ValueError, RuntimeError, ZeroDivisionError, OverflowError) as erro:
            registro['motivo_rejeicao'] = str(erro)
        registros.append(registro)
    calculaveis = [r for r in registros if r['calculavel']]
    if not calculaveis:
        detalhes = '; '.join(f"{r['n_estagios']} estágio(s): {r['motivo_rejeicao']}" for r in registros)
        raise ValueError(f"Nenhum candidato automático calculável em {componente}. {detalhes}")
    escolhido = min(calculaveis, key=chave_classificacao)
    escolhido['selecionado'] = True
    vencedor, texto = solucoes[escolhido['n_estagios']]
    if len(calculaveis) == 1:
        motivo = 'Único candidato calculável entre os vizinhos avaliados.'
    else:
        outro = next(r for r in calculaveis if r is not escolhido)
        nomes = ('maior excesso aerodinâmico', 'soma dos excessos aerodinâmicos por família',
                 'excesso de câmber', 'maior excesso nas faixas comparativas',
                 'soma dos excessos nas faixas comparativas', 'afastamento do ψ solicitado',
                 'menor número de estágios no desempate')
        indice = next(i for i,(a,b) in enumerate(zip(chave_classificacao(escolhido), chave_classificacao(outro))) if a != b)
        motivo = f'Preferido pelo critério: {nomes[indice]}.'
    selecao = dict(politica='vizinhos_criterios_v1', componente=componente,
                   estimativa=estimativa, n_secoes=modelo.n_secoes_avaliacao,
                   candidatos=registros, escolhido=escolhido['n_estagios'], justificativa=motivo,
                   ressalva='Seleção comparativa segundo os critérios implementados; não certifica viabilidade física.')
    modelo.__dict__.update(vencedor.__dict__)
    modelo._entrada_selecao = entrada
    modelo.psi = psi_pedido
    modelo.n_estagios_estimado = estimativa
    modelo.calculo_automatico = True
    modelo.selecao_estagios = selecao
    # Só o meanline escolhido emite suas mensagens; radial/perfis serão executados
    # normalmente pelo chamador, sem avisos dos candidatos rejeitados na contagem.
    faixa = dc.PSI_COMP if compressor else dc.PSI_TURB
    if not faixa[0] <= modelo.psi_efetivo <= faixa[1]:
        print(f"AVISO: ψ = {modelo.psi_efetivo:.3f} está fora da faixa típica [{faixa[0]}, {faixa[1]}].")
    print(texto, end='')
