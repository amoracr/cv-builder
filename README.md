# Automated Job Search & ATS CV Generator

A modular Python/FastAPI backend designed to scrape multiple job sources, store offers in a local database, evaluate them via AI, and generate ATS-optimized custom PDF resumes.

## Features
- **Multi-source Scraper**: Modular architecture for platforms like Wellfound, We Work Remotely, and company career pages.
- **Database Tracking**: Persistent storage using SQLite and SQLModel to prevent duplicate applications.
- **AI-Driven Matching & Adaptation**: Supports multi-provider AI evaluation (choose between **Gemini** in the cloud or local LLMs via **Ollama**) to analyze job requirements against your core CV.
- **Markdown-Based CV**: Your base CV must be a clean Markdown file (`cv.md`), and it will included in Docker as a mount point.
- **ATS-Optimized PDF Generator**: Renders clean, text-selectable PDF resumes without formatting blocks that break ATS parsers.

---

## Configuration & Setup

### 1. Environment Configuration (`.env`)
The application uses an environment file to manage configurations. 
1. Locate the `env.example` file in the repository.
2. Create a copy of it and name it `.env`:
   ```bash
   cp env.example .env
   ```
3. Open your .env file and configure it for only one provider at a time (LLM_ENGINE=gemini or LLM_ENGINE=ollama).

## 2. Docker Override Setup (docker-compose.override.yml)

To map your local Markdown CV file and configure local hardware services, you need an override configuration:

1. Locate the docker-compose.override.example file in the repository.
2. Create a copy of it and name it docker-compose.override.yml:
    ```bash
    cp docker-compose.override.example docker-compose.override.yml
    ```
3. Open the new docker-compose.override.yml file to:

    * Set the full path to your local CV file for read-only volume mounting.
    * Configure Ollama & Hardware Acceleration: Review the built-in instructions and comments inside docker-compose.override.example to select, uncomment, and adjust the specific configuration matching your operating system and GPU (such as Linux AMD/ROCm, Linux NVIDIA, or Windows/macOS/CPU).

## 3. Running with Docker

Depending on whether you choose Gemini or Ollama, follow the instructions below:

### Option A: Using Google Gemini (Cloud API)

If you prefer using Gemini (cloud execution), you still use your `docker-compose.override.yml` to map your local CV file, but you don't need the local Ollama service:
1. Supply your API key in your `.env` file (`LLM_ENGINE=gemini` and `GEMINI_API_KEY=your_key`).
2. In your `docker-compose.override.yml`, make sure to set the path to your local CV file under the `backend` service, and **you can comment out or remove the entire `ollama` service block** (along with its global volume) to save local resources.
3. Build and start the container:
   ```bash
   docker compose up -d --build
   ```

### Option B: Using Local LLMs with Ollama

If you want to run everything locally using models like qwen2.5:7b:

1. Ensure your .env file is configured with LLM_ENGINE=ollama and your target model (OLLAMA_MODEL=qwen2.5:7b).
2. Verify that you have configured your docker-compose.override.yml following the hardware instructions provided in the example file.
3. Build and start the containers (Docker Compose will automatically pick up your override file and spin up both the backend app and the Ollama service):
    ```bash
    docker compose up -d --build
    ```
4. Once the containers are up and running, download your target model inside the Ollama container:
    ```bash
    bash pull-ollama-models.sh
    ```