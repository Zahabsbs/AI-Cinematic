import cv2
import numpy as np
from moviepy.editor import VideoFileClip
import subprocess
import os

class VideoProcessor:
    def __init__(self, lut_path):
        # Загружаем LUT из указанного файла
        self.lut = self.load_lut(lut_path)

    def load_lut(self, lut_path):
        # Считываем LUT-файл с помощью OpenCV
        lut_img = cv2.imread(lut_path)
        if lut_img is None:
            raise ValueError(f"Не удалось загрузить LUT из файла: {lut_path}")
        # Для простоты предполагаем, что LUT должен иметь размер 256x1 пиксель
        lut_img = cv2.resize(lut_img, (256, 1))
        # Приводим LUT к виду массива (256, 3)
        lut = lut_img.reshape(256, 3)
        lut = lut.astype(np.uint8)
        return lut

    def apply_lut(self, frame):
        # Преобразуем кадр из RGB в BGR (OpenCV работает с BGR)
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        # Разбиваем на каналы и применяем LUT к каждому каналу
        channels = cv2.split(frame_bgr)
        processed_channels = []
        for i, ch in enumerate(channels):
            # Функция cv2.LUT применяет преобразование по таблице для каждого канала
            processed = cv2.LUT(ch, self.lut[:, i])
            processed_channels.append(processed)
        frame_bgr = cv2.merge(processed_channels)
        # Возвращаем обратно в RGB
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        return frame_rgb

    def sharpen(self, frame):
        # Простой фильтр резкости – можно менять коэффициенты по своему усмотрению
        kernel = np.array([[0, -1, 0],
                           [-1, 5, -1],
                           [0, -1, 0]])
        sharpened = cv2.filter2D(frame, -1, kernel)
        return sharpened

    def cinematic_blur(self, frame):
        # Применяем небольшое размытие гауссом, чтобы смягчить изображение и добавить эффект глубины
        blurred = cv2.GaussianBlur(frame, (5, 5), 0)
        # Смешиваем оригинал с размытым изображением (70% оригинала и 30% размытого)
        blended = cv2.addWeighted(frame, 0.7, blurred, 0.3, 0)
        return blended

    def process_frame(self, frame):
        # Обрабатываем каждый кадр: цветокоррекция, затем резкость и эффект блюра
        frame = self.apply_lut(frame)
        frame = self.sharpen(frame)
        frame = self.cinematic_blur(frame)
        return frame

    def process_video(self, input_path, output_path):
        # Загружаем исходное видео с помощью MoviePy
        clip = VideoFileClip(input_path)
        # Применяем функцию обработки ко всем кадрам
        processed_clip = clip.fl_image(self.process_frame)
        # Сохраняем промежуточное видео с 24 fps для киношного эффекта
        temp_output = "temp_video.mp4"
        processed_clip.write_videofile(temp_output, fps=24, audio=True)
        clip.close()
        processed_clip.close()
        # Обрабатываем аудио дорожку с помощью ffmpeg (шумоподавление и реверберация)
        self.optimize_audio(temp_output, output_path)
        # Удаляем временный файл
        if os.path.exists(temp_output):
            os.remove(temp_output)

    def optimize_audio(self, input_video, output_video):
        # Команда ffmpeg: afftdn для шумоподавления и aecho для эхо-эффекта
        command = [
            "ffmpeg", "-y", "-i", input_video,
            "-af", "afftdn, aecho=0.8:0.88:60:0.4",
            "-c:v", "copy",
            output_video
        ]
        subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)