# Módulo ML

## Propósito

Este módulo contiene los componentes de Machine Learning para el clasificador de prompt injection. El detector ML corresponde a la Capa 4 del pipeline de detección: se ejecuta entre las reglas determinísticas y el policy engine para aportar una señal probabilística entrenada sobre ejemplos curados.

## Estructura esperada

- `data/`: datasets curados, subset propio en español y splits `train`/`val`/`test`.
- `models/`: checkpoints entrenados, artefactos exportados a ONNX y metadata versionable.
- Scripts de build, entrenamiento y evaluación, por ejemplo:
  - `ml/train_baseline.py`
  - `ml/train_transformer.py`
  - scripts auxiliares de evaluacion/export cuando correspondan.

## Entrenar el baseline

```powershell
./venv/Scripts/python.exe ml/train_baseline.py
```

## Fine-tuning de MiniLM en local (CPU)

Primero instalar PyTorch CPU-only:

```powershell
./venv/Scripts/python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cpu
```

Luego instalar las dependencias de entrenamiento:

```powershell
./venv/Scripts/python.exe -m pip install -r requirements-ml.txt
```

Ejecutar el entrenamiento:

```powershell
./venv/Scripts/python.exe ml/train_transformer.py
```

En CPU local, el fine-tuning puede tardar entre 1 y 3 horas según el hardware y el tamaño del dataset. Para re-entrenamientos grandes del feedback loop, usar Colab con GPU como alternativa recomendada.

## Fuente del dataset

El dataset base es `deepset/prompt-injections`, publicado en Hugging Face:

https://huggingface.co/datasets/deepset/prompt-injections

Licencia Apache-2.0 verificada el 2026-08-04. Citar esta fuente en documentación, reportes y artefactos derivados.

El subset en español es un dataset curado propio, creado como trabajo del autor de este repositorio.

## Verificación rápida

```powershell
./venv/Scripts/python.exe -c "import sklearn, pandas; print(sklearn.__version__)"
```
