export function flashFrameAnimate(canvas, imageUrl) {
  const ctx = canvas.getContext('2d');
  const image = new Image();
  image.src = imageUrl;
  image.onload = () => {
    let startTime = null;
    
    function animate(timestamp) {
      if (!startTime) startTime = timestamp;
      const elapsed = timestamp - startTime;
      
      // Очищаем canvas
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      // Рисуем базовое изображение
      ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
      
      // Пример анимации моргания глаз: каждые 2 секунды на 200мс накладываем полупрозрачный слой.
      const blinkInterval = 2000;
      const blinkDuration = 200;
      if ((elapsed % blinkInterval) < blinkDuration) {
        ctx.fillStyle = 'rgba(0, 0, 0, 0.2)';
        ctx.fillRect(canvas.width * 0.3, canvas.height * 0.3, canvas.width * 0.15, canvas.height * 0.1);
        ctx.fillRect(canvas.width * 0.55, canvas.height * 0.3, canvas.width * 0.15, canvas.height * 0.1);
      }
      
      // Симуляция рябящего эффекта воды – лёгкий сдвиг синего оттенка в нижней части изображения.
      const waterOffset = Math.sin(elapsed / 500) * 5;
      ctx.fillStyle = 'rgba(0, 100, 255, 0.1)';
      ctx.fillRect(0, canvas.height * 0.8 + waterOffset, canvas.width, canvas.height * 0.2);
      
      // Анимация движущихся облаков – рисуем белый эллипс, движущийся по горизонтали.
      const cloudX = (elapsed / 50) % canvas.width;
      ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
      ctx.beginPath();
      ctx.ellipse(cloudX, canvas.height * 0.2, 30, 15, 0, 0, 2 * Math.PI);
      ctx.fill();
      
      // Симуляция покачивания объектов – небольшой поворот элемента в правом нижнем углу.
      const swayAngle = Math.sin(elapsed / 1000) * 0.1;
      ctx.save();
      ctx.translate(canvas.width * 0.8, canvas.height * 0.7);
      ctx.rotate(swayAngle);
      ctx.fillStyle = 'rgba(34,139,34,0.6)';
      ctx.fillRect(-10, -10, 20, 20);
      ctx.restore();
      
      // Эффект мерцающего света – создаём радиальный градиент в центре.
      const flicker = 0.5 + 0.5 * Math.sin(elapsed / 300);
      const gradient = ctx.createRadialGradient(canvas.width * 0.5, canvas.height * 0.5, 0, canvas.width * 0.5, canvas.height * 0.5, 50);
      gradient.addColorStop(0, `rgba(255, 255, 200, ${0.5 * flicker})`);
      gradient.addColorStop(1, 'rgba(255, 255, 200, 0)');
      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.arc(canvas.width * 0.5, canvas.height * 0.5, 50, 0, 2 * Math.PI);
      ctx.fill();
      
      // Пульсация цветов – накладываем красный цвет с меняющейся прозрачностью.
      const pulse = 0.5 + 0.5 * Math.sin(elapsed / 1000);
      ctx.fillStyle = `rgba(255, 0, 0, ${0.1 * pulse})`;
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      
      requestAnimationFrame(animate);
    }
    
    requestAnimationFrame(animate);
  };
  
  image.onerror = () => {
    console.error("Не удалось загрузить изображение для анимации.");
  };
}