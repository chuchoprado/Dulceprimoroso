# Dulceprimoroso

Este repositorio ahora incluye un **MVP técnico** para una app de repostería con cuatro pilares:

1. Recetario de postres clásicos.
2. Tabla de costos con soporte multimoneda.
3. Convertidor de medidas internacional.
4. Chat repostero asistido por IA.

## Archivos clave

- `app/bakery_mvp.py`: API FastAPI del MVP.
- `docs/benchmark_y_estrategia.md`: benchmarking + plan de monetización.

## Ejecutar local

```bash
pip install -r requirements.txt
uvicorn app.bakery_mvp:app --reload
```

## Endpoints

- `GET /recipes`
- `POST /costs`
- `POST /convert`
- `POST /chat`

> Para usar `/chat`, define `OPENAI_API_KEY` en tu entorno.
