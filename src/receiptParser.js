// Parses raw OCR text from a Mexican restaurant/delivery receipt (ticket)
// and extracts line items with quantities and the delivery address (domicilio).

const QUANTITY_LINE_RE = /(\d+(?:[.,]\d+)?)\s*[xX]\s*\$?\s*(\d+(?:[.,]\d+)?)/;

// Keywords that mark a line item as a delivery fee rather than a product,
// so it's excluded from the "units of product" count but still parsed for the address.
// "micili"/"micillo" (substrings of "domicilio") tolerate OCR misreads of the leading letter,
// which is common on thermal-printer receipts (e.g. "Domicilio" -> "pomicillo").
const DELIVERY_KEYWORDS = /micili|micillo|delivery|envio|envío/i;

function cleanLine(line) {
  return line.replace(/\s+/g, ' ').trim();
}

export function parseReceipt(rawText) {
  const lines = rawText
    .split('\n')
    .map(cleanLine)
    .filter(Boolean);

  const items = [];
  let deliveryAddress = null;
  let deliveryZone = null;

  lines.forEach((line, index) => {
    const match = line.match(QUANTITY_LINE_RE);
    if (!match) return;

    const quantity = parseFloat(match[1].replace(',', '.'));
    const unitPrice = parseFloat(match[2].replace(',', '.'));
    if (Number.isNaN(quantity) || Number.isNaN(unitPrice)) return;

    // The product/description name usually sits on the line above the "N x price" line.
    const nameLine = index > 0 ? lines[index - 1] : '';
    const isDelivery = DELIVERY_KEYWORDS.test(nameLine) || DELIVERY_KEYWORDS.test(line);

    if (isDelivery) {
      deliveryZone = nameLine || null;
      // The address itself is typically printed on the line right after the "N x price" line.
      const nextLine = lines[index + 1];
      if (nextLine && !QUANTITY_LINE_RE.test(nextLine) && !/^total$/i.test(nextLine)) {
        deliveryAddress = nextLine;
      }
      return;
    }

    items.push({ name: nameLine, quantity, unitPrice });
  });

  // Fallback: some tickets label the address line explicitly (e.g. "Direccion: ...").
  if (!deliveryAddress) {
    const explicit = lines.find((l) => /^(dirección|direccion|domicilio)\s*[:-]/i.test(l));
    if (explicit) {
      deliveryAddress = explicit.replace(/^(dirección|direccion|domicilio)\s*[:-]\s*/i, '');
    }
  }

  const totalUnits = items.reduce((sum, item) => sum + item.quantity, 0);

  return {
    items,
    totalUnits,
    deliveryZone,
    deliveryAddress,
  };
}
