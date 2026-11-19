"""Comparações parciais com exemplos publicados, sem modificar os modelos.

Em NEW: python -m engine.estudos.verificar_exemplos_livros --saida resultado.json
As tolerâncias são de reprodução de números arredondados, não de projeto.
Não requer os PDFs para executar; dados e localizadores estão registrados aqui.
"""

import argparse
import contextlib
import io
import json
import math
from pathlib import Path
from types import SimpleNamespace


def executar():
    from engine.ciclo.CicloBrayton import CicloBrayton
    from engine.aero.annulus_geometry import raios_anular
    from engine.aero.radial_compressor_4_main import RadialCompressor
    from engine.aero.radial_turbina_3_main import RadialTurbina
    from engine.aero.reacao_turbina import reacao_estatica
    from engine.geometry.airfoil4 import gerar_perfil_pa
    from engine.combustor.Combustor_1D_2_main import Combustor1D
    from engine.diagnosticos import _plano

    linhas, observacoes = [], []

    def comparar(caso, grandeza, calculado, publicado, unidade, tolerancia, escopo):
        erro = calculado - publicado
        ok = math.isfinite(calculado) and abs(erro) <= tolerancia
        linhas.append(dict(caso=caso, grandeza=grandeza, calculado=calculado,
                           publicado=publicado, unidade=unidade, residuo=erro,
                           diferenca_pct=100 * erro / abs(publicado) if publicado else None,
                           tolerancia_absoluta=tolerancia, conforme=ok, escopo=escopo))

    # S, exemplo 2.1, pp. 74-76 / PDF 91-93: somente a compressão.
    # A eficiência publicada é isentrópica; a API recebe a politrópica.
    pi, k, eta_s = 4., 1.4, .85
    tau = 1 + (pi ** ((k - 1) / k) - 1) / eta_s
    eta_p = ((k - 1) / k) * math.log(pi) / math.log(tau)
    with contextlib.redirect_stdout(io.StringIO()):
        ciclo = CicloBrayton(T01=288., P01=1e5, r_compr=pi, TIT=1100.,
                            e_compr=eta_p, e_turb=.87, cp=1005., k=k)
        ciclo.resolver()
    comparar('S2.1', 'T02', ciclo.T02r, 452.7, 'K', .1,
             'Compressor de CicloBrayton; eficiência convertida. Sem recuperador/eixo real.')
    comparar('S2.1', 'eta isentrópica recuperada', ciclo.eta_compr, eta_s, '-', 1e-12,
             'Identidade da conversão; não é evidência externa adicional.')

    # S pp. 210-211 / PDF 227-228: área e anular de descarga.
    plano = _plano(452.5, 419e3, 150., 0., 20., 1005., 1.4)
    comparar('S_anular', 'Área', plano['area_m2'], .0440, 'm2', 1e-4,
             'Diagnóstico _plano; Tt/Pt/Cx/vazão publicados. R derivado de cp/k.')
    rh, rt, h = raios_anular(.0440, .1697)
    for nome, valor, alvo in [('Cubo', rh, .1491), ('Ponta', rt, .1903), ('Altura', h, .0413)]:
        comparar('S_anular', nome, valor, alvo, 'm', 5e-5,
                 'raios_anular com área publicada arredondada; raio médio aritmético.')

    # D exemplo 3.1 pp. 86-87 / PDF 97-98. A incidência 3° é aplicada
    # na preparação da entrada: 50-3=47°. A API continua usando i=0.
    perfil = gerar_perfil_pa(47., 30., 1 / .85, .05)
    comparar('D3.1', 'Desvio Carter', perfil.delta, 6.2, 'graus', .05,
             'gerar_perfil_pa: incidência externa, somente correlação de desvio.')
    comparar('D3.1', 'Câmber Carter', perfil.theta_final, 23.2, 'graus', .05,
             'gerar_perfil_pa: não reproduz perdas nem o escoamento da cascata.')

    # D exemplo 5.1(a), p.178 / PDF 187. Isola os helpers usados pelo
    # radial; não confere as perdas/pressões das partes b/c do exemplo.
    # R=287.15 e k=1.4 fornecidos; cp coerente pela relação do gás ideal.
    gas = SimpleNamespace(k=1.4, R=287.15, cp=287.15 * 1.4 / .4)
    m_abs = .9 * math.cos(math.radians(45))
    t = 288 / (1 + .2 * m_abs ** 2)
    u = m_abs * math.sqrt(gas.k * gas.R * t)
    w = math.hypot(u, u)
    comparar('D5.1a', 'U (preparação analítica)', u, 208.3, 'm/s', .1,
             'Preparação externa a partir de Mrel e beta do livro; não solver de U.')
    comparar('D5.1a', 'Mach absoluto helper', RadialTurbina._mach(gas, u, 288), .6364, '-', 1e-4,
             'Helper de produção, temperatura total absoluta.')
    comparar('D5.1a', 'Mach relativo helper', RadialTurbina._mach_relativo(gas, w, u, 288), .9, '-', 1e-12,
             'Helper de produção; verifica uso da temperatura estática correta.')

    # D exemplo 6.1 pp.219-221 / PDF 228-230: fixture de meanline para
    # acionar o resolver radial real, sem fingir um ciclo compressível.
    omega, rh, rt = 2 * math.pi * 6000 / 60, .45, .5
    rm = (rh + rt) / 2
    cx = omega * rt / (math.tan(math.radians(60)) + math.tan(math.radians(30)))
    v1_tip, v2_tip = cx * math.tan(math.radians(30)), cx * math.tan(math.radians(60))
    fixture = SimpleNamespace(
        omega=omega, u_ax=cx, cp=1005., k=1.4, R=1005. * .4 / 1.4,
        n_estagios=1, Tt_entrada=[500.], Tt_saida=[550.],
        r_hub_est=[rh], r_tip_est=[rt], r_mean=rm,
        v1=[v1_tip * rt / rm], v2=[v2_tip * rt / rm],
        sigma_rotor=[1.], sigma_estator=[1.], Z_rotor=[60], Z_estator=[60],
        corda_rotor=[2 * math.pi * rm / 60], corda_estator=[2 * math.pi * rm / 60],
    )
    radial = RadialCompressor(fixture, n_secoes=3)
    with contextlib.redirect_stdout(io.StringIO()):
        radial.resolver()
    massa = math.pi * (rt ** 2 - rh ** 2) * 1.5 * cx
    trabalho = radial.U_r[0]['tip'] * (radial.v2[0]['tip'] - radial.v1[0]['tip'])
    comparar('D6.1', 'Cx (preparação analítica)', cx, 136., 'm/s', .1,
             'Preparação externa dos triângulos da ponta.')
    comparar('D6.1', 'Vazão (pós-processamento)', massa, 30.4, 'kg/s', .1,
             'Continuidade externa com densidade CONSTANTE publicada 1.5 kg/m3.')
    comparar('D6.1', 'Potência absorvida', massa * trabalho / 1e6, 1.5, 'MW', .01,
             'Euler com saída efetiva de RadialCompressor, vezes vazão externa.')
    for campo, alvo in [('alpha1', 32.75), ('beta1', 55.15), ('alpha2', 62.6), ('beta2', 8.64)]:
        comparar('D6.1', campo + ' hub', getattr(radial, campo)[0]['hub'], alvo, 'graus', .1,
                 'Saída efetiva de RadialCompressor.resolver.')
    comparar('D6.1', 'Reação hub', radial.R_c[0]['hub'], .382, '-', .001,
             'Saída efetiva radial; referência publicada arredondada.')
    observacoes.append('D6.1: Tt=500/550 K e corda/Z são preenchimentos da fixture, não dados do livro. '
                       'Mach, DF, perfis e termodinâmica dessa fixture não são benchmarks. '
                       'Densidade constante não é fornecida ao solver compressível meanline.')

    # D exemplo 4.2 pp.138-139 / PDF148-149: cinco estágios repetitivos.
    # Livro usa módulos de ângulos opostos. Convenção assinada do projeto:
    # Ctheta1=Ctheta3<0 e Ctheta2>0. Não reproduz primeiro bocal axial do app.
    rm, omega = .46, 5600 * 2 * math.pi / 60
    u = rm * omega
    trabalho = 6.64e6 / (15 * 5)
    psi = trabalho / u ** 2
    phi = psi / (math.tan(math.radians(70)) + math.tan(math.radians(15)))
    cx = phi * u
    ct1 = -cx * math.tan(math.radians(15))
    ct2 = cx * math.tan(math.radians(70))
    c1, c2 = math.hypot(cx, ct1), math.hypot(cx, ct2)
    reacao, _, _ = reacao_estatica(trabalho, c1, c2, c1)
    plano = _plano(1200., 213e3, cx, ct1, 15., 1150., 1.333)
    rh, rt, h = raios_anular(plano['area_m2'], rm)
    for nome, valor, alvo, unidade, tol in [
        ('U (preparação)', u, 269.8, 'm/s', .1),
        ('psi (preparação)', psi, 1.217, '-', .001),
        ('phi (preparação)', phi, .403, '-', .001),
        ('Reação estática', reacao, .5, '-', .002),
        ('Mach entrada', plano['M'], .166, '-', .001),
        ('Área entrada', plano['area_m2'], .227, 'm2', .001),
        ('Altura entrada', h, .0785, 'm', .0005),
        ('HTR entrada', rh / rt, .843, '-', .002),
    ]:
        comparar('D4.2', nome, valor, alvo, unidade, tol,
                 'Preparação analítica + helpers reacao_estatica/_plano/raios_anular; não turbina completa.')
    observacoes.append('D4.2: cp/k implicam R=287.284321... em vez de 287.2 publicado; '
                       'diferença pequena de arredondamento. Página139 mostra H=0.0785m e em seguida78.2mm; '
                       'a referência adotada é0.0785m, coerente com a equação, não a conversão contraditória.')

    # M p.822 / PDF887: comprimento por escala de projeto semelhante JT9D.
    def combustor(Tin, Tout, cp, eta=1., pressao=350 * 6894.757293168):
        # Ciclo auxiliar resolvido para fornecer Tin/P02/TIT à API. Seus
        # demais estados NÃO reproduzem o motor do livro e não são comparados.
        razao = (Tin / 300.) ** (1.4 * .85 / .4)
        with contextlib.redirect_stdout(io.StringIO()):
            entrada = CicloBrayton(T01=300., P01=pressao / razao, r_compr=razao,
                                  TIT=Tout, TIT_máx=Tout, e_compr=.85, cp=cp, k=1.4)
            entrada.resolver()
            entrada.vazão_mássica_desejada(15.)
            b = Combustor1D(entrada, combustivel='JP-4', eta_b=eta)
            b.resolver()
        return b
    b = combustor(600., 2900 * 5 / 9, 1005., .99)
    comparar('M_escala', 'Comprimento', b.L_comb / .0254, 16., 'in', .025,
             'Combustor1D.resolver: somente escala; Rankine para K sem deslocamento.')

    # M p.816 / PDF881: hipótese diferente, comparação EXPLICATIVA.
    # A equação externa não é usada para mudar/mascarar a saída do código.
    b = combustor(653., 1670., 1005., pressao=800e3)
    f_distintos = (1235 * 1670 - 1004 * 653) / (42.8e6 - 1235 * 1670)
    comparar('M_balanço', 'f com cp distintos (equação externa)', f_distintos, .0346, 'kg/kg', .0001,
             'Reprodução externa da equação publicada, NÃO resultado de Combustor1D.')
    diferenca_hipotese = dict(
        caso='M_balanço', pagina_impressa=816, pagina_pdf=881,
        cp_ar_livro=1004., cp_gases_livro=1235., cp_unico_modelo=1005.,
        T_entrada_K=653., T_saida_K=1670., eta_b=1., PCI_Jkg=42.8e6,
        f_livro=.0346, f_equacao_livro=f_distintos, f_modelo=b.f,
        phi_livro=.519, phi_modelo=b.phi_eq,
        diferenca_f_pct=100 * (b.f - .0346) / .0346,
        classificacao='Diferença de hipótese quantificada; não exigir coincidência.',
    )
    return dict(comparacoes=linhas, aprovadas=sum(v['conforme'] for v in linhas),
                total=len(linhas), diferenca_hipotese_combustor=diferenca_hipotese,
                conversao_eta_compressor=eta_p, observacoes=observacoes,
                ressalva='Concordância parcial com números publicados não valida um motor real nem todos os cinco livros.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--saida', type=Path, required=True)
    args = parser.parse_args()
    resultado = executar()
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    print(f"Comparações dentro das tolerâncias: {resultado['aprovadas']}/{resultado['total']}")
    print('Diferença de hipótese do combustor registrada separadamente.')
    raise SystemExit(0 if resultado['aprovadas'] == resultado['total'] else 1)
