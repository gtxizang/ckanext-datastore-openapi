(function() {
  var el = document.getElementById("swagger-ui");
  var specUrl = el.getAttribute("data-spec-url");
  if (!specUrl) return;

  fetch(specUrl, {credentials: "same-origin"})
    .then(function(r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .then(function(spec) {
      if (!spec.openapi) throw new Error("Invalid spec");
      while (el.firstChild) el.removeChild(el.firstChild);
      SwaggerUIBundle({
        spec: spec,
        domNode: el,
        presets: [SwaggerUIBundle.presets.apis],
        plugins: [SwaggerUIBundle.plugins.DownloadUrl],
        layout: "BaseLayout",
        tryItOutEnabled: true,
        docExpansion: "full",
        defaultModelsExpandDepth: 0
      });
    })
    .catch(function(e) {
      while (el.firstChild) el.removeChild(el.firstChild);
      var d = document.createElement("div");
      d.className = "error-message";
      var p1 = document.createElement("p");
      p1.textContent = "Failed to load API documentation.";
      var p2 = document.createElement("p");
      p2.textContent = e.message;
      d.appendChild(p1);
      d.appendChild(p2);
      el.appendChild(d);
    });
})();
