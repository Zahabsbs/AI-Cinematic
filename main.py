import sys
import os
import subprocess
from PyQt5 import QtWidgets, QtCore
from video_processor import VideoProcessor

class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI-Cinematic")
        self.input_video_path = ""
        self.output_video_path = "processed_video.mp4"
        # Сопоставление названий стилей с путями к LUT-файлам (не забудь создать папку luts и положить туда примеры)
        self.lut_mapping = {
            "Нео-нуар": "luts/neo_noir.png",
            "Ретро": "luts/retro.png",
            "Блокбастер": "luts/blockbuster.png"
        }
        self.init_ui()

    def init_ui(self):
        self.video_label = QtWidgets.QLabel("Выберите видео для обработки")
        self.video_label.setAlignment(QtCore.Qt.AlignCenter)

        self.select_button = QtWidgets.QPushButton("Выбрать видео")
        self.select_button.clicked.connect(self.select_video)

        self.style_combo = QtWidgets.QComboBox()
        self.style_combo.addItems(list(self.lut_mapping.keys()))

        self.process_button = QtWidgets.QPushButton("Обработать видео")
        self.process_button.clicked.connect(self.process_video)

        self.preview_button = QtWidgets.QPushButton("Предварительный просмотр")
        self.preview_button.clicked.connect(self.preview_video)
        self.preview_button.setEnabled(False)

        # Используем вертикальное расположение элементов
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.video_label)
        layout.addWidget(self.select_button)
        layout.addWidget(self.style_combo)
        layout.addWidget(self.process_button)
        layout.addWidget(self.preview_button)
        self.setLayout(layout)

    def select_video(self):
        options = QtWidgets.QFileDialog.Options()
        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Выберите видео файл", "", "Видео файлы (*.mp4 *.avi *.mov)", options=options)
        if file_name:
            self.input_video_path = file_name
            self.video_label.setText(f"Выбрано: {os.path.basename(file_name)}")

    def process_video(self):
        if not self.input_video_path:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Сначала выберите видео!")
            return
        style = self.style_combo.currentText()
        lut_path = self.lut_mapping.get(style)
        if not os.path.exists(lut_path):
            QtWidgets.QMessageBox.warning(self, "Ошибка", f"LUT-файл для стиля {style} не найден!")
            return

        self.video_label.setText("Обработка видео, пожалуйста подождите...")
        QtWidgets.QApplication.processEvents()

        try:
            processor = VideoProcessor(lut_path)
            processor.process_video(self.input_video_path, self.output_video_path)
            self.video_label.setText("Обработка завершена!")
            self.preview_button.setEnabled(True)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", f"Ошибка при обработке видео: {str(e)}")
            self.video_label.setText("Обработка не удалась.")

    def preview_video(self):
        if os.path.exists(self.output_video_path):
            # Открываем видео с помощью системного плеера
            if sys.platform.startswith('darwin'):
                subprocess.call(('open', self.output_video_path))
            elif os.name == 'nt':
                os.startfile(self.output_video_path)
            elif os.name == 'posix':
                subprocess.call(('xdg-open', self.output_video_path))
        else:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Обработанное видео не найдено!")

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.resize(400, 300)
    window.show()
    sys.exit(app.exec_())