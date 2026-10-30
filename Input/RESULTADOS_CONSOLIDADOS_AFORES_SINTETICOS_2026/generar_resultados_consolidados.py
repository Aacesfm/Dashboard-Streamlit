#!/usr/bin/env python3
"""Genera resultados_consolidados 55 columnas a partir de inputs sintéticos.
Las salidas *_web SON HIPÓTESIS simuladas; no se consultó ningún sitio web.
No estima derechos pensionarios ni reproduce algoritmos comerciales.
Sólo stdlib, determinista y replicable.
"""
from __future__ import annotations
import csv, json, math, zipfile
from pathlib import Path
from collections import Counter, defaultdict
from datetime import date

ROOT=Path('/mnt/data')
INPUT=ROOT/'inputs_afore_sinteticos_2026'
OUT=ROOT/'resultados_consolidados_sinteticos_2026'
OUT.mkdir(parents=True,exist_ok=True)
CUT=date(2026,10,29)

# Los 55 nombres reproducen literalmente la tabla de las seis fotos.
FIELDS=[
'AFORE','REGIMEN','id_cliente','nombre','ap_paterno','ap_materno','age','f_nacim',
'genero','entidad','nss','num_issste','curp','correo','anios_cotizados','anio_fil',
'sem_cot','salario_mensual','saldo_rcv','saldo_ahorro_solidario',
'porcentaje_ahorro_solidario','saldo_bono_pension','saldo_av','saldo_vivienda',
'av_mensual','regimen_estimado','ley_bandera','escenario_estimado','nombre_completo',
'Pension_web','sal_cot_web','saldo_rcv_web','disposicion_recursos_web',
'pension_edad_mas_1_web','pension_edad_mas_2_web','edad_retiro_calculo',
'observaciones','id_checkpoint','ARCHIVO_ORIGEN','FILA_ORIGEN',
 'tasa_remplazo_web','tasa_rendimiento_web','densidad_cot_web',
'saldo_inicial_capturado','saldo_inicial_incluye_av','saldo_acumulado_web',
'estado','pension_con_av_web','saldo_total_web',
'saldo_total_con_av_mensual_web','saldo_acumulado_con_av_web',
'modalidad_web','modalidad_con_av_web','rcv_proy_web','rcv_av_proy_web'
]
assert len(FIELDS)==55 and len(set(FIELDS))==55

BASE_FIELDS=FIELDS[2:29]  # no, son selectivas; las extras se obtienen en source direct
SRC_NAMES=['BANAMEX_INPUT_BASE.csv','XXI_BANORTE_INPUT.csv','COPPEL_INPUT.csv',
           'SURA_INPUT.csv','PROFUTURO_INPUT.csv','INVERCAP_INPUT.csv',
           'PRINCIPAL_INPUT.csv']
LABELS={'BANAMEX_INPUT_BASE.csv':'Banamex', 'XXI_BANORTE_INPUT.csv':'XXI Banorte',
        'COPPEL_INPUT.csv':'Coppel','SURA_INPUT.csv':'SURA',
        'PROFUTURO_INPUT.csv':'Profuturo','INVERCAP_INPUT.csv':'Invercap',
        'PRINCIPAL_INPUT.csv':'Principal'}
# Rendimientos REALES NETOS anuales elegidos exclusivamente para una prueba de sensibilidad.
# Son FICTICIOS; ninguna tasa expresa el desempeño real de la administradora.
ASSUMED_RETURN={'Banamex':4.50,'XXI Banorte':4.35,'Coppel':4.70,'SURA':4.40,
                'Profuturo':4.65,'Invercap':4.25,'Principal':4.55}
COLMAP={'AFORE':'afore_evaluada','REGIMEN':'regimen_estimado'}
for fld in FIELDS[2:29]:
    COLMAP[fld]=fld

def m(v):return f'{float(v):.2f}'
def f(x):return float(x or 0)
def read(path):
    with path.open(encoding='utf-8-sig',newline='') as fd:return list(csv.DictReader(fd))
def write(path,rows,fields=FIELDS):
    with path.open('w',encoding='utf-8-sig',newline='') as fd:
        writer=csv.DictWriter(fd,fieldnames=fields,extrasaction='ignore')
        writer.writeheader();writer.writerows(rows)

def future_value(principal,contrib_monthly,rate_percent,years):
    rate=rate_percent/100
    growth=(1+rate)**years
    rm=(1+rate)**(1/12)-1
    deposits=contrib_monthly*((growth-1)/rm) if rm else contrib_monthly*years*12
    return principal*growth+deposits

def retirement_age(row):
    # Input projection to age 65 if younger; otherwise as-of-date retirement at current age.
    age=int(row['age'])
    return max(65,age)

def sim(row,afore,retire_age,add_monthly_av=False):
    regime=row['regimen_estimado'];age=int(row['age'])
    yrs=max(0,retire_age-age)
    r=ASSUMED_RETURN[afore]
    wage=f(row['salario_mensual'])
    rcv=f(row['saldo_rcv']);av=f(row['saldo_av'])
    solid=f(row['saldo_ahorro_solidario']);bono=f(row['saldo_bono_pension'])
    # tasas de aportación FICTICIAS, no porcentajes reglamentarios personalizados.
    contrib_rate={'IMSS73':0.075,'IMSS97':0.10,'ISSSTE':0.115}[regime]
    rcv_p=future_value(rcv,wage*contrib_rate,r,yrs)
    solid_p=future_value(solid,0,r,yrs)
    # El bono de ISSSTE se mantiene constante en poder adquisitivo dentro de esta prueba.
    bono_p=bono
    av_start_p=future_value(av,0,r,yrs)
    av_new_p=future_value(0,f(row['av_mensual']) if add_monthly_av else 0,r,yrs)
    total=rcv_p+solid_p+bono_p+av_start_p+av_new_p
    negative=row['escenario_estimado'].endswith('NEGATIVA_PENSION')
    if negative:
        pension=0.0
        modalidad='NEGATIVA_HIPOTETICA_NO_DICTAMEN'
    elif regime=='IMSS73':
        # Ilustración simple; la pensión Ley 73 no se deriva mecánicamente del saldo RCV.
        accrued=int(row['sem_cot']) + int(yrs*52)
        years_accrued=accrued/52
        base_factor=min(.80,.42+.010*max(0,years_accrued-10))
        age_factor=min(1.0,.75+.05*max(0,min(65,retire_age)-60))
        pension=wage*base_factor*age_factor
        if row['escenario_estimado']=='IMSS73_GARANTIZADA':
            pension=max(pension,6200.0) # piso de EJEMPLO, NO pensión mínima legal
        modalidad='PENSION_LEY_73_HIPOTETICA'
    else:
        # Capital dividido en un horizonte de extracción sintético (no cálculo actuarial).
        # Mayor edad => menor número de mensualidades restantes, sin valores oficiales.
        months=max(170,285-(retire_age-60)*5)
        pension=total/months
        if row['escenario_estimado']=='ISSSTE_PENSION_GARANTIZADA':
            pension=max(pension,6500.0)  # floor EJEMPLO, NO mínimo legal
        modalidad=('RENTA_VITALICIA_HIPOTETICA' if row['escenario_estimado']=='ISSSTE_RECURSOS_PROPIOS'
                   else 'RETIRO_PROGRAMADO_HIPOTETICO')
    return {'rcv':rcv_p,'av_start':av_start_p,'av_new':av_new_p,
            'solid':solid_p,'bono':bono_p,'total':total,
            'pension':pension,'modalidad':modalidad}

def convert(row,srcname,row_number):
    afore=row['afore_evaluada'];reg=row['regimen_estimado']
    assert afore==LABELS[srcname]
    out={key:row.get(input_key,'') for key,input_key in COLMAP.items()}
    out['nombre_completo']=' '.join([row['nombre'],row['ap_paterno'],row['ap_materno']]).strip()
    age=retirement_age(row)
    base=sim(row,afore,age,False)
    plus=sim(row,afore,age,True)
    next1=sim(row,afore,age+1,False)
    next2=sim(row,afore,age+2,False)
    r=ASSUMED_RETURN[afore]
    start=date(int(row['anio_fil']),1,1)
    elapsed_weeks=(CUT-start).days/7
    density=min(100,100*int(row['sem_cot'])/elapsed_weeks)
    wage=f(row['salario_mensual'])
    out.update({
        'Pension_web':m(base['pension']),
        'sal_cot_web':m(wage),
        'saldo_rcv_web':m(row['saldo_rcv']),
        # Dato ausente: no se inventa un derecho de disposición de recursos.
        'disposicion_recursos_web':'',
        'pension_edad_mas_1_web':m(next1['pension']),
        'pension_edad_mas_2_web':m(next2['pension']),
        'edad_retiro_calculo':str(age),
        'observaciones':('DATOS_100_POR_CIENTO_SINTETICOS; SALIDAS_WEB_NO_CONSULTADAS; '
                         'PENSION_MES_MXN_2026; TASA_REAL_FICTICIA; '
                         'DISPOSICION_RECURSOS_SIN_CALCULO; '
                         'ESCENARIOS_NO_SON_DICTAMENES'),
        'id_checkpoint':f'CKPT26-{afore.upper().replace(" ","_")}-{row["id_cliente"]}',
        'ARCHIVO_ORIGEN':srcname,
        'FILA_ORIGEN':str(row_number),
        'tasa_remplazo_web':m(100*base['pension']/wage) if wage else '',
        'tasa_rendimiento_web':m(r),
        'densidad_cot_web':m(density),
        'saldo_inicial_capturado':m(f(row['saldo_rcv'])+f(row['saldo_ahorro_solidario'])+f(row['saldo_bono_pension'])),
        'saldo_inicial_incluye_av':'0',
        'saldo_acumulado_web':m(base['total']),
        'estado':'SIMULADO_NO_CONSULTADO',
        'pension_con_av_web':m(plus['pension']),
        'saldo_total_web':m(base['total']),
        'saldo_total_con_av_mensual_web':m(plus['total']),
        'saldo_acumulado_con_av_web':m(plus['total']),
        'modalidad_web':base['modalidad'],
        'modalidad_con_av_web':plus['modalidad'],
        'rcv_proy_web':m(base['rcv']),
        # Nombre del esquema heredado: agrega AV actual y AV mensual, NO es saldo RCV contable estricto.
        'rcv_av_proy_web':m(plus['rcv']+plus['av_start']+plus['av_new'])
    })
    assert set(out)==set(FIELDS), (set(FIELDS)-set(out),set(out)-set(FIELDS))
    return out

all_rows=[];source_count={};per_regimen=defaultdict(Counter)
for src in SRC_NAMES:
    raw=read(INPUT/src)
    assert len(raw)==300 and Counter(r['regimen_estimado'] for r in raw)=={'IMSS73':100,'IMSS97':100,'ISSSTE':100}
    converted=[convert(row,src,idx) for idx,row in enumerate(raw,2)]
    file=(OUT/src.replace('_INPUT_BASE.csv','_RESULTADOS.csv').replace('_INPUT.csv','_RESULTADOS.csv'))
    write(file,converted)
    source_count[file.name]=len(converted)
    all_rows.extend(converted)
    per_regimen[LABELS[src]].update(r['REGIMEN'] for r in converted)
assert len(all_rows)==2100
write(OUT/'RESULTADOS_CONSOLIDADOS_7_AFORES.csv',all_rows)

# CONSAR no es AFORE ni calculadora. Archivo opcional para los sistemas que requieren
# un octavo "origen"; variables de salida web intencionalmente vacías.
ref_src=INPUT/'CONSAR_REFERENCIA_NO_OFICIAL.csv'
ref=[]
for i,row in enumerate(read(ref_src),2):
    item={key:row.get(input_key,'') for key,input_key in COLMAP.items()}
    item['AFORE']='CONSAR_NO_ES_AFORE'
    item['nombre_completo']=' '.join([row['nombre'],row['ap_paterno'],row['ap_materno']]).strip()
    item['id_checkpoint']=f'REF-CONSAR-{row["id_cliente"]}'
    item['ARCHIVO_ORIGEN']=ref_src.name
    item['FILA_ORIGEN']=str(i)
    item['estado']='REFERENCIA_NO_WEB_NO_OFICIAL'
    item['observaciones']='CONSAR_ES_REGULADOR; NO ES AFORE NI SIMULADOR; NO_HAY_SALIDAS_WEB'
    ref.append(item)
write(OUT/'CONSAR_REFERENCIA_SIN_RESULTADOS_WEB.csv',ref)
assert len(ref)==300

# La misma id_cliente se evalúa 7 veces con EXACTAMENTE los mismos 27 inputs visibles.
inputs_immutable=[key for key in FIELDS[2:29] if key not in ('AFORE','REGIMEN')]
by_client=defaultdict(list)
for row in all_rows:by_client[row['id_cliente']].append(row)
assert len(by_client)==300
for key,items in by_client.items():
    assert len(items)==7
    assert len({i['AFORE'] for i in items})==7
    for fld in inputs_immutable:
        assert len({i[fld] for i in items})==1,(key,fld)

comparison=[]
for client,items in by_client.items():
    bn=next(x for x in items if x['AFORE']=='Banamex')
    for alt in items:
        if alt['AFORE']=='Banamex':continue
        bp=f(bn['Pension_web']); ap=f(alt['Pension_web'])
        bs=f(bn['saldo_total_web']);as_=f(alt['saldo_total_web'])
        comparison.append({
            'id_cliente':client,'REGIMEN':alt['REGIMEN'],'escenario_estimado':alt['escenario_estimado'],
            'AFORE_COMPARADA':alt['AFORE'],'AFORE_BASE':'Banamex',
            'pension_banamex_sintetica_mxn_mes':m(bp),
            'pension_comparada_sintetica_mxn_mes':m(ap),
            'diferencia_pension_mxn_mes':m(ap-bp),
            'diferencia_pension_porcentaje':m((ap/bp-1)*100) if bp>0 else '',
            'saldo_banamex_sintetico_mxn':m(bs),
            'saldo_comparado_sintetico_mxn':m(as_),
            'diferencia_saldo_mxn':m(as_-bs),
            'diferencia_saldo_porcentaje':m((as_/bs-1)*100) if bs>0 else '',
            'nota':'VARIACIONES_UNICAMENTE_POR_TASAS_FICTICIAS; NO_DESEMPEÑO_REAL'
        })
compcols=list(comparison[0])
assert len(comparison)==1800
write(OUT/'COMPARACION_SINTETICA_VS_BANAMEX.csv',comparison,compcols)

# Reglas de validación contable, tasa y consistencia de escenarios.
errors=[]
for row in all_rows:
    ident=row['id_checkpoint'];s=row['escenario_estimado']
    def test(cond,msg):
        if not cond:errors.append((ident,msg))
    test(row['estado']=='SIMULADO_NO_CONSULTADO','estado')
    test(len(row)==55,'columns')
    test(0<=f(row['densidad_cot_web'])<=100,'density')
    test(0<=f(row['tasa_rendimiento_web'])<=25,'rate')
    test(row['Pension_web']==row['pension_con_av_web'] if row['REGIMEN']=='IMSS73' else f(row['pension_con_av_web'])>=f(row['Pension_web'])-0.02,'voluntary pension')
    test(f(row['saldo_total_con_av_mensual_web'])+0.02>=f(row['saldo_total_web']),'additional AV')
    test(abs(f(row['tasa_remplazo_web'])-100*f(row['Pension_web'])/f(row['salario_mensual']))<=0.015,'replace')
    test(abs(f(row['saldo_total_web'])-f(row['saldo_acumulado_web']))<0.01,'accumulated')
    test(abs(f(row['saldo_total_con_av_mensual_web'])-f(row['saldo_acumulado_con_av_web']))<0.01,'accumulated AV')
    test(f(row['rcv_av_proy_web'])+0.02>=f(row['rcv_proy_web']),'rcv AV')
    test(row['disposicion_recursos_web']=='','unverified disposition')
    test(f(row['Pension_web'])>=0 and f(row['pension_con_av_web'])>=0,'pensions positive')
    if s.endswith('NEGATIVA_PENSION'):
        test(f(row['Pension_web'])==0 and f(row['pension_con_av_web'])==0,'negative')
        test(row['modalidad_web']=='NEGATIVA_HIPOTETICA_NO_DICTAMEN','negative modality')
    if f(row['av_mensual'])==0:
        test(abs(f(row['saldo_total_web'])-f(row['saldo_total_con_av_mensual_web']))<0.02,'zero additional AV')
assert not errors,errors[:10]

# Diccionario fiel a las fotos: "anulable" se transcribe tal como aparece,
# interpretándolo como numérico nullable en las columnas simuladas.
DICT=[
('AFORE','Categórico','AFORE o simulador web al que corresponde el resultado.'),
('REGIMEN','Categórico','Régimen pensionario bajo el cual se procesó el caso.'),
('id_cliente','Texto','Identificador único del cliente.'),
('nombre','Texto','Nombre o nombres del cliente.'),
('ap_paterno','Texto','Apellido paterno.'),
('ap_materno','Texto','Apellido materno.'),
('age','Entero anulable','Edad del cliente.'),
('f_nacim','Fecha anulable','Fecha de nacimiento.'),
('genero','Categórico','Género codificado del cliente.'),
('entidad','Categórico','Código de la entidad federativa.'),
('nss','Texto','Número de Seguridad Social. Debe manejarse como texto.'),
('num_issste','Texto','Número de identificación ISSSTE. Debe manejarse como texto.'),
('curp','Texto','CURP del cliente.'),
('correo','Texto','Correo electrónico.'),
('anios_cotizados','Entero','Años de cotización capturados.'),
('anio_fil','Entero o categórico anulable','Año de afiliación al sistema pensionario.'),
('sem_cot','Entero anulable','Semanas cotizadas capturadas.'),
('salario_mensual','Decimal monetario','Salario mensual utilizado como input.'),
('saldo_rcv','Decimal monetario','Saldo inicial de Retiro, Cesantía y Vejez.'),
('saldo_ahorro_solidario','Decimal monetario','Saldo inicial de ahorro solidario.'),
('porcentaje_ahorro_solidario','Porcentaje','Porcentaje de ahorro solidario capturado.'),
('saldo_bono_pension','Decimal monetario','Saldo o valor del bono pensionario.'),
('saldo_av','Decimal monetario','Saldo inicial de ahorro voluntario.'),
('saldo_vivienda','Decimal monetario','Saldo inicial de vivienda.'),
('av_mensual','Decimal monetario','Aportación voluntaria mensual.'),
('regimen_estimado','Categórico','Régimen pensionario estimado en el input.'),
('ley_bandera','Categórico','Ley pensionaria asignada al cliente.'),
('escenario_estimado','Categórico','Escenario pensionario esperado para el caso.'),
('nombre_completo','Texto','Nombre completo formado a partir de nombres y apellidos.'),
('Pension_web','Decimal monetario anulable','Pensión mensual obtenida del simulador web.'),
('sal_cot_web','Decimal monetario anulable','Salario de cotización mostrado o reconocido por el simulador.'),
('saldo_rcv_web','Decimal monetario anulable','Saldo RCV mostrado o utilizado por el simulador.'),
('disposicion_recursos_web','Decimal monetario anulable','Recursos que el simulador indica que pueden disponerse.'),
('pension_edad_mas_1_web','Decimal monetario anulable','Pensión estimada al calcular el retiro un año después.'),
('pension_edad_mas_2_web','Decimal monetario anulable','Pensión estimada al calcular el retiro dos años después.'),
('edad_retiro_calculo','Entero','Edad de retiro utilizada durante la consulta.'),
('observaciones','Texto','Resultado, incidencia, rechazo u observación del procesamiento.'),
('id_checkpoint','Texto','Identificador utilizado para seguimiento y recuperación del proceso.'),
('ARCHIVO_ORIGEN','Texto','Archivo del que provino originalmente el registro.'),
('FILA_ORIGEN','Entero','Número de fila del registro en el archivo de origen.'),
('tasa_remplazo_web','Porcentaje anulable','Tasa de reemplazo obtenida del simulador web.'),
('tasa_rendimiento_web','Porcentaje anulable','Tasa de rendimiento utilizada o mostrada por el simulador.'),
('densidad_cot_web','Porcentaje anulable','Densidad de cotización considerada por el simulador.'),
('saldo_inicial_capturado','Decimal monetario anulable','Saldo inicial ingresado en el formulario web.'),
('saldo_inicial_incluye_av','Indicador o decimal anulable','Indica o cuantifica si el saldo inicial incluye ahorro voluntario.'),
('saldo_acumulado_web','Decimal monetario anulable','Saldo acumulado proyectado por el simulador.'),
('estado','Categórico anulable','Estado operativo o de validación del registro.'),
('pension_con_av_web','Decimal monetario anulable','Pensión proyectada incluyendo ahorro voluntario.'),
('saldo_total_web','Decimal monetario anulable','Saldo total proyectado por el simulador.'),
('saldo_total_con_av_mensual_web','Decimal monetario anulable','Saldo total proyectado incluyendo aportación voluntaria mensual.'),
('saldo_acumulado_con_av_web','Decimal monetario anulable','Saldo acumulado proyectado con ahorro voluntario.'),
('modalidad_web','Categórico anulable','Modalidad de pensión obtenida sin ahorro voluntario adicional.'),
('modalidad_con_av_web','Categórico anulable','Modalidad de pensión obtenida al incluir ahorro voluntario.'),
('rcv_proy_web','Decimal monetario anulable','Saldo RCV proyectado sin el escenario adicional de ahorro voluntario.'),
('rcv_av_proy_web','Decimal monetario anulable','Saldo RCV proyectado incluyendo ahorro voluntario.')
]
assert [x[0] for x in DICT]==FIELDS
DIC_FIELDS=['numero','variable','tipo_recomendado_foto','descripcion_foto','nota_aplicacion_sintetica']
drows=[]
for idx,(field,typ,desc) in enumerate(DICT,1):
    note=''
    if field.endswith('_web') or field in ('Pension_web','estado','modalidad_con_av_web','edad_retiro_calculo'):
        note='SIMULACIÓN HIPOTÉTICA; NO CONSULTADO EN NINGÚN SITIO WEB'
    if field=='disposicion_recursos_web':note='VACÍO: no se puede inferir sin reglas específicas del simulador/derechos'
    if field=='rcv_av_proy_web':note='Variable heredada: rcv + ahorro voluntario, no saldo estricto de subcuenta RCV'
    if field=='saldo_inicial_capturado':note='RCV + solidario + bono, EXCLUYE ahorro voluntario y vivienda'
    if field=='Pension_web':note+='; PESOS MEXICANOS POR MES'
    if field in ('tasa_remplazo_web','tasa_rendimiento_web','densidad_cot_web'):note+='; PORCENTAJE EN ESCALA 0-100 (ej. 4.50 = 4.50%)'
    if field in ('nss','num_issste','curp'):note='IDENTIFICADOR FICTICIO; conservar como TEXTO; NO OFICIAL'
    drows.append(dict(zip(DIC_FIELDS,[idx,field,typ,desc,note])))
write(OUT/'DICCIONARIO_55_CAMPOS.csv',drows,DIC_FIELDS)

readme='''RESULTADOS CONSOLIDADOS SINTETICOS | corte 2026-10-29
=================================================================
1) CONTENIDO
 - 7 CSV de resultados: Banamex (benchmark separado) y XXI Banorte, Coppel,
   SURA, Profuturo, Invercap y Principal.
 - Cada CSV contiene 300 filas: 100 IMSS Ley 73, 100 IMSS Ley 97, 100 ISSSTE.
 - Un consolidado con 2,100 filas / 55 columnas exactamente como fotografías.
 - COMPARACION_SINTETICA_VS_BANAMEX.csv con 1,800 parejas de comparación.
 - CONSAR_REFERENCIA_SIN_RESULTADOS_WEB.csv separado: NO es AFORE,
   NO es una calculadora, por lo cual no se simulan resultados web.
 - DICCIONARIO_55_CAMPOS.csv y RESUMEN_VALIDACION.json.
 - generar_resultados_consolidados.py para reproducir con archivos de input.

2) MUY IMPORTANTE: SIMULACIONES, NO RESULTADOS REALES
 Los datos marcados *_web, incluido Pension_web, son SALIDAS FICTICIAS de
 una fórmula de prueba propia. No se hizo scraping, consulta o conexión con
 ninguna calculadora pública. NO equivalen a una oferta, pronóstico aprobado,
 cotización, derecho pensionario ni datos financieros/operativos reales.
 estado=SIMULADO_NO_CONSULTADO.
 Las diferencias por AFORE reflejan únicamente rendimientos de ensayo
 ARBITRARIOS para probar la aplicación; no miden ni clasifican AFORE.

3) TRAZABILIDAD Y COMPARABILIDAD
 Se conservaron, byte-a-byte como texto, los 27 campos input visibles
 desde id_cliente hasta escenario_estimado de los CSV anteriores.
 Un mismo id_cliente representa el mismo perfil hipotético en los 7 CSV;
 esto NO implica multiafiliación real.
 ARCHIVO_ORIGEN y FILA_ORIGEN hacen referencia a las filas físicas del
 CSV input original (primera fila de datos = 2).
 El CSV de Banamex se mantiene separado como benchmark.

4) SUPUESTOS MERAMENTE DEMOSTRATIVOS
 - Tasa anual REAL hipotética neta constante (se expresa como porcentaje):
   Banamex 4.50, XXI Banorte 4.35, Coppel 4.70, SURA 4.40,
   Profuturo 4.65, Invercap 4.25, Principal 4.55.
 - Rendimientos son elecciones arbitrarias, NO tasas publicadas de CONSAR.
 - Contribuciones mensuales ficticias sobre salario mensual: IMSS73 7.5%,
   IMSS97 10.0%, ISSSTE 11.5%; NO deben tomarse como cuotas oficiales.
 - Los cálculos se expresan en MXN de poder adquisitivo de 2026, sin
   inflación, impuestos, costos, cambios en salarios ni contingencias.
 - Edad proyectada: 65 si el cliente es menor; edad actual si ya tiene 65+.
 - El saldo futuro utiliza capitalización mensual equivalente a tasa anual.
 - Pensión Ley 73: se usa una razón salarial hipotética, NO saldo RCV.
   El AV mensual NO eleva automáticamente el pago del beneficio Ley 73.
 - IMSS97/ISSSTE: saldo proyectado / meses ilustrativos (NO cálculo actuarial).
 - Piso ficticio ilustrativo 6,200 MXN escenario IMSS73_GARANTIZADA y
   6,500 MXN escenario ISSSTE_PENSION_GARANTIZADA. NO mínimos legales.
 - Negativa de pensión: salida 0 y modalidad NEGATIVA_HIPOTETICA_NO_DICTAMEN.
   Estatus no representa resolución administrativa.
 - Proyecciones a edades +1 y +2 presuponen continuidad de cotización en
   los escenarios no negativos, sólo a fines de ensayo.
 - Disposición de recursos web se deja VACÍA: ningún derecho verificable.
 - saldo_inicial_capturado = RCV + solidario + bono, EXCLUYE AV y vivienda.
 - saldo_total_web = RCV futuro + solidario futuro + bono + AV inicial futuro.
   No incluye vivienda, pues su tratamiento depende de régimen y supuestos.
 - saldo_total_con_av_mensual_web añade las AV mensuales futuras.
 - rcv_av_proy_web hereda un nombre ambiguo del esquema, incluye AV y por
   tanto NO debe interpretarse como saldo contable RCV puro.
 - Tasa de remplazo = 100 * pension mensual / salario mensual.
 - Densidad = 100 * semanas cotizadas / semanas desde año de afiliación.
 - Porcentajes se guardan 0-100 (p.ej. 4.50 representa 4.5%), no fracción.
 - Los dos saldos de ahorro acumulado y total se repiten deliberadamente
   en este modelo a falta de un contrato real del simulador que los distinga.

5) PRECISIONES
 - Los campos respetan mayúsculas/minúsculas EXACTAS de las fotografías.
 - Los CSV son UTF-8 con BOM, comas como separador, punto decimal, dos
   decimales en todos los importes, fecha ISO-8601, textos identificadores.
 - CURP/NSS del input sólo se validan sintácticamente sin consulta oficial.
 - La validez comprobada es ESTRUCTURAL y de consistencia de simulación;
   NO garantiza derechos, rendimientos, saldos ni pensiones reales.

FUENTES DE CONTEXTO (NO se usaron para asignar rendimientos individuales)
 CONSAR, Afore registradas a septiembre de 2026:
 https://consar.gob.mx/gobmx/aplicativo/siset/CuadroInicial.aspx?md=40
'''
(OUT/'LEEME_METODOLOGIA_Y_LIMITACIONES.txt').write_text(readme,encoding='utf-8')

summary={
 'fecha_corte':'2026-10-29','campo_exacto_en_fotos':55,
 'fuente':'Inputs de clientes sintéticos generados en el paso anterior',
 'registros_consolidados':len(all_rows),'registros_referencia_consar_no_web':len(ref),
 'registros_comparacion_con_banamex':len(comparison),'clientes_unicos':len(by_client),
 'registros_por_archivo':source_count,
 'registros_por_regimen_por_afore':{k:dict(v) for k,v in per_regimen.items()},
 'tasa_rendimiento_por_afore_porcentaje_hipotesis':ASSUMED_RETURN,
 'conteo_nulos_disposicion_recursos_web':sum(not r['disposicion_recursos_web'] for r in all_rows),
 'comparabilidad_identidad_y_27_campos_input':'OK',
 'validaciones_contables_y_negativas':'OK' if not errors else 'FALLÓ',
 'estado':'SIMULADO_NO_CONSULTADO',
 'advertencia':'Salidas web y supuestos son ficticios. No se consultaron simuladores; no son datos, rendimientos ni derechos oficiales.'
}
(OUT/'RESUMEN_VALIDACION.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')

# Copiar el código generador dentro del ZIP junto con los CSV.
src_script=ROOT/'generar_resultados_consolidados.py'
ZIP=ROOT/'RESULTADOS_CONSOLIDADOS_AFORES_SINTETICOS_2026.zip'
with zipfile.ZipFile(ZIP,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=8) as z:
    for p in sorted(OUT.iterdir()):
        if p.is_file():z.write(p,arcname=p.name)
    z.write(src_script,arcname='generar_resultados_consolidados.py')
with zipfile.ZipFile(ZIP) as z:
    bad=z.testzip()
    assert bad is None,bad
    assert len(z.namelist())==14,(len(z.namelist()),z.namelist())
print(json.dumps({'zip':str(ZIP),'files':len(z.namelist()),'size_bytes':ZIP.stat().st_size,
                  'rows':len(all_rows),'compare':len(comparison),'profiles':len(by_client),
                  'fields':len(FIELDS),'all_checks':'OK'},ensure_ascii=False,indent=2))
