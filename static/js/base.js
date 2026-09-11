function toggleSidebar() {
    const sidebar = document.getElementById("sidebar");

    sidebar.classList.toggle("open");
}

document.addEventListener("DOMContentLoaded", () => {
    const viewport = document.querySelector(".banner-viewport");
    const track = document.querySelector(".banner-track");
    const firstSet = document.querySelector(".banner-set");
    const secondSet = track?.querySelector('.banner-set[aria-hidden="true"]');
    if (!viewport || !track || !firstSet || !secondSet) return;

    const allSlides = [...firstSet.children, ...secondSet.children];
    const slideCount = firstSet.children.length;
    if (slideCount < 2) return;
    let position = 0;
    let step = 0;

    const layout = () => {
        const cardsVisible = window.innerWidth <= 700 ? 1 : 3;
        const gap = window.innerWidth <= 700 ? 12 : 16;
        const padding = window.innerWidth <= 700 ? 18 : 32;
        const cardWidth = Math.floor((viewport.clientWidth - padding - gap * (cardsVisible - 1)) / cardsVisible);
        const cardHeight = Math.round(cardWidth * 2 / 3);
        step = cardWidth + gap;
        track.style.cssText = "display:flex;width:max-content;animation:none;transform:translateX(" + position + "px);transition:transform 650ms cubic-bezier(.22,.61,.36,1)";
        [firstSet, secondSet].forEach((set) => {
            set.style.cssText = "display:flex;flex:0 0 auto;gap:" + gap + "px;padding:" + (window.innerWidth <= 700 ? "9px" : "12px 16px") + "px";
        });
        allSlides.forEach((slide) => {
            slide.style.cssText = "display:block;flex:0 0 auto;width:" + cardWidth + "px;height:" + cardHeight + "px";
        });
    };

    layout();
    window.addEventListener("resize", () => { position = 0; layout(); });
    window.setInterval(() => {
        position -= step;
        track.style.transform = "translateX(" + position + "px)";
        if (Math.abs(position) >= step * slideCount) {
            window.setTimeout(() => {
                track.style.transition = "none";
                position = 0;
                track.style.transform = "translateX(0)";
                window.requestAnimationFrame(() => { track.style.transition = "transform 650ms cubic-bezier(.22,.61,.36,1)"; });
            }, 680);
        }
    }, 3000);
});
