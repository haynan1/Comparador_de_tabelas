const filter = document.getElementById("tableFilter");
const table = document.getElementById("resultTable");
const themeToggle = document.getElementById("themeToggle");
const savedTheme = localStorage.getItem("theme") || "dark";

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  if (themeToggle) {
    themeToggle.innerHTML = `<span aria-hidden="true">${theme === "dark" ? "&#9728;" : "&#9790;"}</span>`;
    themeToggle.setAttribute("aria-label", theme === "dark" ? "Ativar modo claro" : "Ativar modo escuro");
    themeToggle.setAttribute("title", theme === "dark" ? "Modo claro" : "Modo escuro");
  }
}

applyTheme(savedTheme);

if (themeToggle) {
  themeToggle.addEventListener("click", () => {
    const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    localStorage.setItem("theme", nextTheme);
    applyTheme(nextTheme);
  });
}

if (filter && table) {
  filter.addEventListener("input", () => {
    const term = filter.value.toLowerCase();
    table.querySelectorAll("tbody tr").forEach((row) => {
      row.style.display = row.innerText.toLowerCase().includes(term) ? "" : "none";
    });
  });
}

document.querySelectorAll('input[type="file"]').forEach((input) => {
  input.addEventListener("change", () => {
    const target = document.querySelector(`[data-file-name="${input.id}"]`);
    if (target) {
      target.textContent = input.files.length ? input.files[0].name : "Nenhum arquivo selecionado";
    }
  });
});

document.querySelectorAll("form").forEach((form) => {
  form.addEventListener("submit", () => {
    const btn = form.querySelector('button[type="submit"]');
    if (!btn || btn.disabled) return;
    const originalText = btn.textContent.trim();
    btn.disabled = true;
    btn.innerHTML = `<span class="loading-dots">${originalText}</span>`;
  });
});
