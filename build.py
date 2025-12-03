"""
build script for pyqt6 application
create standalone executable
"""


# ================ IMPORTS ================

import os
import sys
import shutil
import subprocess
from pathlib import Path


# ================ PATHS ================

STOCKSIGHT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = STOCKSIGHT_DIR.parent
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"


# ================ BUILD FUNCTIONS ================

def clean_build():
    """
    remove previous build artifacts
    """
    print("cleaning build directories...")
    
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    
    spec_file = PROJECT_ROOT / "Stocksight.spec"
    if spec_file.exists():
        spec_file.unlink()
    
    print("clean complete")


def check_pyinstaller() -> bool:
    """
    verify pyinstaller installed
    """
    try:
        import PyInstaller
        print(f"pyinstaller version: {PyInstaller.__version__}")
        return True
    except ImportError:
        print("pyinstaller not found")
        print("install with: pip install pyinstaller")
        return False


def check_dependencies() -> bool:
    """
    verify required packages installed
    """
    required = [
        'PyQt6',
        'pandas',
        'numpy',
        'matplotlib',
        'autots',
        'sklearn',
        'statsmodels',
        'openpyxl'
    ]
    
    optional = [
        'ydata_profiling',
        'autoviz',
        'tsfresh',
        'featuretools'
    ]
    
    missing = []
    
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    
    if missing:
        print(f"missing required packages: {missing}")
        print(f"install with: pip install {' '.join(missing)}")
        return False
    
    # check optional
    optional_missing = []
    for pkg in optional:
        try:
            __import__(pkg)
        except ImportError:
            optional_missing.append(pkg)
    
    if optional_missing:
        print(f"optional packages not installed: {optional_missing}")
        print("these features will be disabled in the build")
    
    print("all required dependencies found")
    return True


def build_executable() -> bool:
    """
    create standalone executable
    """
    print("building executable...")
    
    entry_point = STOCKSIGHT_DIR / "app.py"
    
    if not entry_point.exists():
        print(f"entry point not found: {entry_point}")
        return False
    
    # build command
    cmd = [
        sys.executable,
        '-m', 'PyInstaller',
        '--onefile',
        '--windowed',
        '--name', 'Stocksight',
        
        # ---------- PYQT6 ----------
        '--hidden-import', 'PyQt6',
        '--hidden-import', 'PyQt6.QtCore',
        '--hidden-import', 'PyQt6.QtGui',
        '--hidden-import', 'PyQt6.QtWidgets',
        '--hidden-import', 'PyQt6.sip',
        
        # ---------- DATA SCIENCE ----------
        '--hidden-import', 'pandas',
        '--hidden-import', 'numpy',
        '--hidden-import', 'matplotlib',
        '--hidden-import', 'matplotlib.backends.backend_qtagg',
        '--hidden-import', 'matplotlib.backends.backend_agg',
        
        # ---------- AUTOTS ----------
        '--hidden-import', 'autots',
        '--hidden-import', 'autots.models',
        '--hidden-import', 'autots.evaluator',
        
        # ---------- SKLEARN ----------
        '--hidden-import', 'sklearn',
        '--hidden-import', 'sklearn.preprocessing',
        '--hidden-import', 'sklearn.ensemble',
        '--hidden-import', 'sklearn.neighbors',
        
        # ---------- STATSMODELS ----------
        '--hidden-import', 'statsmodels',
        '--hidden-import', 'statsmodels.tsa',
        '--hidden-import', 'statsmodels.tsa.seasonal',
        
        # ---------- OPTIONAL ----------
        '--hidden-import', 'ydata_profiling',
        '--hidden-import', 'autoviz',
        '--hidden-import', 'tsfresh',
        '--hidden-import', 'featuretools',
        
        # ---------- STANDARD ----------
        '--hidden-import', 'openpyxl',
        '--hidden-import', 'xlrd',
        '--hidden-import', 'concurrent.futures',
        '--hidden-import', 'multiprocessing',
        '--hidden-import', 'threading',
        '--hidden-import', 'pickle',
        '--hidden-import', 'json',
        
        # ---------- COLLECT SUBMODULES ----------
        '--collect-submodules', 'autots',
        '--collect-submodules', 'statsmodels',
        '--collect-submodules', 'sklearn',
        '--collect-submodules', 'PyQt6',
        
        # ---------- ENTRY POINT ----------
        str(entry_point)
    ]
    
    # add data directories if exist
    for dir_name in ['data', 'utils', 'ui', 'core']:
        dir_path = STOCKSIGHT_DIR / dir_name
        if dir_path.exists():
            cmd.extend(['--add-data', f'{dir_path}{os.pathsep}{dir_name}'])
    
    # add config
    config_file = STOCKSIGHT_DIR / "config.py"
    if config_file.exists():
        cmd.extend(['--add-data', f'{config_file}{os.pathsep}.'])
    
    # run build
    print(f"running pyinstaller from: {PROJECT_ROOT}")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    
    if result.returncode == 0:
        print("build successful")
        exe_path = DIST_DIR / "Stocksight.exe"
        if exe_path.exists():
            print(f"executable: {exe_path}")
            print(f"size: {exe_path.stat().st_size / (1024*1024):.1f} MB")
        return True
    else:
        print("build failed")
        return False


def copy_resources():
    """
    copy additional resources to dist
    """
    print("copying resources...")
    
    # create directories
    dist_data = DIST_DIR / "data"
    dist_output = DIST_DIR / "output"
    dist_cache = DIST_DIR / "cache"
    dist_models = DIST_DIR / "models"
    
    for d in [dist_data, dist_output, dist_cache, dist_models]:
        d.mkdir(parents=True, exist_ok=True)
    
    print("resources copied")


def create_run_script():
    """
    create batch file to run the executable
    """
    batch_content = '''@echo off
cd /d "%~dp0"
Stocksight.exe
pause
'''
    
    batch_path = DIST_DIR / "Run_Stocksight.bat"
    with open(batch_path, 'w') as f:
        f.write(batch_content)
    
    print(f"created: {batch_path.name}")


def create_archive():
    """
    create distribution archive
    """
    print("creating archive...")
    
    archive_name = PROJECT_ROOT / "Stocksight_dist"
    shutil.make_archive(str(archive_name), 'zip', DIST_DIR)
    
    archive_path = Path(str(archive_name) + ".zip")
    print(f"archive created: {archive_path}")
    print(f"archive size: {archive_path.stat().st_size / (1024*1024):.1f} MB")


# ================ MAIN ================

def main():
    """
    run full build process
    """
    print("=" * 50)
    print("STOCKSIGHT BUILD SCRIPT")
    print("=" * 50)
    print(f"stocksight dir: {STOCKSIGHT_DIR}")
    print(f"project root: {PROJECT_ROOT}")
    print("=" * 50)
    
    # check requirements
    if not check_pyinstaller():
        sys.exit(1)
    
    if not check_dependencies():
        sys.exit(1)
    
    # clean
    clean_build()
    
    # build
    if not build_executable():
        sys.exit(1)
    
    # copy resources
    copy_resources()
    
    # create run script
    create_run_script()
    
    # create archive
    create_archive()
    
    print("=" * 50)
    print("BUILD COMPLETE")
    print("=" * 50)
    print(f"output: {DIST_DIR}")
    print("=" * 50)


if __name__ == "__main__":
    main()