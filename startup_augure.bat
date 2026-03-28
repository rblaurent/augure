@echo off
REM Script de démarrage Augure
REM À placer dans shell:startup ou configurer comme tâche planifiée

echo Démarrage de ComfyUI...
start "" "T:\Projects\ComfyUI\run_comfyui.bat"

REM Attendre que ComfyUI soit prêt (15 secondes)
timeout /t 15 /nobreak

echo Démarrage du bot Augure...
cd /d "%~dp0"
docker-compose up -d

echo Augure démarré.
