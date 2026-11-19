"""Produtos completos e congelados; cp equivalente constante por execução.

NASA/TP-2002-211556, Eq.1 p.2; CO2 p.85, H2O p.131, N2 p.156,
O2 p.166. Coeficientes a1..a7 conferidos contra o PDF local.
Entalpias SENSÍVEIS relativas a 298.15 K: não somar entalpias de formação
ao PCI. Não é solver de equilíbrio, dissociação, cinética ou emissões.
"""
import json
import math
from functools import lru_cache
from pathlib import Path

RU = 8.31446261815324  # J/(mol K), valor moderno
T_REF = 298.15
M = {'CO2':.0440095,'H2O':.01801528,'O2':.0319988,'N2':.0280134,'Ar':.039948}
AR_MOLAR = {'N2':.78084,'O2':.209795,'Ar':.009365}  # seco, normalizado; CO2-traço omitido
M_AR = sum(z*M[s] for s,z in AR_MOLAR.items())
R_AR = RU/M_AR
COMBUSTIVEIS = {'JP-4':42.8e6,'JP-8':43.2e6,'gas_natural':50.e6,'diesel':42.5e6}
COMPOSICOES = {
    'JP-4': dict(C=1.,H=1.94,formula='CH1,94',fonte='NASA Glenn, p.278 (PDF 286): representação elementar de JP-4.'),
    'JP-8': dict(C=12.,H=23.,formula='C12H23',fonte='Hipótese: representação Jet-A de NASA Glenn, p.279 (PDF 287), usada como substituto elementar de JP-8; aditivos omitidos. NIST pub_id=920223 distingue JP-8/Jet A-1 e Jet A.'),
    'gas_natural': dict(C=1.,H=4.,formula='CH4',fonte='Metano puro, NASA Glenn p.83 (PDF 91); simplifica gás natural real.'),
    'diesel': dict(C=12.,H=23.,formula='C12H23',fonte='Diesel mineral representativo C12H23: NASA NTRS 20240010989, p.31. Não representa lote, biodiesel ou contaminantes.'),
}

def positivo(nome,v):
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0:
        raise ValueError(f'{nome} deve ser positivo e finito.')

@lru_cache(maxsize=2)
def coeficientes(alta):
    nome='glenn_1000_6000.json' if alta else 'glenn_200_1000.json'
    return json.loads(Path(__file__).with_name(nome).read_text(encoding='utf-8'))

def cp_molar(especie,T):
    if not math.isfinite(T) or not 200<=T<=6000:
        raise ValueError('Coeficientes da mistura exigem 200 ≤ T ≤ 6000 K.')
    if especie=='Ar':return 2.5*RU  # gás ideal monoatômico
    a=coeficientes(T>1000)[especie]
    return RU*(a['a1']/T**2+a['a2']/T+a['a3']+a['a4']*T+a['a5']*T**2+a['a6']*T**3+a['a7']*T**4)

def delta_h_molar(especie,Ta,Tb):
    cp_molar(especie,Ta);cp_molar(especie,Tb)
    if Ta==Tb:return 0.
    if Ta>Tb:return -delta_h_molar(especie,Tb,Ta)
    if Ta<1000<Tb:return delta_h_molar(especie,Ta,1000)+delta_h_molar(especie,1000,Tb)
    if especie=='Ar':return 2.5*RU*(Tb-Ta)
    a=coeficientes(Ta>=1000)[especie]
    return RU*(a['a1']*(1/Ta-1/Tb)+a['a2']*math.log(Tb/Ta)+sum(a['a'+str(j)]*(Tb**(j-2)-Ta**(j-2))/(j-2) for j in range(3,8)))

def massa_combustivel(nome):
    c=COMPOSICOES[nome]
    return c['C']*.0120107+c['H']*.00100794

def estequiometria(nome):
    c=COMPOSICOES[nome];a=c['C']+c['H']/4
    return massa_combustivel(nome)/(a*M_AR/AR_MOLAR['O2'])

def produtos(nome,f):
    positivo('f',f)
    if nome not in COMPOSICOES:raise ValueError('Combustível sem composição definida.')
    fst=estequiometria(nome)
    if f>fst*(1+1e-12):raise ValueError('Mistura rica: produtos completos com O2 excedente exigem f ≤ f_stoich.')
    c=COMPOSICOES[nome];a=c['C']+c['H']/4;lam=fst/f
    n={'CO2':c['C'],'H2O':c['H']/2,'O2':max(0.,a*(lam-1)),
       'N2':a*lam*AR_MOLAR['N2']/AR_MOLAR['O2'],'Ar':a*lam*AR_MOLAR['Ar']/AR_MOLAR['O2']}
    total=sum(n.values());massa=sum(n[s]*M[s] for s in n)
    z={s:v/total for s,v in n.items()};Y={s:n[s]*M[s]/massa for s in n}
    return dict(moles_por_mol_combustivel=n,fracoes_molares=z,fracoes_massicas=Y,
                M_kg_mol=massa/total,R_J_kg_K=RU/(massa/total),lambda_ar=lam,
                excesso_ar_pct=100*(lam-1),f_stoich=fst)

def propriedades(nome,f,TIT):
    p=produtos(nome,f);Y=p['fracoes_massicas']
    h=sum(Y[s]*delta_h_molar(s,T_REF,TIT)/M[s] for s in Y)
    cp=h/(TIT-T_REF) if TIT!=T_REF else sum(Y[s]*cp_molar(s,TIT)/M[s] for s in Y)
    if cp<=p['R_J_kg_K']:raise ValueError('Mistura exige cp > R.')
    return dict(p,cp_J_kg_K=cp,k=cp/(cp-p['R_J_kg_K']),h_saida_J_kg=h,
                T_referencia_K=T_REF,T_limite_cp_K=TIT,
                metodo_cp='Integral de cp(T) de 298,15 K até TIT, dividida por TIT−298,15; constante por execução.',
                composicao_combustivel=dict(COMPOSICOES[nome]))

def resolver_mistura(nome,T02,TIT,cp_ar,eta_b=.99,PCI=None):
    if nome not in COMPOSICOES:raise ValueError('Combustível sem composição definida.')
    for n,v in [('T02',T02),('TIT',TIT),('cp_ar',cp_ar),('eta_b',eta_b)]:positivo(n,v)
    if eta_b>1 or TIT<=T02:raise ValueError('Mistura exige η_b ≤ 1 e TIT > T02.')
    cp_molar('N2',T02);cp_molar('N2',TIT)
    pci=COMBUSTIVEIS[nome] if PCI is None else PCI;positivo('PCI',pci)
    ha=cp_ar*(T02-T_REF)
    def residuo(f):return f*eta_b*pci-((1+f)*propriedades(nome,f,TIT)['h_saida_J_kg']-ha)
    lo,hi=1e-14,estequiometria(nome)
    if residuo(lo)>=0 or residuo(hi)<0:
        raise ValueError('Não há solução pobre/estequiométrica para TIT e propriedades informadas. Revise o caso; combustão rica não é modelada.')
    for _ in range(100):
        mid=(lo+hi)/2
        if residuo(mid)>0:hi=mid
        else:lo=mid
    f=(lo+hi)/2
    return dict(propriedades(nome,f,TIT),f=f,phi_eq=f/estequiometria(nome),
                residuo_energia_J_kg_ar=residuo(f),PCI_J_kg=pci,eta_b=eta_b)
