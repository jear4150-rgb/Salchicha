# Salchicha - Lector de tickets

App web que usa la cámara del celular para fotografiar un ticket de compra/domicilio y extrae automáticamente:

- El número de unidades (artículos comprados)
- El domicilio de entrega

El reconocimiento de texto (OCR) corre completamente en el navegador con [Tesseract.js](https://github.com/naptha/tesseract.js) — no requiere API keys ni conexión a servicios externos, ya que los archivos del motor OCR (worker, wasm y datos del idioma español) están incluidos en `public/tesseract/`.

## Uso

```bash
npm install
npm run dev
```

Abre la app en el navegador del celular, toca "Tomar / subir foto del ticket" y selecciona la cámara. Tras procesar la imagen se muestran las unidades totales, el domicilio detectado y la lista de artículos.

## Cómo funciona el parseo

`src/receiptParser.js` analiza el texto reconocido por OCR buscando líneas con el patrón `N x precio` (común en tickets impresos) para contar unidades por artículo, y detecta la línea de domicilio/envío (tolerando errores comunes de OCR) para extraer la dirección impresa justo después.

## Scripts

- `npm run dev` - servidor de desarrollo
- `npm run build` - build de producción
- `npm run lint` - lint con oxlint
- `npm run preview` - previsualizar el build
