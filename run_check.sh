#!/bin/bash
cd /var/www/html/GYMNight
source .venv/bin/activate
echo "=== Python path ==="
python -c "import sys; print('\n'.join(sys.path[:5]))"
echo "=== Active workout file ==="
python -c "import ui.screens.active_workout as m; print(m.__file__)"
echo "=== main.py location ==="
which python
pwd
