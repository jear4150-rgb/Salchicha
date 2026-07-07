import { useRef, useState } from 'react';
import { createWorker } from 'tesseract.js';
import { parseReceipt } from './receiptParser';
import './App.css';

function App() {
  const [imageUrl, setImageUrl] = useState(null);
  const [status, setStatus] = useState('idle'); // idle | processing | done | error
  const [rawText, setRawText] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  async function handleFile(file) {
    if (!file) return;

    setImageUrl(URL.createObjectURL(file));
    setStatus('processing');
    setError(null);
    setResult(null);
    setRawText('');

    try {
      const worker = await createWorker('spa', 1, {
        workerPath: '/tesseract/worker.min.js',
        corePath: '/tesseract/core/',
        langPath: '/tesseract/lang/',
      });
      const { data } = await worker.recognize(file);
      await worker.terminate();

      setRawText(data.text);
      setResult(parseReceipt(data.text));
      setStatus('done');
    } catch (err) {
      console.error(err);
      setError(err.message || 'No se pudo leer el ticket.');
      setStatus('error');
    }
  }

  function handleInputChange(event) {
    handleFile(event.target.files?.[0]);
  }

  function reset() {
    setImageUrl(null);
    setStatus('idle');
    setRawText('');
    setResult(null);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Lector de tickets</h1>
        <p>Toma una foto del ticket para extraer las unidades y el domicilio</p>
      </header>

      <main className="app-main">
        {!imageUrl && (
          <label className="capture-button">
            Tomar / subir foto del ticket
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              capture="environment"
              onChange={handleInputChange}
              hidden
            />
          </label>
        )}

        {imageUrl && (
          <div className="preview">
            <img src={imageUrl} alt="Ticket capturado" />
          </div>
        )}

        {status === 'processing' && <p className="status">Leyendo ticket...</p>}

        {status === 'error' && <p className="status status-error">Error: {error}</p>}

        {status === 'done' && result && (
          <section className="result">
            <div className="result-card">
              <span className="result-label">Unidades totales</span>
              <span className="result-value">{result.totalUnits}</span>
            </div>

            <div className="result-card">
              <span className="result-label">Domicilio</span>
              <span className="result-value result-value-text">
                {result.deliveryAddress || 'No detectado'}
              </span>
            </div>

            {result.items.length > 0 && (
              <div className="items">
                <h2>Artículos detectados</h2>
                <ul>
                  {result.items.map((item, i) => (
                    <li key={i}>
                      <span className="item-qty">{item.quantity}x</span>
                      <span className="item-name">{item.name || 'Artículo'}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <details className="raw-text">
              <summary>Ver texto completo detectado</summary>
              <pre>{rawText}</pre>
            </details>
          </section>
        )}

        {imageUrl && (
          <button type="button" className="retry-button" onClick={reset}>
            Tomar otra foto
          </button>
        )}
      </main>
    </div>
  );
}

export default App;
