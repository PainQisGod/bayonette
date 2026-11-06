var root = document.documentElement;
var toastTimer;

// ---------- Dark / Light theme ----------
// this part runs straight away so the page doesn't flash the wrong colors
try {
  var saved = localStorage.getItem("theme");
  if (saved) root.classList.add(saved);
} catch (e) {}

function isDark() {
  if (root.classList.contains("dark")) return true;
  if (root.classList.contains("light")) return false;
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function updateThemeButton() {
  var button = document.getElementById("theme-toggle");
  if (button) button.textContent = isDark() ? "Light" : "Dark";
}

function toggleTheme() {
  var next = isDark() ? "light" : "dark";
  root.classList.remove("dark", "light");
  root.classList.add(next);
  try { localStorage.setItem("theme", next); } catch (e) {}
  updateThemeButton();
}

// ---------- Pop-up message ----------
function showToast(text) {
  var toast = document.getElementById("toast");
  toast.textContent = text;
  toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(function () { toast.classList.remove("show"); }, 2500);
}

// ---------- Add to cart without reloading the page ----------
function addToCart(form) {
  fetch(form.getAttribute("action"), { method: "POST" })
    .then(function (response) { return response.text(); })
    .then(function (html) {
      // the server sends back the whole page, so read the new cart number
      // and any message (like "no more in stock") out of it
      var page = new DOMParser().parseFromString(html, "text/html");
      var count = page.getElementById("cart-count");
      var message = page.querySelector(".flash");
      if (count) document.getElementById("cart-count").textContent = count.textContent;
      showToast(message ? message.textContent.trim() : "Added to cart");
    })
    .catch(function () { form.submit(); });   // if anything goes wrong, do it the old way
}

// ---------- Forms ----------
document.addEventListener("submit", function (event) {
  var form = event.target;
  var action = form.getAttribute("action") || "";

  // <form data-confirm="Are you sure?"> asks before sending
  if (form.dataset.confirm && !confirm(form.dataset.confirm)) {
    event.preventDefault();
    return;
  }

  if (action.indexOf("/add/") === 0) {
    event.preventDefault();
    addToCart(form);
  }
});

document.addEventListener("DOMContentLoaded", function () {
  var button = document.getElementById("theme-toggle");
  if (button) button.addEventListener("click", toggleTheme);
  updateThemeButton();
});