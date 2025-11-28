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

ROOT_DIR = Path(__file__).parent.parent.absolute()
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build"


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
    spec_file = ROOT_DIR / "app.spec"
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


def build_executable():
    """
    create standalone executable
    """
    print("building executable")
    
    # ---------- BUILD COMMAND ----------
    cmd = [
        sys.executable,
        '-m', 'PyInstaller',
        '--onefile',
        '--windowed',
        '--name', 'Stocksight',
        '--add-data', f'data{os.pathsep}data',
        '--add-data', f'utils{os.pathsep}utils',
        '--hidden-import', 'pandas',
        '--hidden-import', 'numpy',
        '--hidden-import', 'matplotlib',
        '--hidden-import', 'autots',
        '--hidden-import', 'dearpygui',
        '--hidden-import', 'sklearn',
        '--hidden-import', 'statsmodels',
        '--hidden-import', 'openpyxl',
        '--hidden-import', 'xlrd',
        str(ROOT_DIR / 'app.py')
    ]
    
    # ---------- RUN BUILD ----------
    result = subprocess.run(cmd, cwd=ROOT_DIR)
    
    if result.returncode == 0:
        print("build successful")
        print(f"executable: {DIST_DIR / 'Stocksight.exe'}")
    else:
        print("build failed")
    
    return result.returncode == 0


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
    
    # ---------- COPY SAMPLE DATA ----------
    sample_csv = ROOT_DIR / "data" / "inventory.csv"
    if sample_csv.exists():
        shutil.copy(sample_csv, dist_data)
    
    # ---------- COPY README ----------
    readme = ROOT_DIR / "README.md"
    if readme.exists():
        shutil.copy(readme, DIST_DIR)
    
    print("resources copied")


def create_archive():
    """
    create distribution archive
    """
    print("creating archive")
    
    archive_name = ROOT_DIR / "Stocksight_dist"
    shutil.make_archive(archive_name, 'zip', DIST_DIR)
    
    print(f"archive created: {archive_name}.zip")


# ================ MAIN ================

def main():
    """
    run full build process
    """
    print("=" * 50)
    print("STOCKSIGHT BUILD SCRIPT")
    print("=" * 50)
    
    # ---------- CHECK REQUIREMENTS ----------
    if not check_pyinstaller():
        sys.exit(1)
    
    # ---------- CLEAN ----------
    clean_build()
    
    # ---------- BUILD ----------
    if not build_executable():
        sys.exit(1)
    
    # ---------- COPY RESOURCES ----------
    copy_resources()
    
    # ---------- CREATE ARCHIVE ----------
    create_archive()
    
    print("=" * 50)
    print("BUILD COMPLETE")
    print("=" * 50)


if __name__ == "__main__":
    main()