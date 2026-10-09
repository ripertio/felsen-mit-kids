(() => {
    const button = document.querySelector("[data-use-current-location]");
    const status = document.querySelector("[data-location-status]");
    if (!button || !status) {
        return;
    }

    button.addEventListener("click", () => {
        if (!navigator.geolocation) {
            status.textContent = "Standortbestimmung wird von diesem Browser nicht unterstützt.";
            return;
        }

        button.disabled = true;
        status.textContent = "Standort wird ermittelt …";

        navigator.geolocation.getCurrentPosition(
            (position) => {
                const location = document.querySelector('[name="location"]');
                if (!location) {
                    button.disabled = false;
                    status.textContent = "Das Standortfeld wurde nicht gefunden.";
                    return;
                }

                location.value = `${position.coords.latitude.toFixed(6)}, ${position.coords.longitude.toFixed(6)}`;
                location.dispatchEvent(new Event("input", { bubbles: true }));
                location.dispatchEvent(new Event("change", { bubbles: true }));
                button.disabled = false;
                status.textContent = "Standort übernommen.";
            },
            (error) => {
                button.disabled = false;
                if (error.code === error.PERMISSION_DENIED) {
                    status.textContent = "Standortzugriff wurde nicht erlaubt.";
                } else if (error.code === error.POSITION_UNAVAILABLE) {
                    status.textContent = "Der Standort ist derzeit nicht verfügbar.";
                } else if (error.code === error.TIMEOUT) {
                    status.textContent = "Die Standortbestimmung hat zu lange gedauert.";
                } else {
                    status.textContent = "Standort konnte nicht ermittelt werden.";
                }
            },
            { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 },
        );
    });
})();
