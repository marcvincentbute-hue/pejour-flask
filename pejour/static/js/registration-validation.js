'use strict';
// This file mirrors Python registration rules. The server remains authoritative.
const form = document.querySelector('#registration-form');
const rules = JSON.parse(form.dataset.rules);
const byId = id => document.getElementById(id);
const charLength = value => Array.from(value).length;
let availability = { username: '', available: null };
let availabilityTimer;
let availabilityController;

function nameError(value, label, required) {
    if (!value) return required ? `${label} is required.` : '';
    if (/[0-9]/.test(value)) return `Numbers are not allowed in ${label}.`;
    if (!/^[A-Za-z ]+$/.test(value)) return `Special characters are not allowed in ${label}.`;
    if (value.includes('  ')) return 'Double space is not allowed.';
    if (value.trim() !== value) return `${label} must not start or end with a space.`;
    if (value.toUpperCase() === value) return 'Do not use all capital letters.';
    if (/([a-z])\1\1/i.test(value)) return 'Three consecutive identical letters are not allowed.';
    if (!/^[A-Z][a-z]*(?: [A-Z][a-z]*)*$/.test(value)) return 'First letter of your name must be capital.';
    if (value.length < 2 || value.length > rules.name_max) return `${label} must be 2â€“${rules.name_max} characters.`;
    return '';
}
function validDate(value) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
    const parsed = new Date(value+'T00:00:00Z');
    return !Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0,10) === value && value <= rules.today;
}
function ageAt(value) {
    const [y,m,d] = value.split('-').map(Number);
    const [ty,tm,td] = rules.today.split('-').map(Number);
    return ty-y-((tm<m || (tm===m && td<d))?1:0);
}
function strengthError(value) {
    const groups = [/[a-z]/.test(value),/[A-Z]/.test(value),/[0-9]/.test(value),/[^A-Za-z0-9\s]/u.test(value)].filter(Boolean).length;
    return charLength(value)<rules.password_min || charLength(value)>rules.password_max || /\s/u.test(value) || groups<3
        ? `Use ${rules.password_min}â€“${rules.password_max} characters, at least three character groups, and no whitespace.` : '';
}
const names = {first_name:'First Name',middle_name:'Middle Name',family_name:'Family Name'};
const addresses = {barangay:'Barangay',city:'Municipality / City',province:'Province',country:'Country'};
function messageFor(id) {
    const input = byId(id); if (!input || input.disabled) return '';
    const value = input.value;
    if (names[id]) return nameError(value,names[id],id!=='middle_name');
    if (id==='id') return /^[0-9]{4}-[0-9]{4}$/.test(value)?'':'ID Number must follow the format xxxx-xxxx.';
    if (id==='name_extension') return ['','Jr.','Sr.','Other'].includes(value)?'':'Please select a valid name extension.';
    if (id==='extension_other') return byId('name_extension').value!=='Other' || ['I','II','III','IV','IX','X'].includes(value)?'':'Name Extension must be I, II, III, IV, IX or X.';
    if (id==='birthdate') return !validDate(value)?'Please enter a valid birthdate that is not in the future.':ageAt(value)<18?'You must be at least 18 years old to register.':'';
    if (id==='street') return /^[A-Za-z0-9 ]{3,50}$/.test(value) && !value.includes('  ') && value.trim()===value?'':'Purok / Street must be 3â€“50 letters, digits and single spaces without leading or trailing spaces.';
    if (addresses[id]) {const max=id==='country'?100:50;return value.length>=2 && value.length<=max && /^[A-Z][a-z]*(?: [A-Z][a-z]*)*$/.test(value)?'':`${addresses[id]} must be 2â€“${max} letters and single spaces in Title Case.`;}
    if (id==='zip_code') return /^[0-9]{4}$/.test(value)?'':'ZIP Code must contain exactly 4 digits.';
    if (id==='email') return value.length<=100 && !/\s/.test(value) && /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value) && !input.validity.typeMismatch?'':'Please enter a valid email address.';
    if (id==='username') {
        if (value.length<rules.username_min || value.length>rules.username_max || !/^[A-Za-z][A-Za-z0-9]*$/.test(value)) return `Username must start with a letter and contain ${rules.username_min}â€“${rules.username_max} letters and digits.`;
        return availability.username===value && availability.available===false?'This username is already registered.':'';
    }
    if (id==='password') return strengthError(value);
    if (id==='password_confirm') return value===byId('password').value?'':'Passwords do not match.';
    if (id.startsWith('question_')) {const chosen=[1,2,3].map(slot=>byId('question_'+slot).value);return !/^[1-8]$/.test(value)?'Please select a question from the question bank.':chosen.filter(q=>q===value).length>1?'Choose three different security questions.':'';}
    if (id.startsWith('answer_')) return value.length>=2 && value.length<=50 && /^[A-Za-z]+(?: [A-Za-z]+)*$/.test(value)?'':'Answer must be 2â€“50 letters and single spaces.';
    if (id==='display_name') return value.length>=2 && value.length<=30 && /^[A-Za-z0-9]+(?: [A-Za-z0-9]+)*$/.test(value)?'':'Journal Display Name must be 2â€“30 letters, digits and single spaces.';
    if (id==='journal_start') return validDate(value)?'':'Journaling Start Date must be a valid date that is not in the future.';
    if (id==='writing_goal') return ['Self Reflection','Gratitude','Daily Memories','Personal Growth'].includes(value)?'':'Please select a valid writing goal.';
    if (id==='intention') return charLength(value.trim())>=10 && charLength(value)<=300 && !/\p{Cc}/u.test(value)?'':'Private Journaling Intention must be 10â€“300 characters without control characters.';
    if (id==='consent') return input.checked?'':'You must agree to the Privacy Notice to register.';
    if (id==='captcha') return /^[A-Za-z0-9]{6}$/.test(value)?'':'Enter the six characters shown in the CAPTCHA.';
    return '';
}
function validate(input) {
    if (!input || !input.id || input.type==='hidden' || input.readOnly || input.id==='website') return true;
    const message = messageFor(input.id);
    input.setCustomValidity(message);
    let error = byId('client-error-'+input.id);
    if (message && !error) {error=document.createElement('span');error.id='client-error-'+input.id;error.className='field-error client-error';input.insertAdjacentElement('afterend',error);}
    if (error) {error.textContent=message;error.hidden=!message;}
    if (message) input.setAttribute('aria-invalid','true'); else input.removeAttribute('aria-invalid');
    return !message;
}
function validateAll() {
    let valid=true;
    for (const input of form.querySelectorAll('input,select,textarea')) if (!validate(input)) valid=false;
    return valid;
}
form.addEventListener('input',event=>{
    validate(event.target);
    const serverError=document.getElementById('error-'+event.target.id);if(serverError)serverError.textContent='';
    if (event.target.id==='password' && byId('password_confirm').value) validate(byId('password_confirm'));
});
form.addEventListener('change',event=>{
    validate(event.target);
    if (event.target.id.startsWith('question_')) for(const slot of [1,2,3]) validate(byId('question_'+slot));
    if (event.target.id==='name_extension') validate(byId('extension_other'));
});
form.querySelector('button[type="submit"]').addEventListener('click',validateAll);
form.addEventListener('submit',event=>{
    if (!validateAll()) {event.preventDefault();event.stopImmediatePropagation();form.reportValidity();}
},true);

const username = byId('username');
const status = document.createElement('span');status.id='username-availability';status.setAttribute('aria-live','polite');status.className='availability-message';username.insertAdjacentElement('afterend',status);
username.addEventListener('input',()=>{
    clearTimeout(availabilityTimer);availabilityController?.abort();
    availability={username:username.value,available:null};status.textContent='';validate(username);
    if (messageFor('username')) return;
    const value=username.value;
    status.textContent='Checking username availabilityâ€¦';
    availabilityTimer=setTimeout(async()=>{
        availabilityController=new AbortController();
        try {
            const response=await fetch('/username-availability?username='+encodeURIComponent(value),{credentials:'same-origin',cache:'no-store',signal:availabilityController.signal});
            const result=await response.json();
            if (username.value!==value) return;
            if (!response.ok || !result.valid) throw new Error('Lookup failed.');
            availability={username:value,available:result.available};status.textContent=result.message;status.className=result.available?'availability-message strength-strong':'availability-message field-error';validate(username);
        } catch (error) {
            if (error.name!=='AbortError' && username.value===value) status.textContent='Availability could not be checked. It will be checked when you submit.';
        }
    },350);
});
