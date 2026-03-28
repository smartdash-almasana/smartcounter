# MVP Usable SmartCounter

## 1. Usuario exacto del MVP

- Operador de estudio contable argentino pequeno o mediano.
- Contador independiente que recibe Excels caoticos de clientes y necesita una primera lectura revisable, no una automatizacion ciega.

## 2. Dolor exacto que resolvemos primero

- Perder tiempo manual detectando donde empieza la tabla util, que columnas significan algo contable y que valores son riesgosos o ambiguos.
- El primer dolor no es "liquidar todo"; es "entender rapido si la planilla sirve, que interpreta el sistema y que debe revisar una persona".

## 3. Input exacto del MVP

- Un archivo Excel local por corrida.
- Hojas con encabezados desplazados, aliases inestables, montos sucios y estructura no siempre limpia.
- Casos baseline confirmados hoy: `03_encabezado_desplazado`, `04_semantica_inestable`, `07_formulas_ocultos`, `08_montos_mixtos_signos`.

## 4. Output exacto del MVP

- `sheet` detectada.
- `header_row_1based` detectado.
- columnas con mapping base a campo canonico o estado `ambiguous`.
- preview de normalizacion base para tipos simples (`fecha`, `monto`, `cuit`, `null`).
- `warnings_estructurados`.
- `normalization_summary` para revision humana por codigo, por campo y con ejemplos reales.

## 5. Flujo minimo de uso punta a punta

1. El operador corre `run_local.py --excel <archivo> --pipeline-curated`.
2. SmartCounter detecta region tabular y header.
3. SmartCounter propone mapping semantico base de columnas.
4. SmartCounter normaliza valores evidentes en preview.
5. SmartCounter devuelve warnings y resumen curado para revisar antes de usar el archivo.

## 6. Que entra en MVP

- Deteccion de tabla util y header real.
- Mapping semantico base con `mapped`, `ambiguous`, `unmapped`.
- Normalizacion base de fechas, montos, cuit/cuil y vacios.
- Warnings estructurados y revision asistida por salida curada.
- Priorizacion tecnica inicial en planillas cercanas a IVA y registros contables tabulares.

## 7. Que queda explicitamente fuera

- ERP.
- Dashboard complejo.
- Automatizacion ciega a AFIP/ARCA.
- Scoring contable final.
- Conciliacion completa.
- Normalizacion profunda de todas las columnas posibles.
- Resolucion automatica de ambiguedades semanticas.

## 8. Criterio de "usable"

- Es usable si un contador puede correr el pipeline sobre un Excel real y obtener en una sola salida:
  - donde esta la tabla,
  - que entendio el sistema,
  - que no entendio,
  - y que debe revisar manualmente.
- No exige cero warnings; exige warnings utiles y no silenciosos.

## 9. Senal concreta de validacion con contador real

- Senal minima de validacion: un contador usa el pipeline sobre al menos 4 archivos reales o equivalentes del pack baseline y confirma que la salida le ahorra el primer filtro manual.
- En esta fase, la senal operativa interna ya confirmada es:
  - `03`: header correcto, mapping `3/0/0`
  - `04`: header correcto, mapping `2/1/0`
  - `07`: header correcto, mapping `3/0/0`
  - `08`: header correcto, mapping `3/0/0` y resumen util de warnings de monto

## 10. Relacion entre construir primero IVA y vender primero LSD

- Construir primero: IVA.
  - Porque obliga a resolver el nucleo duro y reusable del producto: tabla util, header real, fechas, cuit, importes, neto/iva, ambiguedades y trazabilidad.
  - Es la mejor superficie tecnica para endurecer parser y normalizador.
- Vender primero: LSD.
  - Porque comercialmente puede ser una entrada mas simple y concreta para estudio contable, sin prometer automatizacion contable total.
  - Pero no debe definir la arquitectura tecnica inicial.
- Decision explicita:
  - el nucleo tecnico del MVP usable se construye primero para IVA;
  - la entrada comercial inicial puede ser LSD si simplifica adopcion, siempre montada sobre el mismo nucleo de interpretacion revisable.
