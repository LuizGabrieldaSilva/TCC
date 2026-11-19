# Cubo esquemático na montagem 3D

Implementação iniciada em 16/11/2026; verificação concluída em 17/11/2026.

## Apresentação

Na vista **Componente completo**, a opção **Mostrar cubo simplificado** vem ativada. A transparência pode variar entre 0% e 90%. Após mudar uma opção, clicar em **Gerar ou atualizar montagem 3D**. Nas vistas de uma pá ou um estágio, o cubo não é apresentado.

A superfície é cinza e acompanha os raios de cubo já calculados. Mantém o raio constante sob a extensão axial de cada raiz; somente nos vãos entre fileiras faz uma ligação linear. Usa as coordenadas axiais reais das raízes, sem adotar a estimativa conservadora `z_final` como bordo da pá. A vista por setor recorta também a superfície, permitindo enxergar o interior.

É uma superfície de referência, aberta nas extremidades e nas bordas do setor: não é um sólido estrutural nem um único corpo girante. Rotor gira; estatores e bocais são estacionários. As conexões mecânicas, discos e fixações não estão representados. A interpolação nos vãos é uma convenção visual, sem cálculo adicional de escoamento.

Nenhuma coordenada de pá, fórmula, parâmetro ou resultado físico foi alterado. O cubo não entra nas exportações DXF. Apenas `engine/webapp/assembly_3d.py` foi modificado no código da aplicação.

## Verificação

Executado de `NEW`:

```powershell
python ../checkpoints/cubo_esquematico_2026-11-16/verificar.py
```

Os resultados reais salvos dos casos manual e automático foram reutilizados. Foram conferidos:

- Coincidência entre o raio da superfície e a distância ao eixo de todos os pontos das raízes, com tolerância absoluta de 1e-12 m.
- Índices da malha e raios preservados nos setores de 90°, 180° e 360°.
- Traços das pás idênticos com e sem o cubo e resultados de origem imutáveis.
- Controles no AppTest: opção apenas no componente completo, geração com e sem cubo, transparência e invalidação da vista ao mudar parâmetros, incluindo troca entre compressor e turbina.

Os testes passaram. As imagens auxiliares `comp.png` e `turb.png`, produzidas a partir das mesmas malhas, foram inspecionadas visualmente. Não foi feita nova inspeção do WebGL no navegador nesta alteração; a aparência final será avaliada pelo autor na interface.

## Checkpoint e retorno

`checkpoints/cubo_esquematico_2026-11-16/` contém o arquivo anterior, manifesto SHA256, verificador, resultados e imagens auxiliares. A integridade da cópia foi conferida.

Para retornar, copiar `NEW/engine/webapp/assembly_3d.py` dessa pasta sobre o arquivo correspondente do projeto. Depois recarregar a interface e gerar novamente a montagem; o arquivo restaurado desconsidera a vista preparada com o cubo.
