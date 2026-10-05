#!/bin/sh

# Cargar las variables del archivo .env si existe
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

MODEL=${OLLAMA_MODEL:-qwen2.5:3b}
PORT=${OLLAMA_PORT:-11434}

echo "Esperando a que Ollama esté listo en el puerto $PORT..."

# Esperar a que el servidor de Ollama responda
until wget -qO- http://localhost:$PORT/ >/dev/null 2>&1; do
  sleep 2
  echo "Esperando a que Ollama responda..."
done

echo "¡Ollama está activo en el contenedor!"
echo "-> Descargando modelo rápido dentro de Docker: $MODEL"
docker exec ollama_service ollama pull "$MODEL"

echo "¡Todos los modelos se han descargado correctamente!"