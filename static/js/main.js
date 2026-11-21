var root = document.documentElement;
var toastTimer;

// ---------- Dark / Light theme ----------
try {
  var saved = localStorage.getItem("theme");
  if (saved === "light" || saved === "dark") root.classList.add(saved);
} catch (e) {}

function isDark() { return !root.classList.contains("light"); }

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

// Keep CSRF form fields when posting asynchronously.
function postForm(form) {
  return fetch(form.getAttribute("action"), {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8" },
    body: new URLSearchParams(new FormData(form)).toString()
  });
}

// ---------- Pop-up message ----------
function showToast(text) {
  var toast = document.getElementById("toast");
  toast.textContent = text;
  toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(function () { toast.classList.remove("show"); }, 2500);
}

// ---------- Add to cart without reloading ----------
function addToCart(form) {
  postForm(form)
    .then(function (response) { return response.text(); })
    .then(function (html) {
      var page = new DOMParser().parseFromString(html, "text/html");
      var count = page.getElementById("cart-count");
      var message = page.querySelector(".flash");
      var currentCount = document.getElementById("cart-count");
      if (count && currentCount) currentCount.textContent = count.textContent;
      showToast(message ? message.textContent.trim() : "Added to bag");
    })
    .catch(function () { form.submit(); });
}

// ---------- Wishlist heart without reloading ----------
function toggleWish(form) {
  postForm(form)
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