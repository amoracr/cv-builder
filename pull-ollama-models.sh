#!/bin/sh

# Cargar las variables del archivo .env si existe
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

PORT=${OLLAMA_PORT:-11434}
CONTAINER_NAME=${OLLAMA_CONTAINER_NAME:-ollama_service}

# Leer motores y modelos configurados en el .env (pasando a minúsculas por seguridad)
EVAL_ENGINE=$(echo "${EVALUATE_ENGINE:-ollama}" | tr '[:upper:]' '[:lower:]')
EVAL_MODEL=${EVALUATE_MODEL:-qwen2.5-coder:7b}

WRITE_ENGINE=$(echo "${WRITE_CV_ENGINE:-gemini}" | tr '[:upper:]' '[:lower:]')
WRITE_MODEL=${WRITE_CV_MODEL:-gemini-2.5-flash}

# Validar si al menos uno de los motores usa Ollama
NEED_OLLAMA=false
if [ "$EVAL_ENGINE" = "ollama" ] || [ "$WRITE_ENGINE" = "ollama" ]; then
  NEED_OLLAMA=true
fi

if [ "$NEED_OLLAMA" = false ]; then
  echo "-> Ningún motor está configurado para usar Ollama. Omitiendo la comprobación y descarga local."
  exit 0
fi

echo "Esperando a que Ollama esté listo en el puerto $PORT..."

# Esperar a que el servidor de Ollama responda
until wget -qO- http://localhost:$PORT/ >/dev/null 2>&1; do
  sleep 2
  echo "Esperando a que Ollama responda..."
done

echo "¡Ollama está activo en el contenedor!"

# Función robusta para hacer pull con reintentos automáticos ante cortes por EOF o red
pull_model_with_retry() {
  model_name=$1
  max_attempts=10
  attempt=1

  while [ $attempt -le $max_attempts ]; do
    echo "-> Intentando descargar el modelo '$model_name' (Intento $attempt/$max_attempts)..."
    
    # Ejecutamos el pull dentro del contenedor
    if docker exec "$CONTAINER_NAME" ollama pull "$model_name"; then
      echo "¡Modelo '$model_name' descargado con éxito!"
      return 0
    else
      echo "⚠️ La descarga de '$model_name' se interrumpió (posible EOF/red lenta). Reintentando en 5 segundos..."
      sleep 5
      attempt=$((attempt + 1))
    fi
  done

  echo "❌ Error crítico: No se pudo descargar el modelo '$model_name' tras $max_attempts intentos."
  exit 1
}

# Descargar modelo de evaluación si usa Ollama
if [ "$EVAL_ENGINE" = "ollama" ]; then
  echo "-> [Evaluate] Procesando modelo local: $EVAL_MODEL"
  pull_model_with_retry "$EVAL_MODEL"
fi

# Descargar modelo de escritura si usa Ollama (evitando duplicar si usa el mismo modelo)
if [ "$WRITE_ENGINE" = "ollama" ]; then
  if [ "$WRITE_MODEL" = "$EVAL_MODEL" ] && [ "$EVAL_ENGINE" = "ollama" ]; then
    echo "-> [Write] El modelo de escritura es idéntico al de evaluación ($WRITE_MODEL), no es necesario descargarlo de nuevo."
  else
    echo "-> [Write] Procesando modelo local: $WRITE_MODEL"
    pull_model_with_retry "$WRITE_MODEL"
  fi
fi

echo "¡Todos los modelos de Ollama necesarios se han descargado correctamente!"