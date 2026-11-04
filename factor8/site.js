(()=>{'use strict';
 // The filing fields are deliberately not persisted or sent to any server.
 const printFields=()=>{document.querySelectorAll('.filing-form input,.filing-form textarea').forEach(el=>{let p=el.parentElement.querySelector('.print-value');if(!p){p=document.createElement('span');p.className='print-value';el.after(p)}p.textContent=el.value.trim()||'________________________________';});};
 window.addEventListener('beforeprint',printFields);
 document.getElementById('print-petition')?.addEventListener('click',()=>{printFields();window.print()});
 if(window.matchMedia('(max-width:760px)').matches){const contents=document.querySelector('.page-contents details');if(contents)contents.open=false;}
})();
