(function () {
    "use strict";

    // ---------- Helpers ----------

    function qs(selector, scope) {
        return (scope || document).querySelector(selector);
    }

    function qsa(selector, scope) {
        return Array.prototype.slice.call((scope || document).querySelectorAll(selector));
    }

    // ---------- Service worker ----------

    if ("serviceWorker" in navigator) {
        window.addEventListener("load", function () {
            navigator.serviceWorker
                .register("/service-worker.js")
                .then(function (reg) {
                    console.log("[SW] registered", reg.scope);
                })
                .catch(function (err) {
                    console.warn("[SW] registration failed", err);
                });
        });
    }

    // ---------- Mobile menu ----------

    function initMenu() {
        const toggle = qs("[data-menu-toggle]");
        const menu = qs("[data-menu]");

        if (!toggle || !menu) return;

        toggle.addEventListener("click", function () {
            const isOpen = toggle.classList.toggle("is-open");
            menu.classList.toggle("is-open", isOpen);
        });

        // закрывать по клику на ссылку (на мобиле)
        qsa(".ps-nav-link", menu).forEach(function (link) {
            link.addEventListener("click", function () {
                toggle.classList.remove("is-open");
                menu.classList.remove("is-open");
            });
        });
    }

    // ---------- Smooth scroll ----------

    function initSmoothScroll() {
        qsa("[data-scroll-to]").forEach(function (el) {
            el.addEventListener("click", function (e) {
                const href = el.getAttribute("href");
                if (!href || !href.startsWith("#")) return;
                const target = qs(href);
                if (!target) return;
                e.preventDefault();
                window.scrollTo({
                    top: target.getBoundingClientRect().top + window.scrollY - 72,
                    behavior: "smooth"
                });
            });
        });
    }

    // ---------- Back to top ----------

    function initBackToTop() {
        const btn = qs("[data-back-to-top]");
        if (!btn) return;

        function onScroll() {
            if (window.scrollY > 300) {
                btn.classList.add("is-visible");
            } else {
                btn.classList.remove("is-visible");
            }
        }

        window.addEventListener("scroll", onScroll, {passive: true});
        onScroll();

        btn.addEventListener("click", function () {
            window.scrollTo({top: 0, behavior: "smooth"});
        });
    }

    // ---------- Toasts ----------

    function showToast(message, type) {
        type = type || "info";
        const container = qs(".ps-toast-container");
        if (!container) return;

        const toast = document.createElement("div");
        toast.className = "ps-toast ps-toast--" + type;

        const msg = document.createElement("div");
        msg.className = "ps-toast-message";
        msg.textContent = message;

        const close = document.createElement("button");
        close.className = "ps-toast-close";
        close.type = "button";
        close.innerHTML = "×";

        close.addEventListener("click", function () {
            toast.remove();
        });

        toast.appendChild(msg);
        toast.appendChild(close);
        container.appendChild(toast);

        setTimeout(function () {
            toast.remove();
        }, 4000);
    }

    // ---------- PWA install banner ----------

    let deferredPrompt = null;

    function initInstallBanner() {
        const banner = qs("[data-install-banner]");
        const btnAccept = qs("[data-install-accept]", banner);
        const btnDismiss = qs("[data-install-dismiss]", banner);

        if (!banner || !btnAccept || !btnDismiss) return;

        window.addEventListener("beforeinstallprompt", function (e) {
            e.preventDefault();
            deferredPrompt = e;
            banner.hidden = false;
        });

        btnDismiss.addEventListener("click", function () {
            banner.hidden = true;
            deferredPrompt = null;
        });

        btnAccept.addEventListener("click", function () {
            if (!deferredPrompt) {
                banner.hidden = true;
                return;
            }
            deferredPrompt.prompt();
            deferredPrompt.userChoice
                .then(function (choiceResult) {
                    if (choiceResult.outcome === "accepted") {
                        showToast("Установка ParkShare RU запущена", "success");
                    }
                    banner.hidden = true;
                    deferredPrompt = null;
                })
                .catch(function () {
                    banner.hidden = true;
                    deferredPrompt = null;
                });
        });
    }

    // ---------- Skeleton removal ----------

    function initSkeletons() {
        const cards = qsa(".ps-card--skeleton");
        if (!cards.length) return;

        // Имитация загрузки данных — через небольшой таймаут
        window.setTimeout(function () {
            cards.forEach(function (card) {
                card.parentNode && card.parentNode.removeChild(card);
            });
        }, 350);
    }

    // ---------- Geolocation helper ----------

    function initGeolocation() {
        const buttons = qsa("[data-fill-location]");
        if (!buttons.length) return;

        function fill(lat, lng) {
            const latInput = qs("#lat");
            const lngInput = qs("#lng");
            if (!latInput || !lngInput) return;
            latInput.value = lat.toFixed(5);
            lngInput.value = lng.toFixed(5);
            showToast("Координаты определены, нажмите «Найти места»", "success");
        }

        buttons.forEach(function (btn) {
            btn.addEventListener("click", function () {
                if (!("geolocation" in navigator)) {
                    showToast("Геолокация недоступна в этом браузере", "error");
                    return;
                }

                navigator.geolocation.getCurrentPosition(
                    function (pos) {
                        fill(pos.coords.latitude, pos.coords.longitude);
                    },
                    function () {
                        showToast("Не удалось получить местоположение", "error");
                    },
                    {
                        enableHighAccuracy: false,
                        timeout: 8000,
                        maximumAge: 60000
                    }
                );
            });
        });
    }

    // ---------- Init ----------

    document.addEventListener("DOMContentLoaded", function () {
        initMenu();
        initSmoothScroll();
        initBackToTop();
        initInstallBanner();
        initSkeletons();
        initGeolocation();
    });

    // Экспортируем showToast в глобальную область на всякий
    window.ParkShare = window.ParkShare || {};
    window.ParkShare.showToast = showToast;
})();
