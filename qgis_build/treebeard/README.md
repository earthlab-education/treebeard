## Setup Instructions

### For Windows:
1. Ensure Python and pip are installed.
2. Navigate to the plugin directory.
3. Double-click `setup.bat` to run the setup script.
4. Follow the on-screen instructions.
5. Restart QGIS to ensure the new environment is activated.

### For macOS/Linux:
1. Ensure Python and pip are installed.
2. Open a terminal and navigate to the plugin directory.
3. Run `sh setup.sh` to execute the setup script.
4. Follow the on-screen instructions.
5. Restart QGIS to ensure the new environment is activated.

### Verifying the Environment:
1. Open QGIS.
2. Go to `Plugins` > `Python Console`.
3. Enter the following commands to verify the environment:
   ```python
   import sys
   print(sys.executable)
   print(sys.path)
