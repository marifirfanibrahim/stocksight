"""
build script for packaging
create standalone executable
bundle application for distribution
"""


# ================ IMPORTS ================

import os
import sys
import shutil
import subprocess
from pathlib import Path


# ================ PATHS ================

# stocksight directory (where build.py lives)
STOCKSIGHT_DIR = Path(__file__).parent.absolute()

# project root (parent of stocksight)
PROJECT_ROOT = STOCKSIGHT_DIR.parent

# output directories
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"


# ================ BUILD FUNCTIONS ================

def clean_build():
    """
    remove previous build artifacts
    """
    print("cleaning build directories")
    
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    
    # ---------- REMOVE SPEC FILE ----------
    spec_file = PROJECT_ROOT / "Stocksight.spec"
    if spec_file.exists():
        spec_file.unlink()
    
    print("clean complete")


def check_pyinstaller():
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


def check_dependencies():
    """
    verify required packages installed
    """
    required = [
        'pandas',
        'numpy', 
        'matplotlib',
        'autots',
        'dearpygui',
        'sklearn',
        'statsmodels',
        'openpyxl'
    ]
    
    missing = []
    
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    
    if missing:
        print(f"missing packages: {missing}")
        print(f"install with: pip install {' '.join(missing)}")
        return False
    
    print("all dependencies found")
    return True


def build_executable():
    """
    create standalone executable
    """
    print("building executable")
    
    # ---------- ENTRY POINT ----------
    entry_point = STOCKSIGHT_DIR / "app.py"
    
    if not entry_point.exists():
        print(f"entry point not found: {entry_point}")
        return False
    
    # ---------- DATA DIRECTORIES ----------
    data_dir = STOCKSIGHT_DIR / "data"
    utils_dir = STOCKSIGHT_DIR / "utils"
    ui_dir = STOCKSIGHT_DIR / "ui"
    core_dir = STOCKSIGHT_DIR / "core"
    
    # ---------- BUILD COMMAND ----------
    cmd = [
        sys.executable,
        '-m', 'PyInstaller',
        '--onefile',
        '--windowed',
        '--name', 'Stocksight',
        
        # ---------- HIDDEN IMPORTS ----------
        '--hidden-import', 'pandas',
        '--hidden-import', 'numpy',
        '--hidden-import', 'matplotlib',
        '--hidden-import', 'matplotlib.backends.backend_agg',
        '--hidden-import', 'autots',
        '--hidden-import', 'dearpygui',
        '--hidden-import', 'dearpygui.dearpygui',
        '--hidden-import', 'sklearn',
        '--hidden-import', 'sklearn.preprocessing',
        '--hidden-import', 'sklearn.utils',
        '--hidden-import', 'statsmodels',
        '--hidden-import', 'statsmodels.tsa',
        '--hidden-import', 'openpyxl',
        '--hidden-import', 'xlrd',
        '--hidden-import', 'concurrent.futures',
        '--hidden-import', 'multiprocessing',
        '--hidden-import', 'threading',
        '--hidden-import', 'pickle',
        '--hidden-import', 'json',
        '--hidden-import', 'calendar',
        '--hidden-import', 'gc',
        
        # ---------- COLLECT SUBMODULES ----------
        '--collect-submodules', 'autots',
        '--collect-submodules', 'statsmodels',
        '--collect-submodules', 'sklearn',
        '--collect-submodules', 'dearpygui',
        
        # ---------- ENTRY POINT ----------
        str(entry_point)
    ]
    
    # ---------- ADD DATA DIRECTORIES IF EXIST ----------
    if data_dir.exists():
        cmd.extend(['--add-data', f'{data_dir}{os.pathsep}data'])
    
    if utils_dir.exists():
        cmd.extend(['--add-data', f'{utils_dir}{os.pathsep}utils'])
    
    if ui_dir.exists():
        cmd.extend(['--add-data', f'{ui_dir}{os.pathsep}ui'])
    
    if core_dir.exists():
        cmd.extend(['--add-data', f'{core_dir}{os.pathsep}core'])
    
    # ---------- ADD CONFIG ----------
    config_file = STOCKSIGHT_DIR / "config.py"
    if config_file.exists():
        cmd.extend(['--add-data', f'{config_file}{os.pathsep}.'])
    
    # ---------- RUN BUILD ----------
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
    print("copying resources")
    
    # ---------- CREATE DIRECTORIES ----------
    dist_data = DIST_DIR / "data"
    dist_output = DIST_DIR / "output"
    
    os.makedirs(dist_data, exist_ok=True)
    os.makedirs(dist_output, exist_ok=True)
    
    # # ---------- COPY SAMPLE DATA ----------
    # sample_csv = STOCKSIGHT_DIR / "data" / "inventory.csv"
    # if sample_csv.exists():
    #     shutil.copy(sample_csv, dist_data)
    #     print(f"copied: {sample_csv.name}")
    
    # # ---------- COPY README ----------
    # readme = PROJECT_ROOT / "README.md"
    # if readme.exists():
    #     shutil.copy(readme, DIST_DIR)
    #     print(f"copied: {readme.name}")
    
    # # ---------- COPY LICENSE ----------
    # license_file = PROJECT_ROOT / "LICENSE"
    # if license_file.exists():
    #     shutil.copy(license_file, DIST_DIR)
    #     print(f"copied: {license_file.name}")
    
    print("resources copied")


def create_archive():
    """
    create distribution archive
    """
    print("creating archive")
    
    archive_name = PROJECT_ROOT / "Stocksight_dist"
    shutil.make_archive(str(archive_name), 'zip', DIST_DIR)
    
    archive_path = Path(str(archive_name) + ".zip")
    print(f"archive created: {archive_path}")
    print(f"archive size: {archive_path.stat().st_size / (1024*1024):.1f} MB")


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
    
    # ---------- CHECK REQUIREMENTS ----------
    if not check_pyinstaller():
        sys.exit(1)
    
    if not check_dependencies():
        sys.exit(1)
    
    # ---------- CLEAN ----------
    clean_build()
    
    # ---------- BUILD ----------
    if not build_executable():
        sys.exit(1)
    
    # ---------- COPY RESOURCES ----------
    copy_resources()
    
    # ---------- CREATE RUN SCRIPT ----------
    create_run_script()
    
    # ---------- CREATE ARCHIVE ----------
    create_archive()
    
    print("=" * 50)
    print("BUILD COMPLETE")
    print("=" * 50)
    print(f"output: {DIST_DIR}")
    print("=" * 50)


if __name__ == "__main__":
    main()