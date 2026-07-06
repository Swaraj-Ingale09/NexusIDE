/* =====================================================
   NexusIDE — Premium AI Slider Component
   Advanced JavaScript for Slider Functionality
   ===================================================== */

class AISlider {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.slides = this.container.querySelectorAll('.ai-slide');
    this.indicators = this.container.querySelectorAll('.ai-indicator');
    this.prevBtn = this.container.querySelector('.ai-btn-prev');
    this.nextBtn = this.container.querySelector('.ai-btn-next');
    this.slidesTrack = this.container.querySelector('.ai-slider-slides');
    this.progressBar = this.container.querySelector('.ai-progress-bar');
    
    this.currentSlide = 0;
    this.autoPlayInterval = null;
    this.autoPlayDuration = 8000; // 8 seconds
    
    this.init();
  }

  init() {
    this.bindEvents();
    this.startAutoPlay();
  }

  bindEvents() {
    // Navigation buttons
    if (this.prevBtn) {
      this.prevBtn.addEventListener('click', () => this.prevSlide());
    }
    if (this.nextBtn) {
      this.nextBtn.addEventListener('click', () => this.nextSlide());
    }

    // Indicators
    this.indicators.forEach((indicator, index) => {
      indicator.addEventListener('click', () => this.goToSlide(index));
    });

    // Keyboard navigation
    document.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowLeft') this.prevSlide();
      if (e.key === 'ArrowRight') this.nextSlide();
    });

    // Pause auto-play on mouse enter, resume on mouse leave
    this.container.addEventListener('mouseenter', () => this.pauseAutoPlay());
    this.container.addEventListener('mouseleave', () => this.startAutoPlay());

    // Touch/Swipe support
    let startX = 0;
    this.slidesTrack.addEventListener('touchstart', (e) => {
      startX = e.touches[0].clientX;
    });

    this.slidesTrack.addEventListener('touchend', (e) => {
      const endX = e.changedTouches[0].clientX;
      if (startX - endX > 50) this.nextSlide();
      if (endX - startX > 50) this.prevSlide();
    });
  }

  goToSlide(index) {
    if (index >= this.slides.length) {
      this.currentSlide = 0;
    } else if (index < 0) {
      this.currentSlide = this.slides.length - 1;
    } else {
      this.currentSlide = index;
    }

    this.updateSlider();
    this.restartAutoPlay();
  }

  nextSlide() {
    this.goToSlide(this.currentSlide + 1);
  }

  prevSlide() {
    this.goToSlide(this.currentSlide - 1);
  }

  updateSlider() {
    // Move slides
    const offset = -this.currentSlide * 100;
    this.slidesTrack.style.transform = `translateX(${offset}%)`;

    // Update indicators
    this.indicators.forEach((indicator, index) => {
      indicator.classList.toggle('active', index === this.currentSlide);
    });

    // Update progress bar
    this.progressBar.classList.remove('active');
    // Trigger reflow to restart animation
    void this.progressBar.offsetWidth;
    this.progressBar.classList.add('active');

    // Update button states
    if (this.prevBtn) {
      this.prevBtn.disabled = false;
    }
    if (this.nextBtn) {
      this.nextBtn.disabled = false;
    }

    // Add entrance animations to slide content
    this.animateSlideContent();
  }

  animateSlideContent() {
    // Get current slide content elements
    const currentSlide = this.slides[this.currentSlide];
    const contentElements = currentSlide.querySelectorAll('[data-animate]');

    contentElements.forEach((element, index) => {
      // Reset animation
      element.style.animation = 'none';
      // Trigger reflow
      void element.offsetWidth;
      // Apply animation
      const delay = index * 0.1;
      element.style.animation = `slideIn 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) ${delay}s forwards`;
    });
  }

  startAutoPlay() {
    this.autoPlayInterval = setInterval(() => {
      this.nextSlide();
    }, this.autoPlayDuration);
  }

  pauseAutoPlay() {
    clearInterval(this.autoPlayInterval);
  }

  restartAutoPlay() {
    this.pauseAutoPlay();
    this.startAutoPlay();
  }

  destroy() {
    this.pauseAutoPlay();
    if (this.prevBtn) {
      this.prevBtn.removeEventListener('click', () => this.prevSlide());
    }
    if (this.nextBtn) {
      this.nextBtn.removeEventListener('click', () => this.nextSlide());
    }
  }
}

// Initialize slider when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  const slider = new AISlider('ai-slider');
});
