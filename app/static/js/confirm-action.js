document.addEventListener("submit", (event) => {
    const message = event.submitter?.dataset.confirm || event.target.dataset.confirm;
    if (message && !window.confirm(message)) {
        event.preventDefault();
    }
});
