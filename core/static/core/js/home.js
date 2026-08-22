document.addEventListener("mousemove", (event) => {
  const visual = document.querySelector(".hero-visual");
  if (!visual || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const x = (event.clientX / window.innerWidth - .5) * 10;
  const y = (event.clientY / window.innerHeight - .5) * 8;
  visual.style.setProperty("--tilt-x", `${-y}deg`);
  visual.style.setProperty("--tilt-y", `${x}deg`);
});
