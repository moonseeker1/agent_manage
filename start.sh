#!/bin/bash
cd /mnt/pzm/open-claude-ui/backend
/usr/local/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
