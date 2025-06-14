from django.shortcuts import render
from django.conf import settings
import subprocess
import os
import sys


def run_analysis(request):
    selected = request.GET.get('analysis', '')
    image_file = None
    error = None

    if selected in ['spx', 'ndx']:
        try:
            # Get the directory where views.py is located
            views_dir = os.path.dirname(__file__)
            script_path = os.path.join(views_dir, f"{selected}.py")

            # Create the static directory path that matches your script
            static_dir = os.path.join(views_dir, 'static')

            # Ensure the static directory exists
            os.makedirs(static_dir, exist_ok=True)

            # Run the script with the correct working directory
            # Pass the static directory as an environment variable
            env = os.environ.copy()
            env['DJANGO_STATIC_DIR'] = static_dir

            result = subprocess.run(
                [sys.executable, script_path],
                check=True,
                cwd=views_dir,  # Set working directory to views directory
                env=env,
                capture_output=True,
                text=True
            )

            print(f"Script output: {result.stdout}")
            if result.stderr:
                print(f"Script stderr: {result.stderr}")

            # Look for generated image files
            if os.path.exists(static_dir):
                files = sorted(
                    [f for f in os.listdir(static_dir) if f.startswith(selected) and f.endswith('.png')],
                    key=lambda x: os.path.getmtime(os.path.join(static_dir, x)),
                    reverse=True
                )
                if files:
                    image_file = files[0]
                    print(f"Found image file: {image_file}")
                else:
                    error = "No image files generated"
            else:
                error = f"Static directory not found: {static_dir}"

        except subprocess.CalledProcessError as e:
            error = f"Script error: {str(e)}\nStdout: {e.stdout}\nStderr: {e.stderr}"
        except Exception as e:
            error = f"Other error: {str(e)}"

    return render(request, 'result.html', {
        'image_file': image_file,
        'selected': selected,
        'error': error
    })