/* ════════════════════════════════════════════════════════════
   main.js  –  Josiah Guenther Magic Website
   ════════════════════════════════════════════════════════════
   Site-wide JavaScript. Loaded by templates/base.html on every page.

   Contains:
     1. Reviews carousel (auto-rotating, Home page only)
     2. Contact form validation + AJAX submission (Contact page only)

   Both sections check for their target elements before running,
   so this single file is safe to load on every page.
   ════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', function () {
  initCarousel();
  initContactForm();
});

/* ═══════════════════════════════════════════════════════════
   1. REVIEWS CAROUSEL  (Home page)
═══════════════════════════════════════════════════════════ */
function initCarousel() {
  const track = document.getElementById('carouselTrack');
  if (!track) return; // Not on the home page — skip.

  const dotsContainer = document.getElementById('carouselDots');
  const cards = track.querySelectorAll('.review-card');
  const total = cards.length;

  let visible = getVisibleCount();
  let steps = Math.max(total - visible, 0);
  let index = 0;
  let timer = null;

  function getVisibleCount() {
    // Mirrors the card width set in style.css (.review-card flex-basis)
    const width = window.innerWidth;
    if (width <= 768) return 1;
    if (width <= 1024) return 2;
    return 3;
  }

  function buildDots() {
    dotsContainer.innerHTML = '';
    for (let i = 0; i <= steps; i++) {
      const dot = document.createElement('button');
      dot.className = 'carousel-dot' + (i === 0 ? ' active' : '');
      dot.type = 'button';
      dot.setAttribute('aria-label', 'Show review set ' + (i + 1));
      dot.addEventListener('click', () => goTo(i));
      dotsContainer.appendChild(dot);
    }
  }

  function goTo(newIndex) {
    index = Math.max(0, Math.min(newIndex, steps));
    const cardWidth = cards[0].offsetWidth + 24; // 24px = gap defined in CSS
    track.style.transform = `translateX(-${index * cardWidth}px)`;
    dotsContainer.querySelectorAll('.carousel-dot').forEach((dot, i) => {
      dot.classList.toggle('active', i === index);
    });
  }

  function advance() {
    goTo(index < steps ? index + 1 : 0);
  }

  function startTimer() {
    stopTimer();
    timer = setInterval(advance, 6500);
  }

  function stopTimer() {
    if (timer) clearInterval(timer);
  }

  function handleResize() {
    visible = getVisibleCount();
    const newSteps = Math.max(total - visible, 0);
    if (newSteps !== steps) {
      steps = newSteps;
      buildDots();
    }
    goTo(Math.min(index, steps));
  }

  // Pause the carousel while the browser tab is hidden (saves resources)
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      stopTimer();
    } else {
      startTimer();
    }
  });

  window.addEventListener('resize', handleResize);

  buildDots();
  goTo(0);
  startTimer();
}

/* ═══════════════════════════════════════════════════════════
   2. CONTACT FORM  (Contact page)
═══════════════════════════════════════════════════════════ */
function initContactForm() {
  const form = document.getElementById('contactForm');
  if (!form) return; // Not on the contact page — skip.

  const submitBtn          = document.getElementById('submitBtn');
  const successBanner      = document.getElementById('successBanner');
  const serverErrorBanner  = document.getElementById('serverErrorBanner');
  const serverErrorMsg     = document.getElementById('serverErrorMsg');

  // Field-by-field validation rules.
  // These mirror the validation performed again on the server in main.py —
  // client-side checks give instant feedback; server-side checks keep the
  // data trustworthy no matter what reaches the backend.
  const fields = [
    { id: 'firstName', errId: 'err-firstName', validate: v => v.trim().length > 0 },
    { id: 'lastName',  errId: 'err-lastName',  validate: v => v.trim().length > 0 },
    { id: 'email',     errId: 'err-email',     validate: v => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim()) },
    { id: 'phone',     errId: 'err-phone',     validate: v => v.trim().length >= 7 },
    { id: 'message',   errId: 'err-message',   validate: v => v.trim().length > 10 },
  ];

  function showFieldError(field) {
    const input = document.getElementById(field.id);
    const err   = document.getElementById(field.errId);
    input.classList.add('error');
    err.classList.add('visible');
    // Re-trigger the shake animation even on repeated invalid submits
    input.style.animation = 'none';
    void input.offsetHeight; // force reflow
    input.style.animation = '';
  }

  function clearFieldError(field) {
    const input = document.getElementById(field.id);
    const err   = document.getElementById(field.errId);
    input.classList.remove('error');
    err.classList.remove('visible');
  }

  function validateAll() {
    let valid = true;
    fields.forEach(field => {
      const input = document.getElementById(field.id);
      if (!field.validate(input.value)) {
        showFieldError(field);
        valid = false;
      } else {
        clearFieldError(field);
      }
    });
    return valid;
  }

  // Clear a field's error as soon as the visitor starts fixing it
  fields.forEach(field => {
    const input = document.getElementById(field.id);
    input.addEventListener('input', () => clearFieldError(field));
  });

  form.addEventListener('submit', async function (e) {
    e.preventDefault();

    successBanner.classList.remove('visible');
    serverErrorBanner.classList.remove('visible');

    if (!validateAll()) return;

    const payload = {
      firstName: document.getElementById('firstName').value.trim(),
      lastName:  document.getElementById('lastName').value.trim(),
      email:     document.getElementById('email').value.trim(),
      phone:     document.getElementById('phone').value.trim(),
      message:   document.getElementById('message').value.trim(),
    };

    submitBtn.disabled = true;
    submitBtn.textContent = 'Sending…';

    try {
      const response = await fetch('/send-email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const result = await response.json();

      if (response.ok && result.success) {
        successBanner.classList.add('visible');
        form.reset();
        submitBtn.textContent = 'Sent ✓';
      } else if (result.errors) {
        // Server-side validation caught something the client missed
        fields.forEach(field => {
          if (result.errors[field.id]) {
            showFieldError(field);
          }
        });
        submitBtn.disabled = false;
        submitBtn.textContent = 'Send Inquiry';
      } else {
        serverErrorMsg.textContent = result.error || 'Something went wrong. Please try again.';
        serverErrorBanner.classList.add('visible');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Send Inquiry';
      }
    } catch (err) {
      console.error('Contact form submission error:', err);
      serverErrorMsg.textContent = 'Could not reach the server. Please check your connection and try again.';
      serverErrorBanner.classList.add('visible');
      submitBtn.disabled = false;
      submitBtn.textContent = 'Send Inquiry';
    }
  });
}
