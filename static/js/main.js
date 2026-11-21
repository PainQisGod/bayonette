var root = document.documentElement;
var toastTimer;

// ---------- Dark / Light theme ----------
// Dark luxury is the default. A saved light preference overrides it.
try {
  var saved = localStorage.getItem("theme");
  if (saved === "light" || saved === "dark") root.classList.add(saved);
} catch (e) {}

function isDark() {
  return !root.classList.contains("light");
}

function updateThemeButton() {
  var button = document.getElementById("theme-toggle");
  if (button) button.textContent = isDark() ? "Light mode" : "Dark mode";
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
      var page = new DOMParser().parseFromString(html, "text/html");
      var count = page.getElementById("cart-count");
      var message = page.querySelector(".flash");
      if (count) document.getElementById("cart-count").textContent = count.textContent;
      showToast(message ? message.textContent.trim() : "Added to cart");
    })
    .catch(function () { form.submit(); });
}

// ---------- Wishlist heart without reloading the page ----------
function toggleWish(form) {
  fetch(form.getAttribute("action"), { method: "POST" })
    .then(function (response) {
      if (response.url.indexOf("/login") !== -1) {
        window.location = "/login";
        return null;
      }
      return response.text();
    })
    .then(function (html) {
      if (html === null) return;
      var page = new DOMParser().parseFromString(html, "text/html");
      var message = page.querySelector(".flash");
      var saved = message && message.textContent.indexOf("Saved") !== -1;
      var button = form.querySelector(".wish");
      if (button) {
        button.classList.toggle("on", saved);
        button.textContent = saved ? "♥" : "♡";
      }
      var count = document.getElementById("wish-count");
      if (count) count.textContent = Number(count.textContent) + (saved ? 1 : -1);
      showToast(message ? message.textContent.trim() : "Updated");
    })
    .catch(function () { form.submit(); });
}

// ---------- Forms ----------
document.addEventListener("submit", function (event) {
  var form = event.target;
  var action = form.getAttribute("action") || "";
  if (form.dataset.confirm && !confirm(form.dataset.confirm)) {
    event.preventDefault();
    return;
  }
  if (action.indexOf("/add/") === 0) {
    event.preventDefault();
    addToCart(form);
  }
  if (action.indexOf("/wishlist/") === 0 && !form.dataset.reload) {
    event.preventDefault();
    toggleWish(form);
  }
});

document.addEventListener("DOMContentLoaded", function () {
  var button = document.getElementById("theme-toggle");
  if (button) button.addEventListener("click", toggleTheme);
  updateThemeButton();
});