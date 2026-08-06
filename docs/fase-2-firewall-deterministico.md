# Fase 2 — Firewall determinístico (completa)

Sistema RAG de seguridad: proxy inverso que intercepta llamadas a APIs de LLM y las analiza en capas antes de permitirlas, modificarlas o bloquearlas.

**Estado:** ✅ Completa (sub-fases 2.1 y 2.2)
**Commit:** `dbc85fe` — "fase 2.2: postgresql + redis + api keys internas + auditoria"
**Tests:** 57 pasando (`venv/Scripts/python.exe -m pytest -q`)

---

## Sub-fase 2.1 — Pipeline de detección (commit `5d75567`)

- Normalización de entrada: Unicode, caracteres invisibles, homoglyphs, decodificación controlada (Base64, hex, ROT13), detección de texto bidireccional
- Motor de reglas regex + heurísticas en YAML (`app/detection/policies/default.yaml`, 6 reglas)
- Cálculo de risk score con pesos por severidad (`app/detection/scorer.py`)
- Decisiones: `allow` / `flag` / `block` con umbrales configurables (0.3 / 0.7)

---

## Sub-fase 2.2 — Datos y seguridad

### Lo que incluye

1. **Capa de datos** — SQLAlchemy 2.0 async + Alembic
   - `app/database/`: motor async, dependencia `get_db`, modelos `ApiKey`, `SecurityEvent`, `Policy`
   - Repositorios CRUD + `get_stats` (total requests, bloqueados, risk promedio)
   - Migración inicial Alembic `0001_initial`
   - `DATABASE_URL` configurable; default SQLite para dev/tests sin Postgres

2. **Redis con fallback in-memory**
   - Rate limiter de ventana deslizante: 60 req/min por API key (o "anonymous")
   - Caché de decisiones: SHA-256 del texto normalizado -> decisión cacheada 60s

3. **Autenticación con API keys internas**
   - `POST /admin/keys`: genera key con `secrets.token_urlsafe(32)`, prefijo `pif_`
   - Solo se almacena el SHA-256; el plaintext se devuelve una única vez (patrón Stripe)
   - Endpoints admin protegidos con `X-Master-Key` (comparación `hmac.compare_digest`)
   - `GET /admin/keys`, `DELETE /admin/keys/{id}`, `GET /admin/events`, `GET /admin/stats`

4. **Auditoría**
   - Todo request (allow/flag/block) registra un `SecurityEvent` (request_id, risk_score, reglas, IP, user-agent)
   - Middleware `X-Request-ID`: ID trazable en todas las respuestas, incluso errores

5. **Integración en el proxy** (`POST /v1/chat/completions`)
   - Orden: auth -> rate limit -> parse -> detección (con caché) -> auditoría -> proveedor

---

## Decisiones técnicas y trade-offs

### 1. SQLAlchemy 2.0 async + asyncpg (no SQL crudo, no driver sync)
**Por qué:** todo el stack es async (FastAPI, httpx, redis.asyncio). Un driver sync bloquearía el event loop en cada query — el proxy dejaría de responder mientras espera la DB.
**Por qué ORM:** permite cambiar de motor con una línea de config y usar migraciones versionadas. El costo (capa de abstracción) es aceptable a esta escala.
**Trade-off:** el ORM genera queries que un DBA no escribiría a mano; irrelevante con este volumen.

### 2. SQLite por defecto, PostgreSQL en producción
**Por qué:** desarrollar y testear no debe requerir levantar Postgres. Con SQLAlchemy, "modo producción" es cambiar la URL.
**Cómo:** en `main.py`, sqlite -> `create_all` al arrancar; postgres -> migraciones Alembic.
**Trade-off:** sqlite y postgres difieren en detalles (JSON, concurrencia), pero este modelo de datos (3 tablas chicas) es compatible en ambos.

### 3. Alembic para migraciones
**Por qué:** en producción no querés `create_all` a ciegas; querés migraciones versionadas y reproducibles. Es el estándar de la industria.
**Trade-off:** setup inicial más pesado; vale para un proyecto que apunta a deploy real.

### 4. Redis con fallback in-memory
**Por qué Redis:** rate limiting distribuido multi-instancia (INCR+EXPIRE atómico, TTL nativo) — si Cloud Run escala a N workers, el límite es compartido.
**Por qué fallback:** tests y dev sin servicios externos.
**Trade-off consciente:** la ventana en Redis es fija (ráfagas posibles en el borde); el fallback en memoria usa ventana deslizante real (deque de timestamps). Se eligió simple en Redis porque 60 req/min no justifica un script Lua.
**Concurrencia:** el fallback tiene `asyncio.Lock` — suficiente en un proceso async single-event-loop; multi-proceso es justamente el caso que exige Redis.

### 5. Caché de decisiones con hash del texto normalizado
**Por qué cachear:** el pipeline es determinístico; un atacante que repite el mismo payload no debería pagar la evaluación N veces.
**La decisión fina:** se hashea el texto NORMALIZADO, no el raw — si el atacante varía homoglyphs o mayúsculas, la normalización colapsa al mismo hash y la variante cosmética se bloquea con la decisión cacheada. Multiplicador de defensa gratis.
**Por qué la clave no incluye usuario:** el riesgo es intrínseco al texto; compartir la caché entre tenants es correcto y deseable.
**Trade-off:** si cambian las reglas YAML, la caché persiste hasta el TTL (60s). Aceptable.

### 6. API keys: token_urlsafe(32) + SHA-256 + prefijo pif_
**Por qué token_urlsafe(32):** 256 bits de entropía criptográfica, URL-safe.
**Por qué guardar solo el hash:** si la DB se filtra, las keys no se recuperan (patrón de contraseñas).
**Por qué SHA-256 y no bcrypt/argon2:** los KDF lentos existen para contraseñas de baja entropía. Una API key tiene 256 bits — inatacable por fuerza bruta aunque el hash sea rápido. bcrypt sería lentitud sin beneficio.
**Por qué prefijo pif_:** identificar una key en logs/dashboards sin exponer el secreto.

### 7. Master key con hmac.compare_digest
**Por qué:** comparar con `!=` toma tiempo proporcional al prefijo coincidente (timing attack). `compare_digest` siempre tarda lo mismo. Para un proyecto de seguridad, una comparación vulnerable de la propia llave maestra sería inadmisible.
*(Señalado por GPT-4o en el code review de la fase.)*

### 8. Validación de rango en umbrales (Field ge/le)
**Por qué:** un threshold fuera de 0-1 rompería la lógica de decisión en silencio. Validar en la frontera (config) es fail-fast: el error aparece al arrancar, no en producción.

### 9. Auditoría siempre (allow, flag y block) + X-Request-ID
**Por qué auditar también los allow:** sin baseline de tráfico normal no se detectan anomalías ni se miden falsos positivos.
**X-Request-ID:** trazabilidad extremo a extremo sin exponer datos sensibles; el cliente reporta el ID y se busca el evento por él. El middleware lo genera para TODAS las respuestas, incluidos los 400/403 — los errores son lo más importante de trazar.

### 10. Orden del pipeline
- **auth primero:** no gastar CPU en requests no autenticados
- **rate limit antes del parse:** proteger contra floods incluso de payloads inválidos
- **detección antes de la auditoría:** solo se auditan requests válidos y evaluados
- **auditoría antes del proveedor:** si el request se bloquea, igual quedó registrado
- Capas independientes = defensa en profundidad

### 11. Tests con SQLite in-memory + auth desactivada por defecto
**Por qué in-memory:** velocidad y aislamiento entre tests.
**Por qué auth desactivada en conftest:** los 46 tests previos no enviaban headers; activarla los rompería. Los tests nuevos de auth la encienden explícitamente.
**Trade-off:** los tests no ejercitan Postgres/Redis reales — pero la capa SQLAlchemy es la misma y el fallback es código de producción para dev.

### 12. venv con Python 3.12 (uv)
**Por qué:** el README declara 3.12+, el global era 3.14 sin venv. El venv aísla el proyecto y reproduce el contrato. uv descarga el CPython exacto (3.12.11) al vuelo.

---

## Proceso seguido (pipeline de 3 roles)

1. **PM (Hermes):** planificó la fase completa, definió alcance y restricciones
2. **Implementador (Codex):** escribió todo el código (`codex exec`)
3. **Reviewer (GPT-4o):** code review obligatorio de cada salida
   - Detectó 2 problemas reales: master key con `!=` (-> `hmac.compare_digest`) y umbrales sin validación de rango. Corregidos por Codex y re-verificados.
   - Un "CHANGES_REQUIRED" posterior resultó falso positivo (afirmaba que faltaban defaults cuando estaban: 0.7/0.3/60/60, confirmado empíricamente).
4. **Verificación:** 57 tests pasando, defaults confirmados por ejecución

---

## Cómo verificar

```bash
cd prompt-injection-firewall
venv/Scripts/python.exe -m pytest -q        # 57 passed
```

---

## Próximo paso: Fase 3 — Machine Learning

- Dataset de prompts seguros y maliciosos (inglés + subset en español)
- Baseline: TF-IDF + Logistic Regression (scikit-learn)
- Modelo avanzado: MiniLM/DistilBERT fine-tuneado
- Exportación a ONNX + inferencia con ONNX Runtime
- Feedback loop de falsos positivos
