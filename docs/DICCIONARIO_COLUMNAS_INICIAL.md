# Diccionario Columnas Inicial (SmartCounter)

Base prioritaria: manual **"La Practica Real de Excel en Contabilidad Argentina: Un Manual de Interpretacion para Sistemas de Parsing y Normalizacion"**.

## 1) Identificadores principales

| nombre canonico | aliases correctos / abreviaturas | errores frecuentes / sinonimos locales | categoria funcional | prioridad MVP | observacion |
|---|---|---|---|---|---|
| `cliente` | cliente, nom cliente, nombre cliente | empresa, razon social, rsocial, cuenta, cta cte | identificacion de contraparte | alta | No confundir con proveedor sin contexto de hoja. |
| `proveedor` | proveedor, prov, nombre proveedor | suplidor, tercero, empresa | identificacion de contraparte | media | En hojas mixtas puede compartir espacio con cliente. |
| `razon_social` | razon social, rsocial, razon social cliente | empresa, denominacion, socio | identificacion fiscal | alta | Suele duplicar a cliente/proveedor con otra etiqueta. |
| `cuit` | cuit, cuil, doc tercero, documento | doc, nro doc, dni, ruc | identificacion fiscal | alta | No inferir DNI como CUIT sin longitud/patron valido. |
| `tipo_comprobante` | tipo, t/comprobante, tipo comp | comp, factura, nota deb, nota cre | identificacion de comprobante | alta | Alto riesgo de ambiguedad con `comprobante`. |
| `punto_venta` | pv, punto venta, pto vta, pvta | local, sucursal | identificacion de comprobante | media | Puede venir fusionado con numero comprobante. |
| `numero_comprobante` | nro, nro comp, nro factura, num | factura, folio, remito | identificacion de comprobante | alta | Si viene texto mixto, preservar original y normalizado. |
| `comprobante` | comprobante, factura, recibo | comp, fac, remito, nc, nd | identificacion de comprobante | media | Campo paraguas; evitar mapear automatico a tipo o numero. |

## 2) Importes y totales

| nombre canonico | aliases correctos / abreviaturas | errores frecuentes / sinonimos locales | categoria funcional | prioridad MVP | observacion |
|---|---|---|---|---|---|
| `importe` | importe, impte, importe total | monto, total, valor | monetario | alta | Puede venir con $/signos/paréntesis. |
| `monto` | monto, monto neto, monto total | total, importe, cobrar, pagar | monetario | alta | Si hay varias columnas de monto, marcar ambiguedad. |
| `total` | total, importe_total | subtotal, neto, saldo | monetario | alta | `total` es ambiguo sin contexto tributario. |
| `neto_gravado` | neto, neto gravado, base imponible | total sin iva, importe neto | tributario-monetario | alta | Clave en IVA compras/ventas. |
| `saldo` | saldo, saldo final | deuda, debe, haber, disponible | cuentas corrientes | alta | No inferir signo semantico sin contexto de cuenta. |
| `saldo_pendiente` | saldo pendiente, pendiente | deuda pendiente, saldo deuda | cuentas corrientes | alta | Prioritario para cobranzas. |
| `deuda` | deuda, monto adeudado | saldo, pendiente, por cobrar | cobranzas | media | Puede ser derivado de otras columnas. |

## 3) IVA e impuestos

| nombre canonico | aliases correctos / abreviaturas | errores frecuentes / sinonimos locales | categoria funcional | prioridad MVP | observacion |
|---|---|---|---|---|---|
| `iva_debito` | iva debito, iva_deb, debito fiscal | iibb, percepcion ibb, retencion ibb | impuestos | alta | En manual aparece mezcla frecuente con otros tributos. |
| `iva_credito` | iva credito, iva_cre, credito iva | iva acreditable | impuestos | alta | No mezclar con iva debito por similitud textual. |
| `alicuota_iva` | alicuota iva, alic %, tasa iva | porcentaje iva, iva 21 | impuestos | media | Puede venir como texto `%`. |
| `percepcion_iibb` | percepcion iibb, perc iibb | iva, retencion iibb | impuestos | media | Suele confundirse con retenciones. |
| `retencion` | retencion, ret, imp retenido | percepcion, descuento | impuestos | media | Confirmar sujeto y base antes de mapear. |
| `impuesto_interno` | imp interno, impuestos internos | lit, impuesto litros, otros imp | impuestos | baja | Frecuente en rubros especificos. |

## 4) Cuentas corrientes / cobranzas / pagos

| nombre canonico | aliases correctos / abreviaturas | errores frecuentes / sinonimos locales | categoria funcional | prioridad MVP | observacion |
|---|---|---|---|---|---|
| `estado` | estado, situacion, status | condicion, vigente, finalizado | seguimiento operativo | alta | Usado para pendiente/vencido/cobrado. |
| `condicion_pago` | condicion pago, terminos, plazo | contado, cta cte, neto 30 | condiciones comerciales | media | Puede afectar vencimiento esperado. |
| `medio_pago` | medio pago, forma pago, canal | transferencia, efectivo, tarjeta | cobranza/pago | media | En algunos excels va en columna `canal`. |
| `fecha_pago` | fecha pago, pago, fecha cobro | cobr, cancelacion, fecha cancelado | cobranzas/pagos | media | No asumir que reemplaza vencimiento. |
| `cobrado` | cobrado, importe cobrado | pagado, cancelado parcial | cobranzas/pagos | media | Sirve para calcular saldo pendiente. |
| `debe` | debe | cargo, debito | cuenta corriente | baja | Ambiguo si no existe `haber`. |
| `haber` | haber | credito | cuenta corriente | baja | Ambiguo si no existe `debe`. |

## 5) Nomina / remuneraciones

| nombre canonico | aliases correctos / abreviaturas | errores frecuentes / sinonimos locales | categoria funcional | prioridad MVP | observacion |
|---|---|---|---|---|---|
| `legajo` | legajo, nro legajo | id empleado, codigo empleado | nomina | baja | Relevante para modulo futuro de sueldos. |
| `empleado` | empleado, apellido y nombre | colaborador, personal | nomina | baja | No prioritario en MVP inicial contable general. |
| `periodo_liquidacion` | periodo, periodo liquidacion | mes liquidado, quincena | nomina | baja | Puede confundirse con periodo fiscal. |
| `remuneracion_bruta` | remuneracion bruta, bruto | sueldo bruto, haberes | nomina | baja | Fuera del foco MVP inicial de parsing general. |
| `remuneracion_neta` | remuneracion neta, neto | sueldo de bolsillo, a cobrar | nomina | baja | Util para expansion vertical posterior. |

## 6) Vencimientos / agenda

| nombre canonico | aliases correctos / abreviaturas | errores frecuentes / sinonimos locales | categoria funcional | prioridad MVP | observacion |
|---|---|---|---|---|---|
| `fecha` | fecha, fec, fecha doc | fecha val, fecha movimiento | temporal | media | Campo intrinsicamente ambiguo. |
| `fecha_emision` | fecha emision, emision, f emi | fecha documento, fecha comp | temporal-documental | alta | Importante para trazabilidad documental. |
| `fecha_vencimiento` | fecha vencimiento, vto, vence, fvto, fec vto | fecha, plazo, dias plazo | temporal-vencimientos | alta | Uno de los campos mas criticos del MVP. |
| `periodo_fiscal` | periodo fiscal, periodo, periodo iva | mes, anio mes, periodo contable | fiscal | media | No mezclar con periodo de nomina. |
| `jurisdiccion` | jurisdiccion, provincia, agip, arba | zona, delegacion | agenda impositiva | baja | Relevante en vencimientos tributarios. |

## 7) Conciliacion bancaria

| nombre canonico | aliases correctos / abreviaturas | errores frecuentes / sinonimos locales | categoria funcional | prioridad MVP | observacion |
|---|---|---|---|---|---|
| `fecha_valor` | fecha valor, fec valor | fecha banco, fecha acreditacion | bancaria | media | Diferente de fecha de operacion. |
| `descripcion` | descripcion, detalle, concepto | glosa, referencia, observacion | bancaria/operativa | media | Util para conciliacion y auditoria. |
| `referencia_bancaria` | referencia, nro op, id movimiento | comprobante banco, ticket | bancaria | media | Suele venir incompleta o en texto libre. |
| `debito_bancario` | debito, egreso banco | salida, cargo banco | bancaria | baja | No inferir signo sin columna complementaria. |
| `credito_bancario` | credito, ingreso banco | entrada, abono banco | bancaria | baja | No inferir signo sin columna complementaria. |
| `saldo_bancario` | saldo banco, saldo extracto | saldo, disponible | bancaria | media | Evitar mezclar con saldo de cliente/proveedor. |

## 10 campos canonicos que deben resolverse primero (MVP si o si)

1. `cliente`
2. `cuit`
3. `tipo_comprobante`
4. `numero_comprobante`
5. `fecha_emision`
6. `fecha_vencimiento`
7. `importe`
8. `neto_gravado`
9. `iva_debito`
10. `estado`

## 5 ambiguedades criticas que SmartCounter no debe inferir automaticamente

1. `fecha` -> no decidir automaticamente si es `fecha_emision`, `fecha_vencimiento`, `fecha_pago` o `fecha_valor`.
2. `saldo` -> no decidir automaticamente si es saldo deudor, acreedor, pendiente o bancario.
3. `total` -> no asumir si corresponde a neto, total con IVA o total general.
4. `comprobante` -> no asumir automaticamente `tipo_comprobante` o `numero_comprobante` sin separacion clara.
5. `documento/doc/nro doc` -> no mapear automaticamente a `cuit` sin validacion de formato y longitud.
