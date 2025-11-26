// Interactive Login Page Behaviors
(function () {
  const form = document.querySelector('#login-form');
  const email = document.querySelector('#login-email');
  const password = document.querySelector('#login-password');
  const btn = document.querySelector('#login-submit');
  const card = document.querySelector('#login-card');
  const toggle = document.querySelector('#toggle-password');
  const starsContainer = document.querySelector('.stars');
  const emailMsg = document.querySelector('#email-msg');
  const passMsg = document.querySelector('#pass-msg');

  const supportsReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function validateEmail(value) {
    if (!value) return { ok: false, msg: 'Email is required.' };
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const ok = re.test(value.trim());
    return { ok, msg: ok ? 'Looks good.' : 'Enter a valid email.' };
  }

  function validatePassword(value) {
    if (!value) return { ok: false, msg: 'Password is required.' };
    const ok = value.length >= 4; // basic check
    return { ok, msg: ok ? '✓' : 'At least 4 characters.' };
  }

  function setValidation(input, msgEl, result) {
    input.classList.toggle('is-valid', result.ok);
    input.classList.toggle('is-invalid', !result.ok);
    input.setAttribute('aria-invalid', (!result.ok).toString());
    msgEl.textContent = result.msg;
    msgEl.dataset.state = result.ok ? 'success' : 'error';
  }

  if (email) {
    email.addEventListener('input', () => setValidation(email, emailMsg, validateEmail(email.value)));
    email.addEventListener('blur', () => setValidation(email, emailMsg, validateEmail(email.value)));
  }
  if (password) {
    password.addEventListener('input', () => setValidation(password, passMsg, validatePassword(password.value)));
    password.addEventListener('blur', () => setValidation(password, passMsg, validatePassword(password.value)));
  }

  // Button pulse by default
  if (btn && !supportsReducedMotion) {
    btn.classList.add('pulse');
  }

  // Submit: show loading spinner, success glow briefly, then submit
  if (form) {
    form.addEventListener('submit', (e) => {
      // If invalid, show shake and block submit briefly
      const emailRes = validateEmail(email.value);
      const passRes = validatePassword(password.value);
      setValidation(email, emailMsg, emailRes);
      setValidation(password, passMsg, passRes);
      if (!emailRes.ok || !passRes.ok) {
        e.preventDefault();
        card.classList.add('shake');
        setTimeout(() => card.classList.remove('shake'), 400);
        return;
      }

      btn.classList.add('loading');
      // Add success glow prior to navigation
      if (!supportsReducedMotion) {
        card.classList.add('success-glow');
        setTimeout(() => card.classList.remove('success-glow'), 600);
      }
    });
  }

  if (toggle && password) {
    toggle.addEventListener('click', () => {
      const isText = password.getAttribute('type') === 'text';
      password.setAttribute('type', isText ? 'password' : 'text');
      toggle.setAttribute('aria-pressed', (!isText).toString());
      const icon = toggle.querySelector('span');
      if (icon) {
        icon.classList.toggle('fa-eye', isText);
        icon.classList.toggle('fa-eye-slash', !isText);
      }
      toggle.setAttribute('aria-label', isText ? 'Show password' : 'Hide password');
      password.focus();
    });
  }

  if (starsContainer && !supportsReducedMotion) {
    const count = 50;
    const minDur = 5;
    const maxDur = 8;
    const minMove = 20;
    const maxMove = 50;
    for (let i = 0; i < count; i++) {
      const s = document.createElement('div');
      s.className = 'star';
      const left = Math.random() * 100;
      const bottom = Math.random() * 100;
      const dur = (Math.random() * (maxDur - minDur) + minDur).toFixed(2) + 's';
      const move = (Math.random() * (maxMove - minMove) + minMove).toFixed(0) + 'px';
      s.style.left = left + 'vw';
      s.style.bottom = bottom + 'px';
      s.style.setProperty('--star-move', move);
      s.style.animationDuration = dur + ', ' + dur;
      starsContainer.appendChild(s);
    }
  }

  // If server rendered an error alert, shake on load for feedback
  window.addEventListener('DOMContentLoaded', () => {
    const errorAlert = document.querySelector('.alert-danger');
    if (errorAlert && card) {
      card.classList.add('shake');
      setTimeout(() => card.classList.remove('shake'), 400);
    }
  });
})();