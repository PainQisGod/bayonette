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

// ---------- Wishlist heart without reloading the page ----------
function toggleWish(form) {
  fetch(form.getAttribute("action"), { method: "POST" })
    .then(function (response) {
      // not logged in: the server sends us to the login page
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

  // <form data-confirm="Are you sure?"> asks before sending
  if (form.dataset.confirm && !confirm(form.dataset.confirm)) {
    event.preventDefault();
    return;
  }

  if (action.indexOf("/add/") === 0) {
    event.preventDefault();
    addToCart(form);
  }

  // the Remove button on the wishlist page reloads normally (data-reload)
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