// Keep the scroll position when a page is reloaded or a form redirects back
// to it (e.g. after marking a character in a long list).
(function () {
    var key = "xuehanzi:scroll:" + location.pathname + location.search;

    window.addEventListener("beforeunload", function () {
        sessionStorage.setItem(key, String(window.scrollY));
    });

    window.addEventListener("load", function () {
        var saved = sessionStorage.getItem(key);
        if (saved !== null) {
            window.scrollTo(0, parseInt(saved, 10));
            sessionStorage.removeItem(key);
        }
    });

    // Elements with data-toggle="#id" show/hide the target.
    document.addEventListener("click", function (event) {
        var trigger = event.target.closest("[data-toggle]");
        if (!trigger) {
            return;
        }
        var target = document.querySelector(trigger.dataset.toggle);
        if (target) {
            target.hidden = !target.hidden;
        }
    });

    // Confirmation for destructive forms.
    document.addEventListener("submit", function (event) {
        var message = event.target.dataset.confirm;
        if (message && !window.confirm(message)) {
            event.preventDefault();
        }
    });
})();
