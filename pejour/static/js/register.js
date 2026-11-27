'use strict';

// Submit in place: passwords and recovery answers stay only in the current DOM.
// No localStorage, sessionStorage, cookie, URL or server draft stores them.
const registration = document.querySelector('#registration-form');
registration.addEventListener('submit', async event => {
  event.preventDefault();
  const button = registration.querySelector('button[type="submit"]');
  button.disabled = true;
  const original = button.textContent;
  button.textContent = 'Creating your account…';
  document.querySelectorAll('.field-error').forEach(node => {
    node.textContent = '';
  });
  const summary = document.querySelector('#form-error');
  summary.hidden = true;
  try {
    const response = await fetch('/register', {
      method: 'POST',
      headers: {
        Accept: 'application/json'
      },
      credentials: 'same-origin',
      body: new FormData(registration)
    });
    const data = await response.json();
    if (data.ok) {
      location.assign(data.redirect);
      return;
    }
    if (data.csrf) {
      registration.querySelector('[name="csrf"]').value = data.csrf;
      document.querySelector('meta[name="csrf-token"]').content = data.csrf;
    }
    const errors = data.errors || {
      _form: 'Registration could not be completed. Please try again.'
    };
    for (const [key, value] of Object.entries(errors)) {
      const output = document.getElementById('error-' + key);
      if (output) {
        output.textContent = value;
        document.getElementById(key)?.setAttribute('aria-invalid', 'true');
      }
    }
    summary.textContent = errors._form || 'Please correct the marked fields. Your password and recovery answers are still in this page.';
    summary.hidden = false;
    const first = Object.keys(errors).map(key => document.getElementById(key)).find(Boolean);
    const errorStep = panels.indexOf(first?.closest('fieldset'));
    if (errorStep >= 0) showStep(errorStep, false);
    (first || summary).scrollIntoView({
      block: 'center',
      behavior: 'smooth'
    });
    first?.focus();
  } catch (error) {
    summary.textContent = 'The server could not be reached. Your details remain in this page. Please try again.';
    summary.hidden = false;
  } finally {
    document.querySelector('#captcha-image').src = '/captcha?t=' + Date.now();
    document.querySelector('#captcha').value = '';
    document.querySelector('#consent').checked = false;
    button.disabled = false;
    button.textContent = original;
  }
});

// Keep every step in the same form so Back preserves the entered values.
const panels = Array.from(registration.querySelectorAll('fieldset'));
const groups = [0, 1, 2, 2, 3, 3];
const previous = document.querySelector('#previous-step');
const next = document.querySelector('#next-step');
const submit = registration.querySelector('[type="submit"]');
let step = 0;
function showStep(index, focusHeading = true) {
  step = index;
  panels.forEach((panel, i) => {
    panel.hidden = i !== step;
  });
  previous.hidden = step === 0;
  next.hidden = step === panels.length - 1;
  submit.hidden = !next.hidden;
  document.querySelectorAll('.step-list li').forEach((item, i) => {
    if (i === groups[step]) item.setAttribute('aria-current', 'step');else item.removeAttribute('aria-current');
  });
  if (focusHeading) {
    const heading = panels[step].querySelector('legend');
    heading.tabIndex = -1;
    heading.focus();
  }
}
function advance() {
  for (const input of panels[step].querySelectorAll('input,select,textarea')) {
    validate(input);
    if (!input.reportValidity()) return;
  }
  showStep(step + 1);
}
next.addEventListener('click', advance);
previous.addEventListener('click', () => showStep(step - 1));
registration.addEventListener('keydown', event => {
  if (event.key === 'Enter' && event.target.matches('input') && !next.hidden) {
    event.preventDefault();
    advance();
  }
});
registration.addEventListener('invalid', event => {
  const index = panels.indexOf(event.target.closest('fieldset'));
  if (index >= 0 && panels[index].hidden) showStep(index, false);
}, true);
showStep(0, false);

// Show examples inside the registration fields.
const registrationPlaceholders = {
  id: "e.g. 2026-1234",
  first_name: "e.g. Juan",
  middle_name: "e.g. Santos",
  family_name: "e.g. Dela Cruz",
  extension_other: "e.g. III",
  age: "Calculated from your birthdate",

  street: "e.g. Purok Uno",
  barangay: "e.g. Mabini",
  city: "e.g. Cabadbaran City",
  province: "e.g. Agusan Del Norte",
  country: "e.g. Philippines",
  zip_code: "e.g. 8605",

  email: "e.g. juan@example.com",
  username: "e.g. JuanDelaCruz26",
  password: "Create your password",
  password_confirm: "Type your password again",
  answer_1: "Enter your answer",
  answer_2: "Enter your answer",
  answer_3: "Enter your answer",

  display_name: "e.g. Juan",
  intention: "e.g. I want to write about what I learn each day.",
  captcha: "Type the code shown"
};

for (const [name, example] of Object.entries(registrationPlaceholders)) {
  const field = document.querySelector(`#registration-form [name="${name}"]`);
  if (field) {
    field.placeholder = example;
  }
}