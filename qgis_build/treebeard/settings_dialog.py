from PyQt5.QtWidgets import QDialog, QVBoxLayout, QCheckBox, QPushButton

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Treebeard Settings")

        # Layout and Widgets
        layout = QVBoxLayout()

        self.buffer_checkbox = QCheckBox("Enable Buffering")
        self.buffer_checkbox.setChecked(True)  # Default to enabled
        layout.addWidget(self.buffer_checkbox)

        self.png_checkbox = QCheckBox("Generate PNG Files")
        self.png_checkbox.setChecked(True)  # Default to enabled
        layout.addWidget(self.png_checkbox)

        # Buttons
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        layout.addWidget(self.ok_button)

        self.setLayout(layout)

    def get_settings(self):
        """Returns the settings selected by the user."""
        return {
            "buffering_enabled": self.buffer_checkbox.isChecked(),
            "png_generation_enabled": self.png_checkbox.isChecked(),
        }
