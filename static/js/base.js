function toggleSidebar() {
    const sidebar = document.getElementById("sidebar");

    sidebar.classList.toggle("open");
}

document.addEventListener("DOMContentLoaded", () => {
    const track = document.querySelector(".banner-track");
    const firstSet = document.querySelector(".banner-set");
    if (!track || !firstSet) return;

    const slides = Array.from(firstSet.querySelectorAll("img"));
    if (slides.length < 2) return;
    track.style.animation = "none";
    track.style.width = "100%";
    track.style.transition = "transform 650ms cubic-bezier(.22,.61,.36,1)";
    firstSet.style.cssText = "display:flex; flex:0 0 100%; gap:0; padding:0";
    const duplicate = track.querySelector('.banner-set[aria-hidden="true"]');
    if (duplicate) duplicate.style.display = "none";
    const setBackdrop = (slide) => {
        firstSet.style.backgroundImage = "linear-gradient(rgba(7,16,28,.42),rgba(7,16,28,.42)),url('" + slide.src + "')";
        firstSet.style.backgroundPosition = "center";
        firstSet.style.backgroundSize = "cover";
    };
    slides.forEach((slide, index) => {
        slide.style.cssText += ";display:" + (index === 0 ? "block" : "none") + ";width:100%;height:clamp(230px, 27vw, 310px);object-fit:contain;background-color:#07101c;background-image:linear-gradient(rgba(7,16,28,.22),rgba(7,16,28,.22)),url('" + slide.currentSrc + "');background-size:cover;background-position:center";
    });
    setBackdrop(slides[0]);
    let index = 0;
    setInterval(() => {
        const current = slides[index];
        index = (index + 1) % slides.length;
        const next = slides[index];
        setBackdrop(next);
        next.style.display = "block";
        next.style.position = "absolute";
        next.style.inset = "0";
        next.style.transform = "translateX(100%)";
        next.style.transition = "transform 650ms cubic-bezier(.22,.61,.36,1)";
        firstSet.style.position = "relative";
        requestAnimationFrame(() => {
            current.style.transform = "translateX(-100%)";
            current.style.transition = "transform 650ms cubic-bezier(.22,.61,.36,1)";
            next.style.transform = "translateX(0)";
        });
        setTimeout(() => {
            current.style.display = "none";
            current.style.transform = "";
            current.style.transition = "";
            next.style.position = "";
            next.style.inset = "";
        }, 680);
    }, 3000);
});
