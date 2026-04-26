import sys, os
os.chdir('/var/www/html/GYMNight')
sys.path.insert(0, '.')
from ui.screens import active_workout
import inspect
src = inspect.getsource(active_workout.ActiveWorkoutScreen._build)
print("HAS_CARDIO:", 'cardio' in src.lower())
print("HAS_BORDER_RADIUS:", 'border-radius' in src)
print("FILE:", active_workout.__file__)
