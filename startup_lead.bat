@echo off
cd /d L:\charlie_lead
start "" python main.py
start "" ngrok http --domain=lead.ngrok.dev 7860
