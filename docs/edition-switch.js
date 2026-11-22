document.querySelectorAll(".edition-switch a").forEach((link) => {
  const destination = new URL(link.href);

  function updateDestination() {
    const activeSection = document.querySelector("#TOC .nav-link.active");
    destination.hash = window.location.hash || activeSection?.hash || "";
    link.href = destination.href;
  }

  updateDestination();
  window.addEventListener("hashchange", updateDestination);
  link.addEventListener("focus", updateDestination);
  link.addEventListener("pointerdown", updateDestination);
  link.addEventListener("click", updateDestination);
});
