const form = document.getElementById('registerForm');

function validarNome(nome) {
  return nome.trim().split(' ').filter(n => n.length > 0).length >= 2;
}

function validarEmail(email) {
  const dominios = ['unicamp', 'unesp', 'usp', 'fatec', 'unifesp', 'unb', 'ufrj', 'ufmg', 'ufrgs'];
  return dominios.some(dominio => email.toLowerCase().includes(dominio));
}

function validarSenha(senha) {
  const regex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{8,}$/;
  return regex.test(senha);
}

form.addEventListener('submit', function(event) {
  let valid = true;

  const nome = form.name.value;
  if (!validarNome(nome)) {
    form.name.classList.add('is-invalid');
    valid = false;
  } else {
    form.name.classList.remove('is-invalid');
  }

  const email = form.email.value;
  if (!validarEmail(email)) {
    form.email.classList.add('is-invalid');
    valid = false;
  } else {
    form.email.classList.remove('is-invalid');
  }

  const senha = form.password.value;
  const senhaConfirm = form.password_confirm.value;
  if (!validarSenha(senha) || senha !== senhaConfirm) {
    form.password.classList.add('is-invalid');
    form.password_confirm.classList.add('is-invalid');
    valid = false;
  } else {
    form.password.classList.remove('is-invalid');
    form.password_confirm.classList.remove('is-invalid');
  }

  if (!valid) {
    event.preventDefault();
    event.stopPropagation();
  }
});

const passwordInput = document.getElementById('password');
const passwordConfirmInput = document.getElementById('password_confirm');

const requirements = {
  length: document.getElementById('length'),
  lowercase: document.getElementById('lowercase'),
  uppercase: document.getElementById('uppercase'),
  number: document.getElementById('number'),
  special: document.getElementById('special'),
  match: document.getElementById('password-match'),
};

passwordInput.addEventListener('input', () => {
  const val = passwordInput.value;
  const confirmVal = passwordConfirmInput.value;

  // Checa cada requisito
  if (val.length >= 8) {
    requirements.length.textContent = '✔ Mínimo de 8 caracteres';
    requirements.length.classList.remove('text-danger');
    requirements.length.classList.add('text-success');
  } else {
    requirements.length.textContent = '❌ Mínimo de 8 caracteres';
    requirements.length.classList.add('text-danger');
    requirements.length.classList.remove('text-success');
  }

  if (/[a-z]/.test(val)) {
    requirements.lowercase.textContent = '✔ Letra minúscula';
    requirements.lowercase.classList.remove('text-danger');
    requirements.lowercase.classList.add('text-success');
  } else {
    requirements.lowercase.textContent = '❌ Letra minúscula';
    requirements.lowercase.classList.add('text-danger');
    requirements.lowercase.classList.remove('text-success');
  }

  if (/[A-Z]/.test(val)) {
    requirements.uppercase.textContent = '✔ Letra maiúscula';
    requirements.uppercase.classList.remove('text-danger');
    requirements.uppercase.classList.add('text-success');
  } else {
    requirements.uppercase.textContent = '❌ Letra maiúscula';
    requirements.uppercase.classList.add('text-danger');
    requirements.uppercase.classList.remove('text-success');
  }

  if (/\d/.test(val)) {
    requirements.number.textContent = '✔ Número';
    requirements.number.classList.remove('text-danger');
    requirements.number.classList.add('text-success');
  } else {
    requirements.number.textContent = '❌ Número';
    requirements.number.classList.add('text-danger');
    requirements.number.classList.remove('text-success');
  }

  if (/[\W_]/.test(val)) {
    requirements.special.textContent = '✔ Caractere especial';
    requirements.special.classList.remove('text-danger');
    requirements.special.classList.add('text-success');
  } else {
    requirements.special.textContent = '❌ Caractere especial';
    requirements.special.classList.add('text-danger');
    requirements.special.classList.remove('text-success');
  }

   // Verifica se as senhas coincidem
  if (val && confirmVal && val === confirmVal) {
    requirements.match.textContent = '✔ Senhas coincidem';
    requirements.match.classList.remove('text-danger');
    requirements.match.classList.add('text-success');
  } else {
    requirements.match.textContent = '❌ Senhas coincidem';
    requirements.match.classList.add('text-danger');
    requirements.match.classList.remove('text-success');
  }
});
