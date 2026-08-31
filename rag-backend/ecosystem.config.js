module.exports = {
  apps: [
    {
      name: "rag-backend",
      script: ".venv311/Scripts/uvicorn",
      args: "app.main:app --host 0.0.0.0 --port 8000",
      interpreter: "none",
      watch: false,
      max_memory_restart: "1G",
      autorestart: true,
      restart_delay: 3000,
      env: {
        PORT: 8000
      }
    }
  ]
};
