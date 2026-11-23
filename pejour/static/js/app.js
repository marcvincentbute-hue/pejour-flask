'use strict';
const csrfToken=()=>document.querySelector('meta[name="csrf-token"]')?.content||'';
const captchaImage=document.querySelector('#captcha-image');
document.querySelector('#refresh-captcha')?.addEventListener('click',()=>{
  captchaImage.src='/captcha?t='+Date.now();const input=document.querySelector('#captcha');input.value='';input.focus();
});
document.querySelector('[data-show-password]')?.addEventListener('change',event=>{
  for(const input of document.querySelectorAll('input[name="password"],input[name="password_confirm"]')) input.type=event.target.checked?'text':'password';
});
const password=document.querySelector('#password');
function passwordStrength(value){const count=[/[a-z]/.test(value),/[A-Z]/.test(value),/[0-9]/.test(value),/[^A-Za-z0-9\s]/u.test(value)].filter(Boolean).length;const length=Array.from(value).length;return length<8||length>64||/\s/u.test(value)||count<3?'Weak':length>=14&&count===4?'Strong':'Medium';}
password?.addEventListener('input',()=>{const label=document.querySelector('#password-strength');if(label){const value=passwordStrength(password.value);label.textContent='Strength: '+value;label.className='strength strength-'+value.toLowerCase();}});
const birthdate=document.querySelector('#birthdate');
function calculateAge(){const out=document.querySelector('#age');if(!out)return;const date=new Date(birthdate.value+'T00:00:00');const today=new Date();let years=today.getFullYear()-date.getFullYear();if(today.getMonth()<date.getMonth()||(today.getMonth()===date.getMonth()&&today.getDate()<date.getDate()))years--;out.value=Number.isFinite(years)&&years>=0?years:'';}
birthdate?.addEventListener('change',calculateAge);if(birthdate)calculateAge();
for(const form of document.querySelectorAll('[data-lock-seconds]')){
  const end=Date.now()+Number(form.dataset.lockSeconds)*1000;
  const tick=()=>{const remaining=Math.max(0,Math.ceil((end-Date.now())/1000));for(const out of form.querySelectorAll('[data-lock-count]'))out.textContent=remaining;
    const message=form.querySelector('.lock-message');if(message)message.hidden=!remaining;
    for(const control of form.querySelectorAll('[data-lock-control]')){if(control.tagName==='A'){control.setAttribute('aria-disabled',remaining?'true':'false');control.tabIndex=remaining?-1:0;}
      else control.disabled=remaining>0;}};
  tick();setInterval(tick,1000);
}
const resend=document.querySelector('[data-resend]');if(resend){const end=Date.now()+Number(resend.dataset.resend)*1000;const tick=()=>{const left=Math.max(0,Math.ceil((end-Date.now())/1000));resend.disabled=left>0;document.querySelector('#resend-count').textContent=left?'Available in '+left+'s':'';};tick();setInterval(tick,1000);}
if(document.body.dataset.authenticated){
  const warning=document.querySelector('#idle-warning');let deadline=Date.now()+Number(document.body.dataset.idleSeconds)*1000;let busy=false;let lastTouch=0;let touchQueued=false;
  async function sync(touch=false){
    if(busy){if(touch)touchQueued=true;return;}busy=true;
    try{const response=await fetch('/session',{method:touch?'POST':'GET',headers:touch?{'X-CSRF-Token':csrfToken()}: {},credentials:'same-origin',cache:'no-store'});
      if(response.status===401){location.replace('/login');return;}if(!response.ok)throw new Error('Session check failed');
      const data=await response.json();deadline=Date.now()+data.remaining*1000;if(touch){lastTouch=Date.now();if(warning.open)warning.close();}}
    catch(error){/* The server remains authoritative; retry on the next check. */}
    finally{busy=false;if(touchQueued){touchQueued=false;sync(true);}}
  }
  const touch=()=>{if(Date.now()-lastTouch>30000&&!warning.open)sync(true);};
  document.addEventListener('pointerdown',touch);document.addEventListener('keydown',touch);
  document.querySelector('#stay-active')?.addEventListener('click',()=>sync(true));
  setInterval(()=>sync(false),15000);sync(false);
  setInterval(()=>{const left=Math.max(0,Math.ceil((deadline-Date.now())/1000));if(left<=0){location.replace('/login');return;}if(left<=60){document.querySelector('#idle-seconds').textContent=left;if(!warning.open)warning.showModal();}},1000);
  window.addEventListener('pageshow',event=>{if(event.persisted)location.reload();});
}
