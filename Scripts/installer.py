import platform
import subprocess
import sys
from pathlib import Path
from Config.config import ScriptConfig
from Config.logs_config import setup_logging

# Configure the logger
logger = setup_logging(ScriptConfig.SCRIPT_FILENAME, ScriptConfig.SCRIPT_LOG_PATH)

class Installer:
    def __init__(self):
        self.os_name = platform.system().lower()
        self.script_map = {
            "linux": ScriptConfig.linux_script,
            "windows": ScriptConfig.windows_script,
        }

    def run_script(self):
        """Run the platform-specific installation script."""
        script = self.script_map.get(self.os_name)
        if not script:
            logger.error(f"Unsupported operating system: {self.os_name}")
            raise Exception(f"Unsupported operating system: {self.os_name}")

        logger.info(f"Running installation script for {self.os_name}: {script}")
        try:
            if self.os_name == "linux":
                subprocess.run(["bash", script], check=True)
            elif self.os_name == "windows":
                subprocess.run(["powershell.exe", "-File", script], check=True)
            logger.info(f"Script executed successfully: {script}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running script {script}: {e}")
            raise

    def install_python_package(self, package=None):
        try:
            if package:
                subprocess.run([sys.executable, "-m", "pip", "install", package], check=True)
            
            requirements_file = Path(ScriptConfig.requirements_file)
            if requirements_file.is_file():
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
                    check=True,
                )
            else:
                logger.error(f"Requirements file not found: {requirements_file}")
                raise FileNotFoundError(f"Requirements file not found: {requirements_file}")
            logger.info("Package installation completed successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error during package installation: {e}")
            raise

    def run(self):
        try:
            self.run_script()
            self.install_python_package(ScriptConfig.windows_curse if self.os_name == "windows" else None)
        except Exception as e:
            logger.error(f"Installation process failed: {e}")
            raise
        logger.info("Installation process completed successfully.")
    
    def main(self):
        self.run()
        
