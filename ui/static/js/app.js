document.addEventListener('htmx:afterRequest', (event) => {
  if (event.detail.elt && event.detail.elt.matches('[hx-post="/api/refresh"]')) {
    window.location.reload();
  }
});
