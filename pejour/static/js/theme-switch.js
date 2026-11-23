'use strict';

const themeForm = document.getElementById('theme-form');
const themeSwitch = themeForm.querySelector('[role="switch"]');
const themeStatus = themeForm.querySelector('[role="status"]');

function showTheme(theme) {
  if (theme === 'dark') document.documentElement.dataset.theme = 'dark';
  else delete document.documentElement.dataset.theme;
  themeSwitch.setAttribute('aria-checked', String(theme === 'dark'));
  themeForm.elements.theme.value = theme === 'dark' ? 'light' : 'dark';
}

themeForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (themeSwitch.disabled) return;
  const data = new FormData(themeForm);
  const next = data.get('theme');
  const previous = next === 'dark' ? 'light' : 'dark';
  themeSwitch.disabled = true;
  themeStatus.textContent = '';
  showTheme(next);
  try {
    const response = await fetch(themeForm.action, {
      method: 'POST', body: data, headers: { Accept: 'application/json' }
    });
    if (!response.ok || (await response.json()).theme !== next) {
      throw new Error('Theme save failed');
    }
  } catch {
    showTheme(previous);
    themeStatus.textContent = 'Could not save your theme. Refresh and try again.';
  } finally {
    themeSwitch.disabled = false;
  }
});
