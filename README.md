# 🛡️ Prompt Injection Firewall

Proxy inverso que intercepta llamadas a APIs de LLM y las analiza en múltiples capas de seguridad antes de permitirlas, modificarlas o bloquearlas.

---

## Estado del proyecto

| Fase | Estado |
|------|--------|
| **Fase 1 — Proxy funcional** | ✅ Completa |
| **Fase 2 — Firewall determinístico** | ✅ Completa |
| **Fase 3 — Machine Learning** | ⏳ Pendiente |
| **Fase 4 — Seguridad contextual** | ⏳ Pendiente |
| **Fase 5 — Producto demostrable** | ⏳ Pendiente |

---

## Fase 1: Proxy funcional ✅

El núcleo del proyecto. Endpoint compatible con OpenAI que recibe requests y los reenvía a un proveedor LLM.

### Lo que incluye
- `POST /v1/chat/completions` — endpoint principal compatible con la API de OpenAI
- `GET /health` — health check
- Streaming vía SSE (Server-Sent Events)
- Adaptador para OpenAI con HTTPX
- Validación de requests (mensajes no vacíos, modelo presente, content válido)
- Config vía variables de entorno
- Logs estructurados básicos

### Decisiones clave
- Estructura de carpetas completa desde el día 1 con módulos placeholder
- Streaming como passthrough desde el vamos
- OpenAI como proveedor inicial (estándar de facto)

### Lo que NO incluye
Autenticación, base de datos, Redis, detección de inyecciones, seguridad. Solo reenvío.

---

## Fase 2: Firewall determinístico ✅

La primera capa de seguridad real del proxy. Implementada en dos sub-fases:
- **2.1 (commit `5d75567`)**: normalización, motor de reglas YAML, risk score
- **2.2 (commit `dbc85fe`)**: PostgreSQL (SQLAlchemy async + Alembic), Redis (rate limit + caché de decisiones), API keys internas, auditoría

Decisiones detalladas y trade-offs en [docs/fase-2-firewall-deterministico.md](docs/fase-2-firewall-deterministico.md).

### Lo que incluye
- **Normalización de entrada**: Unicode, caracteres invisibles, homoglyphs, decodificación controlada (Base64, hex, ROT13), detección de texto bidireccional
- **Motor de reglas regex + heurísticas** en YAML — patrones conocidos de inyección (ignore previous instructions, DAN, system prompt extraction, etc.)
- **Cálculo de risk score** con pesos configurables
- **Decisiones**: `allow`, `block`, `allow_with_redaction`
- **PostgreSQL**: tablas `security_events`, `policies`, `api_keys`
- **Redis**: rate limiting + caché de decisiones
- **Autenticación via API keys internas**
- **Logs de auditoría**

### Pipeline de detección (Fase 2)
1. **Validación estructural** — tamaño, cantidad de mensajes, roles permitidos, profundidad JSON
2. **Normalización segura** — copia normalizada para análisis, original intacto para el proveedor
3. **Reglas determinísticas** — regex sobre patrones conocidos, scoring por regla
4. **Evaluación de políticas** — el motor de políticas toma la decisión final basada en el risk score agregado

### Decisiones clave
- Reglas en YAML desde el vamos (más fácil de ajustar sin deploy)
- Risk score con pesos configurables por tenant
- Arrancar solo bloqueando, redacción después
- PostgreSQL desde el inicio, no SQLite + migración

---

## Fase 3: Machine Learning ⏳

Clasificador de prompts maliciosos basado en modelos de lenguaje.

### Lo que incluye
- Dataset de prompts seguros y maliciosos (inglés + subset en español)
- Baseline: TF-IDF + Logistic Regression (scikit-learn)
- Evaluación: precisión, recall, F1
- Modelo avanzado: MiniLM o DistilBERT fine-tuneado
- Exportación a ONNX + inferencia con ONNX Runtime
- Versionado de detectores
- Feedback loop de falsos positivos

### Evolución del modelo
```
1. TF-IDF + Logistic Regression  → rápido, simple, explicable
2. MiniLM / DistilBERT fine-tune  → mejor comprensión semántica
3. Exportación a ONNX             → inferencia optimizada
4. ONNX Runtime                   → inferencia local eficiente
```

### Decisiones clave
- Modelo inicial: pre-entrenado de HuggingFace, fine-tune después
- Dataset con subset en español para diferenciar el portfolio
- Inferencia inline en el backend (separar solo si la latencia es problema)
- No usar un LLM como detector principal (caro, lento, también vulnerable)

---

## Fase 4: Seguridad contextual ⏳

El firewall se vuelve contextual — analiza historial, RAG, tools, y respuestas.

### Lo que incluye
- **Análisis del historial completo** del chat (ventana deslizante)
- **Detección de indirect prompt injection** — ataques via documentos RAG
- **Validación de tool calls** por nivel de riesgo
- **Output scanning** — secretos, PII, system prompt leakage
- **Redacción automática** de secretos en respuestas
- **Políticas compuestas**: risk score + tool risk level + contexto

### Niveles de riesgo para herramientas
| Nivel | Descripción |
|-------|-------------|
| 0 | Generación de texto |
| 1 | Búsqueda y lectura |
| 2 | Escritura reversible |
| 3 | Envío de mensajes o modificación de datos |
| 4 | Eliminación, pagos o ejecución de código |

### Decisiones clave
- Ventana deslizante de N mensajes, no historial completo
- Output scanning: regex para secretos/PII + modelo para system prompt leakage
- Tool risk levels configurables por tenant en YAML

---

## Fase 5: Producto demostrable ⏳

Lo que convierte el proyecto en un portfolio vendible y demoable.

### Lo que incluye
- **Frontend admin** con Next.js + Tailwind + shadcn/ui:
  - Dashboard con métricas en tiempo real
  - Security events y request inspector
  - Gestión de políticas y API keys
  - Detector performance y false-positive feedback
  - Audit trail completo
- **Playground de ataques** — comparar con/sin firewall
- **SDK o paquete Python** para integración externa (publicable en PyPI)
- **CI/CD** con GitHub Actions
- **Deploy**: Railway (API) + Vercel (frontend) + Upstash (Redis)
- **Documentación completa**

### Decisiones clave
- Frontend no se incorpora hasta esta fase — Swagger/curl alcanza para Fases 1-4
- Playground como mini frontend dedicado, no solo Swagger

---

## Stack completo

| Área | Tecnología |
|------|------------|
| Lenguaje | Python 3.12+ |
| API | FastAPI + Pydantic |
| Cliente HTTP | HTTPX |
| Servidor | Uvicorn |
| Clasificación inicial | scikit-learn |
| Clasificación avanzada | MiniLM / DistilBERT + ONNX |
| Políticas MVP | Python + YAML |
| Políticas avanzadas | Open Policy Agent (post-MVP) |
| Base de datos | PostgreSQL |
| Cache y rate limiting | Redis |
| Frontend | Next.js + TypeScript + Tailwind + shadcn |
| Observabilidad | OpenTelemetry + Prometheus + Grafana |
| Testing | Pytest + HTTPX + Locust |
| Contenedores | Docker + Docker Compose |
| CI/CD | GitHub Actions |
| Deploy | Railway + Vercel + Upstash |

---

## Cómo empezar

```bash
# Clonar el repositorio
git clone https://github.com/pato6604/prompt-injection-firewall.git
cd prompt-injection-firewall

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tu OPENAI_API_KEY

# Iniciar el proxy
uvicorn app.main:app --reload
```

El proxy escucha en `http://localhost:8000`. Los clientes solo necesitan cambiar la URL base:

```env
OPENAI_BASE_URL=http://localhost:8000/v1
```

### Probar el proxy

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"Hola"}]}'
```

### Ejecutar tests

```bash
pytest tests/ -v
```

---

## Arquitectura

```
app/
├── api/                    # Endpoints HTTP
│   ├── proxy_routes.py     # POST /v1/chat/completions
│   ├── admin_routes.py     # Endpoints de administración
│   └── health_routes.py    # GET /health
├── proxy/                  # Lógica del proxy
│   ├── request_parser.py   # Validación de requests
│   ├── provider_router.py  # Ruteo a proveedores
│   ├── stream_handler.py   # Manejo de streaming SSE
│   └── response_adapter.py # Adaptación de respuestas
├── detection/              # Pipeline de detección
│   ├── pipeline.py
│   ├── regex_detector.py
│   ├── heuristic_detector.py
│   ├── classifier_detector.py
│   ├── encoding_detector.py
│   └── indirect_injection_detector.py
├── policies/               # Motor de políticas
│   ├── engine.py
│   ├── rules/
│   └── schemas.py
├── security/               # Seguridad
│   ├── authentication.py
│   ├── rate_limit.py
│   ├── secret_scanner.py
│   └── redaction.py
├── providers/              # Adaptadores de proveedores
│   ├── base.py
│   ├── openai.py
│   ├── gemini.py
│   ├── anthropic.py
│   └── ollama.py
├── observability/          # Observabilidad
│   ├── metrics.py
│   ├── tracing.py
│   └── audit.py
├── database/               # Capa de datos
│   ├── models.py
│   └── repositories.py
└── main.py                 # FastAPI app + lifespan
```

---

## Pipeline de detección

```
Request entrante
       │
       ▼
┌─────────────────────────────┐
│ Capa 1: Validación          │
│ estructural                 │  ← Sin IA
│ (tamaño, roles, JSON deep)  │
└──────────┬──────────────────┘
           ▼
┌─────────────────────────────┐
│ Capa 2: Normalización       │
│ (Unicode, homoglyphs,       │
│  decodificación, RTL)       │
└──────────┬──────────────────┘
           ▼
┌─────────────────────────────┐
│ Capa 3: Reglas              │  ← Fase 2
│ determinísticas (regex)     │
└──────────┬──────────────────┘
           ▼
┌─────────────────────────────┐
│ Capa 4: Clasificador ML     │  ← Fase 3
│ (TF-IDF → DistilBERT)       │
└──────────┬──────────────────┘
           ▼
┌─────────────────────────────┐
│ Capa 5: Contexto            │  ← Fase 4
│ (historial, RAG, tools)     │
└──────────┬──────────────────┘
           ▼
┌─────────────────────────────┐
│ Policy Engine               │
│  → allow / block /          │
│    redact / quarantine      │
└──────────┬──────────────────┘
           ▼
      Proveedor LLM
           │
           ▼
┌─────────────────────────────┐
│ Output scanning             │  ← Fase 4
│ (secretos, PII, leakage)    │
└──────────┬──────────────────┘
           ▼
      Respuesta al cliente
```

---

## Licencia

MIT
