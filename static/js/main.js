var root = document.documentElement;
var toastTimer;
var toastQueue = [];
var toastBusy = false;

// ---------- Theme ----------
try {
  var savedTheme = localStorage.getItem("theme");
  if (savedTheme === "light" || savedTheme === "dark") root.classList.add(savedTheme);
} catch (e) {}

function isDark() { return !root.classList.contains("light"); }

function updateThemeButton() {
  var button = document.getElementById("theme-toggle");
  if (!button) return;
  var label = isDark() ? "Switch to light mode" : "Switch to dark mode";
  button.textContent = isDark() ? "Light mode" : "Dark mode";
  button.setAttribute("aria-label", label);
  button.setAttribute("aria-pressed", String(!isDark()));
}

function toggleTheme() {
  var next = isDark() ? "light" : "dark";
  root.classList.remove("dark", "light");
  root.classList.add(next);
  try { localStorage.setItem("theme", next); } catch (e) {}
  updateThemeButton();
}

// ---------- Shared helpers ----------
function postForm(form) {
  return fetch(form.getAttribute("action"), {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8" },
    body: new URLSearchParams(new FormData(form)).toString()
  });
}

function setFormBusy(form, busy, label) {
  var button = form.querySelector('button[type="submit"], button:not([type])');
  if (!button) return;
  if (busy) {
    button.dataset.originalLabel = button.textContent;
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
    button.classList.add("is-loading");
    if (label) button.textContent = label;
  } else {
    button.disabled = false;
    button.removeAttribute("aria-busy");
    button.classList.remove("is-loading");
    if (button.dataset.originalLabel) {
      button.textContent = button.dataset.originalLabel;
      delete button.dataset.originalLabel;
    }
  }
}

function parseResponse(response) {
  if (response.url && response.url.indexOf("/login") !== -1) {
    window.location.assign(response.url);
    return Promise.resolve(null);
  }
  if (!response.ok) throw new Error("The request could not be completed.");
  return response.text().then(function (html) {
    return new DOMParser().parseFromString(html, "text/html");
  });
}

function getFlashText(page) {
  var message = page && page.querySelector(".flash");
  return message ? message.textContent.trim() : "";
}

function updateCount(id, page) {
  var next = page && page.getElementById(id);
  var current = document.getElementById(id);
  if (next && current) current.textContent = next.textContent.trim();
}

// ---------- Toast notifications ----------
function showToast(message) {
  var toast = document.getElementById("toast");
  if (!toast || !message) return;
  toastQueue.push(message);
  if (toastBusy) return;

  toastBusy = true;
  var next = toastQueue.shift();
  toast.textContent = next;
  toast.classList.add("show");
  toast.setAttribute("aria-hidden", "false");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(function () {
    toast.classList.remove("show");
    toast.setAttribute("aria-hidden", "true");
    toastBusy = false;
    if (toastQueue.length) showToast(toastQueue.shift());
  }, 2800);
}

// ---------- Add to bag ----------
function addToCart(form) {
  setFormBusy(form, true, "Adding…");
  postForm(form)
    .then(parseResponse)
    .then(function (page) {
      if (!page) return;
      updateCount("cart-count", page);
      showToast(getFlashText(page) || "Added to your bag.");
    })
    .catch(function () {
      form.submit();
    })
    .finally(function () { setFormBusy(form, false); });
}

// ---------- Wishlist ----------
function toggleWish(form) {
  setFormBusy(form, true);
  postForm(form)
    .then(parseResponse)
    .then(function (page) {
      if (!page) return;
      var message = getFlashText(page);
      var wasSaved = message.indexOf("Saved to your wishlist.") !== -1;
      var wasRemoved = message.indexOf("Removed from your wishlist.") !== -1;
      var button = form.querySelector(".wish");

      if (button && (wasSaved || wasRemoved)) {
        button.classList.toggle("on", wasSaved);
        button.textContent = wasSaved ? "♥" : "♡";
        button.setAttribute("aria-pressed", String(wasSaved));
        button.setAttribute("aria-label", wasSaved ? "Remove from wishlist" : "Save to wishlist");
      }

      updateCount("wish-count", page);
      showToast(message || "Wishlist updated.");
    })
    .catch(function () {
      form.submit();
    })
    .finally(function () { setFormBusy(form, false); });
}

// ---------- Form behavior ----------
document.addEventListener("submit", function (event) {
  var form = event.target;
  if (!form || !form.getAttribute) return;

  if (form.dataset.confirm && !window.confirm(form.dataset.confirm)) {
    event.preventDefault();
    return;
  }

  var action = form.getAttribute("action") || "";
  if (action.indexOf("/add/") === 0) {
    event.preventDefault();
    addToCart(form);
  } else if (action.indexOf("/wishlist/") === 0 && !form.dataset.reload) {
    event.preventDefault();
    toggleWish(form);
  }
});

document.addEventListener("DOMContentLoaded", function () {
  var themeButton = document.getElementById("theme-toggle");
  if (themeButton) themeButton.addEventListener("click", toggleTheme);
  updateThemeButton();

  document.querySelectorAll(".wish").forEach(function (button) {
    button.setAttribute("aria-pressed", String(button.classList.contains("on")));
  });
});
