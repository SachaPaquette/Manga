import platform
import subprocess
from Config.config import ScriptConfig
from Config.logs_config import setup_logging

# Configure the logger
logger = setup_logging(ScriptConfig.SCRIPT_FILENAME,
                       ScriptConfig.SCRIPT_LOG_PATH)

class Scripts:

    def run_script(self):
        if platform.system().lower() == 'linux':
            # Run the linux installation script
            subprocess.run(['bash', ScriptConfig.linux_script])
        elif platform.system().lower() == 'windows':
            # Run the windows installation script
            subprocess.run(['powershell.exe', '-File', ScriptConfig.windows_script])
            self.install_python_package(ScriptConfig.window_curses)
        else:
            raise Exception(f"Unsupported operating system: {platform.system().lower()}")
        # Install the required python packages
        self.install_python_package()
        
    def install_python_package(self, package=None):
        # If a specific package is provided, install it
        if package:
            subprocess.run(['pip', 'install', package])
        else:
            # Install all the required packages
            subprocess.run(['pip', 'install', '-r',
                       ScriptConfig.requirements_file])
    
    def main(self):
        # Get the operating system
        # Run the appropriate script based on the operating system
        self.run_script()
        
