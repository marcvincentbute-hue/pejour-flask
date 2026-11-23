'use strict';
// Submit in place: passwords and recovery answers stay only in the current DOM.
// No localStorage, sessionStorage, cookie, URL or server draft stores them.
const registration=document.querySelector('#registration-form');
registration.addEventListener('submit',async event=>{
  event.preventDefault();const button=registration.querySelector('button[type="submit"]');button.disabled=true;const original=button.textContent;button.textContent='Creating your account…';
  document.querySelectorAll('.field-error').forEach(node=>{node.textContent='';});
  const summary=document.querySelector('#form-error');summary.hidden=true;
  try{
    const response=await fetch('/register',{method:'POST',headers:{Accept:'application/json'},credentials:'same-origin',body:new FormData(registration)});
    const data=await response.json();if(data.ok){location.assign(data.redirect);return;}
    if(data.csrf){registration.querySelector('[name="csrf"]').value=data.csrf;document.querySelector('meta[name="csrf-token"]').content=data.csrf;}
    const errors=data.errors||{_form:'Registration could not be completed. Please try again.'};
    for(const [key,value]of Object.entries(errors)){const output=document.getElementById('error-'+key);if(output){output.textContent=value;document.getElementById(key)?.setAttribute('aria-invalid','true');}}
    summary.textContent=errors._form||'Please correct the marked fields. Your password and recovery answers are still in this page.';summary.hidden=false;
    const first=Object.keys(errors).map(key=>document.getElementById(key)).find(Boolean);(first||summary).scrollIntoView({block:'center',behavior:'smooth'});first?.focus();
  }catch(error){summary.textContent='The server could not be reached. Your details remain in this page. Please try again.';summary.hidden=false;}
  finally{document.querySelector('#captcha-image').src='/captcha?t='+Date.now();document.querySelector('#captcha').value='';document.querySelector('#consent').checked=false;button.disabled=false;button.textContent=original;}
});
